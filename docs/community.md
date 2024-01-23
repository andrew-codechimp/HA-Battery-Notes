# Community Contributions

## Automations

### Battery Low Notification (Beta Only)

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
  - platform: event
    event_type: battery_notes_battery_threshold
    event_data:
      battery_low: false
    id: notlow
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
                trigger.event.data.battery_quantity }}x {{
                trigger.event.data.battery_type }}
      - conditions:
          - condition: trigger
            id:
              - notlow
        sequence:
          - service: persistent_notification.dismiss
            data:
              notification_id: "{{ trigger.event.data.device_id }}"
mode: queued
```

### Battery Replaced (Beta Only)

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

## Automation Tips

To call the battery replaced service from an entity trigger you will need the device_id, here's an easy way to get this

```yaml
action:
  - service: battery_notes.set_battery_replaced
    data:
      device_id: "{{ device_id(trigger.entity_id) }}"
```

## Contributing

If you want to contribute then [fork the repository](https://github.com/andrew-codechimp/HA-Battery-Notes), edit this page which is in the docs folder and submit a pull request.
