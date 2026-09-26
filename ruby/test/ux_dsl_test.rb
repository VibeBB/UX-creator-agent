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
    assert_equal({ "from" => "idle", :event => "press", :to => "heating" },
                 chart[:transitions].first)
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
