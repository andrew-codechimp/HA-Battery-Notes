# Community Contributions

## UI

### Battery State Card
Using the excellent [Battery State Card](https://github.com/maxwroc/battery-state-card) by maxwroc you can easily display devices with their batteries required where the devices battery threshold indicates it's low and show be replaced.

```yaml
type: custom:battery-state-card
secondary_info: '{attributes.battery_type_and_quantity}'
round: 0
filter:
  include:
    - name: entity_id
      value: '*_battery_plus'
  exclude:
    - name: attributes.battery_low
      value: false
bulk_rename:
  - from: "Battery+"      
sort:
  - state
```

## Automations

### Battery Low Notification
Raise a persistent notification when a battery is low, dismiss when it's not low

```yaml
alias: Battery Low Notification
description: Battery Low Notification with auto dismiss
trigger:
  - platform: event
    event_type: battery_notes_battery_threshold
    event_data:
      battery_low: true
    id: low
    alias: Battery went low
  - platform: event
    event_type: battery_notes_battery_threshold
    event_data:
      battery_low: false
    id: high
    alias: Battery went high
condition: []
action:
  - choose:
      - conditions:
          - condition: trigger
            id:
              - low
        sequence:
          - service: persistent_notification.create
            data:
              title: |
                {{ trigger.event.data.device_name }} Battery Low
              notification_id: "{{ trigger.event.data.device_id }}"
              message: >
                The device has a battery level of {{
                trigger.event.data.battery_level }}% {{ '\n' -}} You need {{
                trigger.event.data.battery_quantity }}× {{
                trigger.event.data.battery_type }}
      - conditions:
          - condition: trigger
            id:
              - high
        sequence:
          - service: persistent_notification.dismiss
            data:
              notification_id: "{{ trigger.event.data.device_id }}"
mode: queued
```

### Check Battery Low daily reminder
Call the check battery low service every day to raise events for those that are still low.  
To be used in conjunction with a [Battery Low Notification](community.md/#battery-low-notification) or similar.

```yaml
alias: Daily Battery Low Check
description: Check whether a battery is low
trigger:
  - platform: time
    at: "09:00:00"
condition: []
action:
  - service: battery_notes.check_battery_low
mode: single
```

### Check Battery Low weekly reminder
Weekly reminders are a little trickier, you will need to create a [Schedule Helper](https://www.home-assistant.io/integrations/schedule/) for when you want the battery check to occur then use this automation for when the helper is on.  
Below I am referencing a schedule helper called maintenance which I have set to come on weekly.  
To be used in conjunction with a [Battery Low Notification](community.md/#battery-low-notification) or similar.  

```yaml
alias: Battery Low Check
description: Check whether a battery is low
trigger:
  - platform: state
    entity_id:
      - schedule.maintenance
    to: "on"
condition: []
action:
  - service: battery_notes.check_battery_low
    data: {}
mode: single
```

### Battery Replaced
Mark a battery as replaced when there is an increase in battery level.

```yaml
alias: Battery Replaced
description: Battery Replaced
trigger:
  - platform: event
    event_type: battery_notes_battery_increased
condition: []
action:
  - service: battery_notes.set_battery_replaced
    data:
      device_id: "{{ trigger.event.data.device_id }}"
mode: queued
```

Send a notification when there is an increase in battery level.

```yaml
alias: Battery Increased Notification
description: Battery Increased Notification
trigger:
  - platform: event
    event_type: battery_notes_battery_increased
condition: []
action:
  - service: persistent_notification.create
    data:
      title: |
        {{ trigger.event.data.device_name }} Battery Increased
      message: >
        The device has increased its battery level, you probably want to mark it as replaced
mode: queued
```

### Check Battery Last Reported Daily
Call the check battery last reported service every day to raise events for those not reported in the last two days.  
To be used in conjunction with a Battery Not Reported automation.

```yaml
alias: Daily Battery Not Reported Check
description: Check whether a battery has reported
trigger:
  - platform: time
    at: "09:00:00"
condition: []
action:
  - service: battery_notes.check_battery_last_reported
    data:
      days_last_reported: 2
mode: single
```

### Battery Not Reported
Respond to events raised by the check_battery_last_reported service and create notifications.

Note this cannot be run manually as it examines event triggers, use it with the [Check Battery Last Reported Daily](community.md/#check-battery-last-reported-daily) or similar.

```yaml
alias: Battery Not Reported
description: Battery not reported
trigger:
  - platform: event
    event_type: battery_notes_battery_not_reported
condition: []
action:
  - service: persistent_notification.create
    data:
      title: |
        {{ trigger.event.data.device_name }} Battery Not Reported
      message: >
        The device has not reported its battery level for {{
        trigger.event.data.battery_last_reported_days }} days {{ '\n'
        -}} Its last reported level was {{
        trigger.event.data.battery_last_reported_level }}% {{ '\n' -}} You need
        {{ trigger.event.data.battery_quantity }}× {{
        trigger.event.data.battery_type }}
mode: queued
max: 30
```

## Automation Tips

To call the battery replaced service from an entity trigger you will need the device_id, here's an easy way to get this

```yaml
action:
  - service: battery_notes.set_battery_replaced
    data:
      device_id: "{{ device_id(trigger.entity_id) }}"
```

## Blueprints

[Blueprints](https://www.home-assistant.io/docs/automation/using_blueprints/) are an excellent way to get you up and running with the integration quickly. They can also be used as a guide for setting up new automations which you can tailor to your needs. 

### Battery Threshold
[Install blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fandrew-codechimp%2FHA-Battery-Notes%2Fmain%2Fdocs%2Fblueprints%2Fbattery_notes_battery_threshold.yaml) | [Source](https://raw.githubusercontent.com/andrew-codechimp/HA-Battery-Notes/main/docs/blueprints/battery_notes_battery_threshold.yaml)

This blueprint will allow notifications to be raised and/or custom actions to be performed when the battery threshold is met.
It is extended from the example Battery Low Notification automation yaml above for those who'd prefer an easy way to get started.


### Battery Replaced
[Install blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fandrew-codechimp%2FHA-Battery-Notes%2Fmain%2Fdocs%2Fblueprints%2Fbattery_notes_battery_replaced.yaml) | [Source](https://raw.githubusercontent.com/andrew-codechimp/HA-Battery-Notes/main/docs/blueprints/battery_notes_battery_replaced.yaml)

This blueprint will automatically update the battery replaced sensor and custom actions to be performed when the battery increases.
It is extended from the example Battery Replaced automation yaml above for those who'd prefer an easy way to get started.

### Battery Not Reported
[Install blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fandrew-codechimp%2FHA-Battery-Notes%2Fmain%2Fdocs%2Fblueprints%2Fbattery_notes_battery_not_reported.yaml) | [Source](https://raw.githubusercontent.com/andrew-codechimp/HA-Battery-Notes/main/docs/blueprints/battery_notes_battery_not_reported.yaml)

This blueprint will allow notifications to be raised and/or custom actions to be performed when the battery not reported event is fired.  
It is extended from the example Battery Not Reported automation yaml above for those who'd prefer an easy way to get started.  
You must trigger the check_battery_not_reported service via an automation to raise events, see [Check Battery Last Reported Daily](community.md/#check-battery-last-reported-daily) above.

## Contributing  
If you want to contribute then [fork the repository](https://github.com/andrew-codechimp/HA-Battery-Notes), edit this page which is in the docs folder and submit a pull request.
