# Triggers

## Battery Replaced

`battery_notes.battery_replaced`

The **Battery replaced** trigger is available under **Battery Notes** in the
automation editor. It fires when a battery is marked as replaced by the
[replacement button](./entities.md#battery-replaced) or the
[Set Battery Replaced action](./actions.md#set-battery-replaced), at the same
time as the [Battery Replaced event](./events.md#battery-replaced).

### Targets

The target is optional. Omit it to trigger on replacements for all battery
notes:

``` yaml
triggers:
  - trigger: battery_notes.battery_replaced
```

The target supports entities, devices, areas, floors, and labels. Select a
Battery Notes entity to target its battery note, or a device to target all
battery notes associated with that device. Source entities can also be targeted
in YAML.

Targets are resolved when each event arrives, so changes to area, floor, and
label membership are applied automatically.

An explicitly empty target (`target: {}`) matches no battery notes.

The trigger also fires when an action records a replacement date in the past.
It does not fire just because a battery level increases or a replacement
timestamp changes.

### Trigger Data

| Member                              | Type               | Description                                                            |
| ----------------------------------- | ------------------ | ---------------------------------------------------------------------- |
| `trigger.device_id`                 | `string`           | The source device ID, or an empty string for a standalone entity note. |
| `trigger.source_entity_id`          | `string`           | The source entity ID, or an empty string for a device note.            |
| `trigger.area_name`                 | `string` or `null` | The area name associated with the source device or entity.             |
| `trigger.device_name`               | `string`           | The battery note's name.                                               |
| `trigger.battery_type_and_quantity` | `string`           | The battery type and quantity, for example `2× AA`.                    |
| `trigger.battery_type`              | `string`           | The battery type.                                                      |
| `trigger.battery_quantity`          | `int`              | The battery quantity.                                                  |
| `trigger.note`                      | `string`           | The note added in the battery note configuration.                      |

### Automation Example

``` yaml
alias: Battery Replaced in Kitchen
mode: queued
triggers:
  - trigger: battery_notes.battery_replaced
    target:
      area_id: kitchen
actions:
  - action: persistent_notification.create
    data:
      title: "{{ trigger.device_name }} Battery Replaced"
      message: "You just used {{ trigger.battery_type_and_quantity }} batteries"
```
