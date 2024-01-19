# Events

The following events are raised by the integration. These events can be used within automations.

## Battery Threshold

`battery_notes_battery_threshold`

This is fired when any device within Battery Notes has a battery level changed to either below or above the device specific or global threshold.

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `device_name` | `string` | The device name. |
| `battery_low` | `bool` | Returns True if the battery has gone below the threshold, false when the battery has returned above the threshold. **Your automations will almost certainly want to examine this value and set/clear notifications or other indicators.** |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |
| `battery_level` | `int` | Battery level % of the device. |

### Automation Example

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
