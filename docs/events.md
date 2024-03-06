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
| `battery_level` | `float` | Battery level % of the device. |
| `previous_battery_level` | `float` | Previous battery level % of the device. |
| `reminder` | `bool` | Returns true if the event was raised by a service call, false if it's from a device event. |

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
| `battery_level` | `float` | Current battery level % of the device. |
| `previous_battery_level` | `float` | Previous battery level % of the device. |

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

## Battery Not Reported
`battery_notes_battery_not_reported`

This is fired from the [check_battery_last_reported](./services.md/#check_battery_last_reported) service call for each device that has not reported its battery level for the number of days specified in the service call.

The service can raise multiple events quickly so when using with an automation it's important to use the `mode: queued` to handle these.

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `device_name` | `string` | The device name. |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |
| `battery_last_reported` | `datetime` | The datetime the battery was last reported. |
| `battery_last_reported_days` | `int` | The number of days since the battery was last reported. |
| `battery_last_reported_level` | `float` | The level of the battery when it was last reported. |

### Automation Example

See others in the [community contributions](./community.md)

Note this cannot be run manually as it examines event triggers.

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