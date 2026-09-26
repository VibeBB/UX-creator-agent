# frozen_string_literal: true

# UX DSL — an idiomatic-Ruby authoring surface for `.ux.json` contracts.
#
#     UX.design "smart-kettle" do
#       persona :busy_parent, goals: ["hot water fast"], context: "morning rush"
#       job :boil, functional: "...", emotional: "...", social: "...",
#           importance: 9, satisfaction: 4
#       journey :morning do
#         stage :fill, touchpoints: %w[lid handle], emotion: 3
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

  Surface = Struct.new(:id, :layer, :name, :notes)
  Persona = Struct.new(:id, :name, :goals, :context, :pains)
  Job = Struct.new(:id, :functional, :emotional, :social, :importance, :satisfaction)
  Stage = Struct.new(:id, :touchpoints, :emotion, :pain_points, :surfaces)
  Journey = Struct.new(:id, :persona, :stages)
  StateDef = Struct.new(:id, :initial, :final)
  Transition = Struct.new(:from_state, :event, :to)
  Statechart = Struct.new(:id, :states, :transitions)
  Blueprint = Struct.new(:frontstage, :backstage, :support_processes)

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
              { id: s.id, touchpoints: s.touchpoints, emotion: s.emotion,
                pain_points: s.pain_points, surfaces: s.surfaces }
            end }
        end,
        service_blueprint: @blueprint && {
          frontstage: @blueprint.frontstage,
          backstage: @blueprint.backstage,
          support_processes: @blueprint.support_processes,
        },
        statecharts: @statecharts.map do |c|
          { id: c.id,
            states: c.states.map { |s| { id: s.id, initial: s.initial, final: s.final } },
            transitions: c.transitions.map { |t| { "from" => t.from_state, event: t.event, to: t.to } } }
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

    def stage(id, touchpoints: [], emotion:, pain_points: [], surfaces: [])
      @stages << Stage.new(id.to_s, touchpoints.map(&:to_s), Integer(emotion),
                           pain_points.map(&:to_s), surfaces.map(&:to_s))
    end
  end

  # Collects `state`/`on` declarations inside `statechart`.
  class StatechartBuilder
    attr_reader :states, :transitions

    def initialize(_id)
      @states = []
      @transitions = []
    end

    def state(id, initial: false, final: false)
      @states << StateDef.new(id.to_s, initial, final)
    end

    def on(from_state, event, to:)
      @transitions << Transition.new(from_state.to_s, event.to_s, to.to_s)
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
