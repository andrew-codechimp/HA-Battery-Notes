# Blueprints

[Blueprints](https://www.home-assistant.io/docs/automation/using_blueprints/) are an excellent way to get you up and running with the integration quickly. They can also be used as a guide for setting up new automations which you can tailor to your needs.

### Battery Threshold

[Install blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fandrew-codechimp%2FHA-Battery-Notes%2Fmain%2Fdocs%2Fblueprints%2Fbattery_notes_battery_threshold.yaml) | [Source](https://raw.githubusercontent.com/andrew-codechimp/HA-Battery-Notes/main/docs/blueprints/battery_notes_battery_threshold.yaml)

This blueprint will allow notifications to be raised and/or custom actions to be performed when the battery threshold is met.  
It is extended from the [community Battery Low Notification automation yaml](community.md/#battery-low-notification) for those who'd prefer an easy way to get started.

### Battery Replaced

[Install blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fandrew-codechimp%2FHA-Battery-Notes%2Fmain%2Fdocs%2Fblueprints%2Fbattery_notes_battery_replaced.yaml) | [Source](https://raw.githubusercontent.com/andrew-codechimp/HA-Battery-Notes/main/docs/blueprints/battery_notes_battery_replaced.yaml)

This blueprint will automatically update the battery replaced sensor and custom actions to be performed when the battery increases.  
It is extended from the [community Battery Replaced automation yaml](community.md/#battery-replaced) for those who'd prefer an easy way to get started.

### Battery Not Reported

[Install blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fandrew-codechimp%2FHA-Battery-Notes%2Fmain%2Fdocs%2Fblueprints%2Fbattery_notes_battery_not_reported.yaml) | [Source](https://raw.githubusercontent.com/andrew-codechimp/HA-Battery-Notes/main/docs/blueprints/battery_notes_battery_not_reported.yaml)

This blueprint will allow notifications to be raised and/or custom actions to be performed when the battery not reported event is fired.  
It is extended from the [community Battery Not Reported automation yaml](community.md/#battery-not-reported) for those who'd prefer an easy way to get started.

!!! info

    You must trigger the check_battery_not_reported action via an automation to raise events, see [Check Battery Last Reported Daily](community.md/#check-battery-last-reported-daily).
