# Events

The following events are raised by the integration. These events can be used within automations.

## Battery Threshold
`battery_notes_battery_threshold`

This is fired when a device within Battery Notes has a battery level changed to either below or above the device specific or global threshold.

You can use this to send notifications in your preferred method.  An example automation below displays a persistent notification.  

!!! note

    Battery Threshold events are only raised when the device has a Battery+ entity or a [Battery Low Template](./index.md/#battery-low-template) is added to the Battery Notes configuration.

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `source_entity_id` | `string` | The entity id of the sensor associated with the battery note. |
| `device_name` | `string` | The device name (or associated sensor name if no device), if you have renamed the battery note it will use this name. |
| `battery_low` | `bool` | Returns true if the battery has gone below the threshold, false when the battery has returned above the threshold. **Your automations will almost certainly want to examine this value and set/clear notifications or other indicators.** |
| `battery_low_threshold` | `string` | Battery low threshold (or global if 0). |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |
| `battery_level` | `float` | Battery level % of the device. |
| `previous_battery_level` | `float` | Previous battery level % of the device. |
| `battery_last_replaced` | `datetime` | The date the battery was last replaced. |
| `reminder` | `bool` | Returns true if the event was raised by an action, false if it's from a device event. |  

### Automation Example

See others in the [community contributions](./community.md)

```yaml
alias: Battery Low Notification
description: Battery Low Notification with auto dismiss
mode: queued
triggers:
  - trigger: event
    event_type: battery_notes_battery_threshold
    event_data:
      battery_low: true
    id: low
    alias: Battery went low
  - trigger: event
    event_type: battery_notes_battery_threshold
    event_data:
      battery_low: false
    id: high
    alias: Battery went high
conditions: []
actions:
  - choose:
      - conditions:
          - condition: trigger
            id:
              - low
        sequence:
          - action: persistent_notification.create
            data:
              title: |
                {{ trigger.event.data.device_name }} Battery Low
              notification_id: "{{ trigger.event.data.device_id }}-{{ trigger.event.data.source_entity_id }}"
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
          - action: persistent_notification.dismiss
            data:
              notification_id: "{{ trigger.event.data.device_id }}-{{ trigger.event.data.source_entity_id }}"
```

## Battery Increased
`battery_notes_battery_increased`

This is fired when a device within Battery Notes has a battery level increased above the battery_increase_threshold (default 25%) if not changed within [configuration setting](./configuration.md).

It deliberately does not update the battery_replaced sensor allowing you to choose how you want to handle this.  The increase theshold allows for detecting/handling of partially charged batteries rather than just full batteries.  
An example automation below shows how to update the battery_replaced.

!!! note

    Battery Increased events are only raised when the device has a Battery+ entity or a [Battery Low Template](./index.md/#battery-low-template) is added to the Battery Notes configuration.

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `source_entity_id` | `string` | The entity id of the sensor associated with the battery note. |
| `device_name` | `string` | The device name (or associated sensor name if no device), if you have renamed the battery note it will use this name. |
| `battery_low` | `bool` | Returns true if the battery has gone below the threshold, false when the battery has returned above the threshold. |
| `battery_low_threshold` | `string` | Battery low threshold (or global if 0). |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |
| `battery_level` | `float` | Current battery level % of the device. |
| `previous_battery_level` | `float` | Previous battery level % of the device. |
| `battery_last_replaced` | `datetime` | The date the battery was last replaced. |

### Automation Example

See others in the [community contributions](./community.md)

```yaml
alias: Battery Replaced
description: Battery Replaced
mode: queued
triggers:
  - trigger: event
    event_type: battery_notes_battery_increased
conditions: []
actions:
  - action: battery_notes.set_battery_replaced
    data:
      device_id: "{{ trigger.event.data.device_id }}"
      source_entity_id: "{{ trigger.event.data.source_entity_id }}"

```

## Battery Not Reported
`battery_notes_battery_not_reported`

This is fired from the [check_battery_last_reported](./actions.md/#check-battery-last-reported) action call for each device that has not reported its battery level for the number of days specified in the action call.

The action can raise multiple events quickly so when using with an automation it's important to use the `mode: queued` to handle these.

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `source_entity_id` | `string` | The entity id of the sensor associated with the battery note. |
| `device_name` | `string` | The device name (or associated sensor name if no device), if you have renamed the battery note it will use this name. |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |
| `battery_last_reported` | `datetime` | The datetime the battery was last reported. |
| `battery_last_reported_days` | `int` | The number of days since the battery was last reported. |
| `battery_last_reported_level` | `float` | The level of the battery when it was last reported. |
| `battery_last_replaced` | `datetime` | The date the battery was last replaced. |

### Automation Example

See others in the [community contributions](./community.md)

Note this cannot be run manually as it examines event triggers.

```yaml
alias: Battery Not Reported
description: Battery not reported
mode: queued
max: 30
triggers:
  - trigger: event
    event_type: battery_notes_battery_not_reported
conditions: []
actions:
  - action: persistent_notification.create
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
```

## Battery Replaced
`battery_notes_battery_replaced`

This is fired when the battery is replaced, either by a button press or the action.

This can be useful for adding batteries to a shopping list or inventory system.

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `source_entity_id` | `string` | The entity id of the sensor associated with the battery note. |
| `device_name` | `string` | The device name (or associated sensor name if no device), if you have renamed the battery note it will use this name. |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |

### Automation Example

Note this cannot be run manually as it examines event triggers.

```yaml
alias: Battery Replaced
description: Battery replaced
mode: queued
max: 30
triggers:
  - trigger: event
    event_type: battery_notes_battery_replaced
conditions: []
actions:
  - action: persistent_notification.create
    data:
      title: |
        {{ trigger.event.data.device_name }} Battery Replaced
      message: >
        You just used {{ trigger.event.data.battery_type_and_quantity }} batteries
```

## Battery Not Replaced
`battery_notes_battery_not_replaced`

This is fired from the [check_battery_last_replaced](./actions.md/#check-battery-last-replaced) action call for each device that has not had its battery replaced for the number of days specified in the action call.

If you do not want an event raised for certain devices such as rechargeable then disable the battery_last_replaced sensor entity for that device.

The action can raise multiple events quickly so when using with an automation it's important to use the `mode: queued` to handle these.

| Attribute | Type | Description |
|-----------|------|-------------|
| `device_id` | `string` | The device id of the device. |
| `source_entity_id` | `string` | The entity id of the sensor associated with the battery note. |
| `device_name` | `string` | The device name (or associated sensor name if no device), if you have renamed the battery note it will use this name. |
| `battery_type_and_quantity` | `string` | Battery type & quantity. |
| `battery_type` | `string` | Battery type. |
| `battery_quantity` | `int` | Battery quantity. |
| `battery_last_reported` | `datetime` | The datetime the battery was last reported. |
| `battery_last_reported_level` | `float` | The level of the battery when it was last reported. |
| `battery_last_replaced` | `datetime` | The date the battery was last replaced. |
| `battery_last_replaced_days` | `int` | The number of days since the battery was last replaced. |

### Automation Example

See others in the [community contributions](./community.md)

Note this cannot be run manually as it examines event triggers.

```yaml
alias: Battery Not Replaced
description: Battery not replaced
mode: queued
max: 30
triggers:
  - trigger: event
    event_type: battery_notes_battery_not_replaced
conditions: []
actions:
  - action: persistent_notification.create
    data:
      title: |
        {{ trigger.event.data.device_name }} Battery Not Replaced
      message: >
        The device has not been replaced for {{ 
        trigger.event.data.battery_last_replaced_days }} days {{ '\n' 
        -}} Its last replaced date was {{ trigger.event.data.battery_last_replaced 
        | as_timestamp | timestamp_custom('%Y-%m-%d', true)}} {{ '\n' -}} You need 
        {{ trigger.event.data.battery_quantity }}× {{ trigger.event.data.battery_type }}        
```
