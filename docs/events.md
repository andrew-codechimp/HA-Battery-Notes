# Events

The following events are raised by the integration. These events can be used within automations.

## Battery Threshold
`battery_notes_battery_threshold`

This is fired when any device within Battery Notes has a battery level changed to either below or above the device specific or global threshold.

You can use this to send notifications in your preferred method.  An example automation below displays a persistent notification.  

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `device_name` | `string` | The device name. |
| `battery_low` | `bool` | Returns true if the battery has gone below the threshold, false when the battery has returned above the threshold. **Your automations will almost certainly want to examine this value and set/clear notifications or other indicators.** |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |
| `battery_level` | `int` | Battery level % of the device. |
| `previous_battery_level` | `int` | Previous battery level % of the device. |

### Automation Example

See others in the [community contributions](./community.md)

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
                trigger.event.data.battery_quantity }}x {{
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

## Battery Increased
`battery_notes_battery_increased`

This is fired when any device within Battery Notes has a battery level increased above the battery_increase_threshold (default 25%) if not changed within [configuration setting](./configuration.md).

It deliberately does not update the battery_replaced sensor allowing you to choose how you want to handle this.  The increase theshold allows for detecting/handling of partially charged batteries rather than just full batteries.  
An example automation below shows how to update the battery_replaced.

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `device_name` | `string` | The device name. |
| `battery_low` | `bool` | Returns true if the battery has gone below the threshold, false when the battery has returned above the threshold. |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |
| `battery_level` | `int` | Current battery level % of the device. |
| `previous_battery_level` | `int` | Previous battery level % of the device. |

### Automation Example

See others in the [community contributions](./community.md)

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