# frozen_string_literal: true

# UX DSL — an idiomatic-Ruby authoring surface for `.ux.json` contracts.
#
#     UX.design "smart-kettle" do
#       persona :busy_parent, goals: ["hot water fast"], context: "morning rush"
#       job :boil, functional: "...", emotional: "...", social: "...",
#           importance: 9, satisfaction: 4
#       journey :morning do
#         stage :fill, touchpoints: %w[lid handle], emotion: 3, jobs: %i[boil]
#       end
#       statechart :power do
#         state :idle, initial: true
#         on :idle, :press, to: :heating
#       end
#       surface :hardware_button, layer: :hardware
#       core_experience "one press, walk away"
#       qcd quality: :high, cost: :medium, delivery: :fast
#     end
#
# `ruby bin/ux-dsl file.rb` prints the contract JSON to stdout. Plain
# stdlib only — no method_missing, no external gems.

require "json"

# UX — the design-expression DSL namespace. `UX.design` builds a
# `.ux.json` contract hash; judgement lives in the Python gates.
module UX
  LAYERS = %i[
    hardware mechanism industrial_design circuit firmware
    cloud_backend web_ui smartphone_app pc_app
  ].freeze
  QCD_LEVELS = %i[low medium high].freeze
  QCD_DELIVERY = %i[slow normal fast].freeze
  STAGE_KINDS = %i[discover onboard use recover exit].freeze
  MODALITIES = %i[visual audio haptic motion text].freeze
  CONTROL_KINDS = %i[button touch dial switch link gesture].freeze
  CADENCES = %i[moment session daily weekly].freeze

  Surface = Struct.new(:id, :layer, :name, :notes)
  Persona = Struct.new(:id, :name, :goals, :context, :pains)
  Job = Struct.new(:id, :functional, :emotional, :social, :importance, :satisfaction)
  Stage = Struct.new(:id, :kind, :touchpoints, :emotion, :pain_points, :surfaces, :jobs)
  Journey = Struct.new(:id, :persona, :stages)
  StateDef = Struct.new(:id, :initial, :final, :description, :surface, :entry, :exit)
  Transition = Struct.new(:from_state, :event, :to, :guard, :actions)
  Statechart = Struct.new(:id, :states, :transitions)
  Blueprint = Struct.new(:frontstage, :backstage, :support_processes)
  Control = Struct.new(:id, :surface, :kind, :touchpoint, :width_mm, :height_mm,
                       :fg, :bg, :large_text)
  Feedback = Struct.new(:id, :trigger, :surface, :modality, :latency_ms,
                        :progress_indicator, :description)
  ExperienceLoop = Struct.new(:id, :steps, :reward, :cadence)

  class DesignError < StandardError; end

  # Builder collected by `UX.design`; `to_h` is the contract shape.
  class Design
    attr_reader :product_name

    def initialize(product_name)
      @product_name = product_name.to_s
      @surfaces = []
      @personas = []
      @jobs = []
      @journeys = []
      @statecharts = []
      @feedback = []
      @controls = []
      @loops = []
      @blueprint = nil
      @core_experience = ""
      @implementation_spec = []
      @qcd = { quality: :medium, cost: :medium, delivery: :normal, rationale: "" }
      @imports = []
    end

    def surface(id, layer:, name: "", notes: "")
      unless LAYERS.include?(layer)
        raise DesignError, "unknown surface layer #{layer.inspect}; expected one of #{LAYERS.inspect}"
      end

      @surfaces << Surface.new(id.to_s, layer.to_s, name.to_s, notes.to_s)
    end

    def persona(id, name: "", goals: [], context: "", pains: [])
      @personas << Persona.new(id.to_s, name.to_s, goals.map(&:to_s), context.to_s, pains.map(&:to_s))
    end

    def job(id, functional:, emotional: "", social: "", importance:, satisfaction:)
      @jobs << Job.new(id.to_s, functional.to_s, emotional.to_s, social.to_s,
                       Integer(importance), Integer(satisfaction))
    end

    def journey(id, persona: "", &block)
      builder = JourneyBuilder.new(id)
      builder.instance_eval(&block)
      @journeys << Journey.new(id.to_s, persona.to_s, builder.stages)
    end

    def service_blueprint(frontstage: [], backstage: [], support: [])
      @blueprint = Blueprint.new(frontstage.map(&:to_s), backstage.map(&:to_s), support.map(&:to_s))
    end

    def statechart(id, &block)
      builder = StatechartBuilder.new(id)
      builder.instance_eval(&block)
      @statecharts << Statechart.new(id.to_s, builder.states, builder.transitions)
    end

    def surface_layer_for(id)
      @surfaces.find { |s| s.id == id.to_s }&.layer
    end

    def core_experience(text)
      @core_experience = text.to_s
    end

    def implementation_spec(*items)
      @implementation_spec.concat(items.flatten.map(&:to_s))
    end

    def feedback(id, trigger:, surface:, modality:, latency_ms: 100,
                 progress_indicator: false, description: "")
      unless MODALITIES.include?(modality)
        raise DesignError, "unknown feedback modality #{modality.inspect}; expected #{MODALITIES.inspect}"
      end

      @feedback << Feedback.new(id.to_s, trigger.to_s, surface.to_s, modality.to_s,
                                Integer(latency_ms), progress_indicator ? true : false,
                                description.to_s)
    end

    def control(id, surface:, kind: :touch, size_mm: nil, touchpoint: "",
                fg: "", bg: "", large_text: false)
      unless CONTROL_KINDS.include?(kind)
        raise DesignError, "unknown control kind #{kind.inspect}; expected #{CONTROL_KINDS.inspect}"
      end

      width_mm, height_mm = size_mm || []
      @controls << Control.new(id.to_s, surface.to_s, kind.to_s, touchpoint.to_s,
                               width_mm, height_mm, fg.to_s, bg.to_s,
                               large_text ? true : false)
    end

    # `loop` is Kernel#loop, so the DSL verb is `experience_loop`.
    def experience_loop(id, steps:, reward: "", cadence: :session)
      unless CADENCES.include?(cadence)
        raise DesignError, "unknown loop cadence #{cadence.inspect}; expected #{CADENCES.inspect}"
      end

      @loops << ExperienceLoop.new(id.to_s, steps.map(&:to_s), reward.to_s, cadence.to_s)
    end

    def qcd(quality:, cost:, delivery:, rationale: "")
      unless QCD_LEVELS.include?(quality) && QCD_LEVELS.include?(cost) && QCD_DELIVERY.include?(delivery)
        raise DesignError, "qcd expects quality/cost ∈ #{QCD_LEVELS.inspect}, delivery ∈ #{QCD_DELIVERY.inspect}"
      end

      @qcd = { quality: quality, cost: cost, delivery: delivery, rationale: rationale.to_s }
    end

    def import(system:, path:, sha256:, extracted: [])
      @imports << { system: system.to_s, path: path.to_s, sha256: sha256.to_s,
                    extracted: extracted.map(&:to_s) }
    end

    def to_h
      {
        schema_version: 1,
        system: "ux-creator",
        product: {
          name: @product_name,
          surfaces: @surfaces.map { |s| { id: s.id, layer: s.layer, name: s.name, notes: s.notes } },
        },
        core_experience: @core_experience,
        implementation_spec: @implementation_spec,
        qcd: @qcd.transform_values(&:to_s),
        personas: @personas.map { |p| { id: p.id, name: p.name, goals: p.goals, context: p.context, pains: p.pains } },
        jobs: @jobs.map do |j|
          { id: j.id, functional: j.functional, emotional: j.emotional, social: j.social,
            importance: j.importance, satisfaction: j.satisfaction }
        end,
        journeys: @journeys.map do |j|
          { id: j.id, persona: j.persona,
            stages: j.stages.map do |s|
              { id: s.id, kind: s.kind, touchpoints: s.touchpoints, emotion: s.emotion,
                pain_points: s.pain_points, surfaces: s.surfaces, jobs: s.jobs }
            end }
        end,
        service_blueprint: @blueprint && {
          frontstage: @blueprint.frontstage,
          backstage: @blueprint.backstage,
          support_processes: @blueprint.support_processes,
        },
        statecharts: @statecharts.map do |c|
          { id: c.id,
            states: c.states.map do |s|
              { id: s.id, initial: s.initial, final: s.final, description: s.description,
                surface: s.surface, entry: s.entry, exit: s.exit }
            end,
            transitions: c.transitions.map do |t|
              { "from" => t.from_state, event: t.event, to: t.to,
                guard: t.guard, actions: t.actions }
            end }
        end,
        controls: @controls.map do |c|
          { id: c.id, surface: c.surface, kind: c.kind, touchpoint: c.touchpoint,
            width_mm: c.width_mm, height_mm: c.height_mm, fg: c.fg, bg: c.bg,
            large_text: c.large_text }
        end,
        feedback: @feedback.map do |f|
          { id: f.id, trigger: f.trigger, surface: f.surface, modality: f.modality,
            latency_ms: f.latency_ms, progress_indicator: f.progress_indicator,
            description: f.description }
        end,
        loops: @loops.map do |l|
          { id: l.id, steps: l.steps, reward: l.reward, cadence: l.cadence }
        end,
        imports: @imports,
      }.compact
    end
  end

  # Collects `stage` declarations inside `journey`.
  class JourneyBuilder
    attr_reader :stages

    def initialize(_id)
      @stages = []
    end

    def stage(id, kind: :use, touchpoints: [], emotion:, pain_points: [], surfaces: [], jobs: [])
      unless STAGE_KINDS.include?(kind)
        raise DesignError, "unknown stage kind #{kind.inspect}; expected #{STAGE_KINDS.inspect}"
      end

      @stages << Stage.new(id.to_s, kind.to_s, touchpoints.map(&:to_s), Integer(emotion),
                           pain_points.map(&:to_s), surfaces.map(&:to_s), jobs.map(&:to_s))
    end
  end

  # Collects `state`/`on` declarations inside `statechart`.
  class StatechartBuilder
    attr_reader :states, :transitions

    def initialize(_id)
      @states = []
      @transitions = []
    end

    def state(id, initial: false, final: false, description: "", surface: "",
              entry: [], exit: [])
      @states << StateDef.new(id.to_s, initial, final, description.to_s, surface.to_s,
                              entry.map(&:to_s), exit.map(&:to_s))
    end

    def on(from_state, event, to:, guard: "", actions: [])
      @transitions << Transition.new(from_state.to_s, event.to_s, to.to_s,
                                     guard.to_s, actions.map(&:to_s))
    end
  end

  module_function

  # Entry point: `UX.design "name" do ... end` → Design
  def design(product_name, &block)
    builder = Design.new(product_name)
    builder.instance_eval(&block)
    builder
  end

  def compile_file(path)
    design = eval(File.read(path, encoding: "UTF-8"), TOPLEVEL_BINDING, path) # rubocop:disable Security/Eval
    design.is_a?(Design) ? design : raise(DesignError, "#{path} did not return a UX.design")
  end
end
