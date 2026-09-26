# frozen_string_literal: true

# Smart kettle UX contract example — compiled by `ruby bin/ux-dsl` to
# smart-kettle.ux.json, which is asserted identical in tests.

UX.design "smart-kettle" do
  persona :busy_parent, goals: ["hot water fast", "no watching the kettle"],
          context: "morning rush with kids",
          pains: ["forgot boiling water", "scald worry"]

  job :boil,
      functional: "boil 500 ml of water in under 3 minutes",
      emotional: "confidence it will not overflow or be forgotten",
      social: "a tidy, quiet kitchen while guests arrive",
      importance: 9, satisfaction: 4

  job :keep_warm,
      functional: "hold water at 80°C for 30 minutes",
      emotional: "trust that a second cup is ready",
      social: "hospitality without re-boiling in front of guests",
      importance: 6, satisfaction: 5

  journey :morning do
    stage :fill, touchpoints: %w[lid handle spout], emotion: 3,
          pain_points: ["lid hinge pinches fingers"], surfaces: %w[kettle_body]
    stage :boil, touchpoints: %w[button led beep], emotion: 4,
          surfaces: %w[hardware_button status_led]
    stage :pour, touchpoints: %w[handle spout], emotion: 5,
          surfaces: %w[kettle_body]
    stage :forgot, touchpoints: %w[app_notification], emotion: 2,
          pain_points: ["no reminder when water cools"],
          surfaces: %w[mobile_app]
  end

  service_blueprint frontstage: %w[button_press led_feedback beep],
                    backstage: %w[thermostat_control boil_detection],
                    support: %w[firmware_update_service]

  statechart :power do
    state :idle, initial: true
    state :heating
    state :keep_warm
    state :done, final: true
    on :idle, :press, to: :heating
    on :heating, :boiled, to: :done
    on :heating, :keep_warm_selected, to: :keep_warm
    on :keep_warm, :timeout, to: :idle
    on :done, :lifted, to: :idle
  end

  surface :kettle_body, layer: :industrial_design, name: "kettle body & handle"
  surface :hardware_button, layer: :hardware, name: "single boil button"
  surface :status_led, layer: :circuit, name: "ring status LED"
  surface :thermostat, layer: :firmware, name: "boil/keep-warm controller"
  surface :mobile_app, layer: :smartphone_app, name: "companion app"

  core_experience "one press, walk away — hot water that waits for you"
  implementation_spec "plastic vs steel body", "beep vs chime", "app optional"

  qcd quality: :high, cost: :medium, delivery: :fast,
      rationale: "core_experience is the boil job; app features stay optional"
end
