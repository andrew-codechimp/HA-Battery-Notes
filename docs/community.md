# Community Contributions

## Automations

### Battery Low Notification

Raise a persistent notification when a battery is low.

```yaml
alias: Battery Low Notification
description: Battery Low Notification
trigger:
  - platform: event
    event_type: battery_notes_battery_threshold
    event_data:
      battery_low: true
condition: []
action:
  - service: persistent_notification.create
    data:
      title: |
        {{ trigger.event.data.device_name }} Battery Low
      message: >
        The device has a battery level of {{ trigger.event.data.battery_level
        }}% {{ '\n' -}} You need {{ trigger.event.data.battery_quantity }}x {{
        trigger.event.data.battery_type }}
mode: queued
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

### Battery Replaced Repair Notification

If you are using the excellent [Spook](https://github.com/frenck/spook) HACS integration you can create a Repair notification in home assistant with a link to the device to confirm the battery has been replaced.

```yaml
alias: Battery Replaced Repair Notification
description: Battery Replaced using Spook
trigger:
  - platform: event
    event_type: battery_notes_battery_increased
condition: []
action:
  - service: battery_notes.set_battery_replaced
    data:
      device_id: "{{ trigger.event.data.device_id }}"
    enabled: false
  - service: repairs.create
    metadata: {}
    data:
      title: Battery Replaced
      issue_id: "{{ trigger.event.data.device_id }}"
      domain: battery_notes
      persistent: true
      description: >-
        It seems like the battery was replaced on [{{
        trigger.event.data.device_name }}](./devices/device/{{
        trigger.event.data.device_id }})  

        Clicking Submit will clear this repair.
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
