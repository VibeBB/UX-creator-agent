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
    stage :pair_app, kind: :onboard, touchpoints: %w[app_pairing], emotion: 3,
          pain_points: ["pairing needs account"], surfaces: %w[mobile_app]
    stage :fill, touchpoints: %w[lid handle spout], emotion: 3,
          pain_points: ["lid hinge pinches fingers"], surfaces: %w[kettle_body],
          jobs: %i[boil]
    stage :boil, touchpoints: %w[button led beep], emotion: 4,
          surfaces: %w[hardware_button status_led], jobs: %i[boil]
    stage :pour, touchpoints: %w[handle spout], emotion: 5,
          surfaces: %w[kettle_body], jobs: %i[boil]
    stage :forgot, touchpoints: %w[app_notification], emotion: 2,
          pain_points: ["no reminder when water cools"],
          surfaces: %w[mobile_app], jobs: %i[keep_warm]
  end

  service_blueprint frontstage: %w[button_press led_feedback beep],
                    backstage: %w[thermostat_control boil_detection],
                    support: %w[firmware_update_service]

  statechart :power do
    state :idle, initial: true, surface: :hardware_button,
          description: "kettle idle, LED off"
    state :heating, surface: :status_led, entry: %w[led_pulse],
          description: "water heating, LED pulsing"
    state :keep_warm, surface: :status_led,
          description: "holding temperature, LED steady"
    state :done, final: true
    on :idle, :press, to: :heating
    on :heating, :boiled, to: :done, guard: "temp >= 100", actions: %w[beep]
    on :heating, :boiled, to: :keep_warm, guard: "keep_warm_armed"
    on :heating, :keep_warm_selected, to: :keep_warm
    on :keep_warm, :timeout, to: :idle
    on :done, :lifted, to: :idle
  end

  surface :kettle_body, layer: :industrial_design, name: "kettle body & handle"
  surface :hardware_button, layer: :hardware, name: "single boil button"
  surface :status_led, layer: :circuit, name: "ring status LED"
  surface :thermostat, layer: :firmware, name: "boil/keep-warm controller"
  surface :buzzer, layer: :circuit, name: "piezo beeper"
  surface :mobile_app, layer: :smartphone_app, name: "companion app"

  control :boil_button, surface: :hardware_button, kind: :button,
          size_mm: [14, 14], touchpoint: "button"
  control :app_boil_tap, surface: :mobile_app, kind: :touch,
          size_mm: [9, 9], touchpoint: "app_pairing",
          fg: "#FFFFFF", bg: "#0057D9"

  feedback :led_boiling, trigger: :press, surface: :status_led,
           modality: :visual, latency_ms: 50,
           description: "LED starts pulsing within one blink of the press"
  feedback :beep_done, trigger: :boiled, surface: :buzzer,
           modality: :audio, latency_ms: 100,
           description: "two-tone done chime at boil detection"
  feedback :app_reminder, trigger: :app_notification, surface: :mobile_app,
           modality: :text, latency_ms: 3000, progress_indicator: true,
           description: "push card counts down cooling time"

  experience_loop :morning_brew,
                  steps: %w[press boiled lifted],
                  reward: "hot water without waiting", cadence: :daily

  core_experience "one press, walk away — hot water that waits for you"
  implementation_spec "plastic vs steel body", "beep vs chime", "app optional"

  qcd quality: :high, cost: :medium, delivery: :fast,
      rationale: "core_experience is the boil job; app features stay optional"
end
