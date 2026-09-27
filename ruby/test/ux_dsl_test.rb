# frozen_string_literal: true

require "minitest/autorun"
require "json"

$LOAD_PATH.unshift(File.expand_path("../lib", __dir__))
require "ux_dsl"

# Parity checks: the DSL output validates against the contract shape.
class UxDslTest < Minitest::Test
  def design
    UX.design "kettle" do
      persona :busy_parent, goals: ["hot water fast"], context: "morning rush"
      job :boil, functional: "boil 500ml in <3min", emotional: "confidence it will not overflow",
                 social: "kitchen looks tidy", importance: 9, satisfaction: 4
      journey :morning do
        stage :fill, touchpoints: %w[lid handle], emotion: 3
        stage :boil, touchpoints: %w[button led], emotion: 4, surfaces: %w[hardware_button]
      end
      statechart :power do
        state :idle, initial: true
        state :heating
        on :idle, :press, to: :heating
        on :heating, :boiled, to: :idle
      end
      surface :hardware_button, layer: :hardware
      core_experience "one press, walk away"
      qcd quality: :high, cost: :medium, delivery: :fast
    end
  end

  def test_schema_header
    h = design.to_h
    assert_equal 1, h[:schema_version]
    assert_equal "ux-creator", h[:system]
    assert_equal "kettle", h[:product][:name]
  end

  def test_jobs_and_scores
    job = design.to_h[:jobs].first
    assert_equal 9, job[:importance]
    assert_equal 4, job[:satisfaction]
    refute_empty job[:emotional]
  end

  def test_statechart_shape
    chart = design.to_h[:statecharts].first
    assert_equal 2, chart[:states].size
    assert chart[:states].first[:initial]
    assert_equal({ "from" => "idle", :event => "press", :to => "heating",
                   :guard => "", :actions => [] },
                 chart[:transitions].first)
  end

  def test_richer_statechart_fields
    h = design.to_h
    state = h[:statecharts].first[:states].first
    assert_equal "", state[:surface]
    assert_equal [], state[:entry]
    assert_equal "use", h[:journeys].first[:stages].first[:kind]
    assert_equal [], h[:journeys].first[:stages].first[:jobs]
  end

  def test_stage_jobs_emitted
    d = UX.design("demo") do
      journey :j do
        stage :s, emotion: 4, jobs: %i[boil keep_warm]
      end
    end
    stage = d.to_h[:journeys].first[:stages].first
    assert_equal %w[boil keep_warm], stage[:jobs]
  end

  def test_feedback_and_loops
    d = UX.design("demo") do
      surface :led, layer: :circuit
      journey :j do
        stage :s, touchpoints: %w[btn], emotion: 4
      end
      statechart :sc do
        state :a, initial: true
        state :b, final: true
        on :a, :go, to: :b, guard: "ready", actions: %w[led_on]
      end
      feedback :fb, trigger: :go, surface: :led, modality: :visual, latency_ms: 50
      experience_loop :l, steps: %w[go], reward: "done", cadence: :daily
    end
    h = d.to_h
    fb = h[:feedback].first
    assert_equal "visual", fb[:modality]
    assert_equal 50, fb[:latency_ms]
    assert_equal true, h[:transitions] if h[:transitions]
    t = h[:statecharts].first[:transitions].first
    assert_equal "ready", t[:guard]
    assert_equal %w[led_on], t[:actions]
    loop_h = h[:loops].first
    assert_equal "daily", loop_h[:cadence]
    assert_equal %w[go], loop_h[:steps]
  end

  def test_bad_loop_cadence_rejected
    assert_raises(UX::DesignError) do
      UX.design("x") { experience_loop :l, steps: %w[a], cadence: :hourly }
    end
  end

  def test_bad_stage_kind_rejected
    assert_raises(UX::DesignError) do
      UX.design("x") do
        journey(:j) { stage :s, kind: :sideways, emotion: 3 }
      end
    end
  end

  def test_bad_layer_rejected
    assert_raises(UX::DesignError) do
      UX.design("x") { surface :s, layer: :hologram }
    end
  end

  def test_bad_qcd_rejected
    assert_raises(UX::DesignError) do
      UX.design("x") { qcd quality: :perfect, cost: :low, delivery: :fast }
    end
  end

  def test_compiled_example_matches_committed_contract
    root = File.expand_path("../..", __dir__)
    rb = File.join(root, "examples/smart-kettle/smart-kettle.ux.rb")
    json_path = File.join(root, "examples/smart-kettle/smart-kettle.ux.json")
    skip "example files absent" unless File.exist?(rb) && File.exist?(json_path)
    compiled = JSON.parse(JSON.generate(UX.compile_file(rb).to_h), symbolize_names: true)
    committed = JSON.parse(File.read(json_path), symbolize_names: true)
    assert_equal committed, compiled
  end
end
