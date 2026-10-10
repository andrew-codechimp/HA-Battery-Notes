# Triggers

## Battery Low

`battery_notes.battery_became_low`

The **Battery became low** trigger is available under **Battery Notes** in the
automation editor. It listens to the [Battery Threshold event](./events.md#battery-threshold)
and fires when `battery_low` is true, according to the reminder option below.
Events indicating that a battery is no longer low are ignored.

The trigger uses the battery note's existing low-state detection, including
its device-specific or global threshold, battery low template, or binary
battery source. For percentage sources, a level is low when it is **below**
the threshold. The trigger does not set a separate threshold.

### Battery Low Targets

The target is optional. Omit it to trigger for all battery notes:

``` yaml
triggers:
  - trigger: battery_notes.battery_became_low
```

The trigger supports the same [targets as Battery Replaced](#targets):
entities, devices, areas, floors, and labels. Targets are resolved for each
event, so membership changes are applied automatically. An explicitly empty
target (`target: {}`) matches no battery notes.

### Reminders

Use the **Reminders** option in the automation editor, or `options.reminder`
in YAML, to choose which low battery events trigger the automation:

| Option | YAML value | Behavior |
| --- | --- | --- |
| Exclude reminders | `exclude` | Trigger when a battery becomes low. Ignore reminders. |
| Reminders only | `only` | Trigger only on reminders raised by [Check Battery Low](./actions.md#check-battery-low). |
| All (default) | `all` | Trigger on both low battery transitions and reminders. |

The [Check Battery Low action](./actions.md#check-battery-low) raises a reminder
for each low battery note when `raise_events` is true (the default). To send
regular reminders, schedule that action in a separate automation. The trigger
does not schedule reminders itself.

Repeated readings while a battery remains low do not trigger a new transition.
Initialization and unavailable readings do not generate low battery events.

### Battery Low Trigger Data

The trigger exposes the same [identity and battery metadata as Battery Replaced](#trigger-data),
plus these fields from the threshold event. Access fields directly, for example
`trigger.battery_level` or `trigger.reminder`.

| Member | Type | Description |
| --- | --- | --- |
| `trigger.battery_low` | `bool` | Always true for this trigger. |
| `trigger.battery_low_threshold` | `int` | The effective battery low threshold. |
| `trigger.battery_increase_threshold` | `int` | The effective battery increase threshold. |
| `trigger.battery_level` | `float` or `null` | The current battery percentage. |
| `trigger.previous_battery_level` | `float` or `null` | The previous battery percentage. |
| `trigger.battery_last_replaced` | `datetime` or `null` | The recorded replacement date. |
| `trigger.reminder` | `bool` | True for an action reminder, false for a low-state transition. |

Binary and low-template transitions use nominal levels of 0 for low and 100 for
healthy. Reminder events preserve the current event data; battery levels can be
null when no percentage is available.

### Battery Low Automation Example

``` yaml
alias: Battery Low in Kitchen
mode: queued
triggers:
  - trigger: battery_notes.battery_became_low
    target:
      area_id: kitchen
    options:
      reminder: all
actions:
  - action: persistent_notification.create
    data:
      title: "{{ trigger.device_name }} Battery Low"
      message: "You need {{ trigger.battery_type_and_quantity }} batteries"
      notification_id: "{{ trigger.device_id }}-{{ trigger.source_entity_id }}"
```

## Battery No Longer Low

`battery_notes.battery_no_longer_low`

The **Battery no longer low** trigger listens to the
[Battery Threshold event](./events.md#battery-threshold) and fires when
`battery_low` is false. For percentage sources, this happens when the battery
returns to or above its effective low threshold. Binary and low-template sources
trigger when their low state becomes false.

It supports the same [targets as Battery Replaced](#targets). Omit the target
to include all battery notes; `target: {}` matches none. Target membership is
resolved for each event.

This trigger has no reminder option. Low battery transitions and reminders
raised by Check Battery Low do not trigger it. Repeated healthy readings,
initialization, and unavailable readings do not generate recovery events.

It exposes the same [threshold event fields as Battery Low](#battery-low-trigger-data),
with `trigger.battery_low` set to false. Event fields and context are preserved.

### Recovery Automation Example

This dismisses notifications using the same ID as the Battery Low example:

``` yaml
alias: Battery No Longer Low in Kitchen
mode: queued
triggers:
  - trigger: battery_notes.battery_no_longer_low
    target:
      area_id: kitchen
actions:
  - action: persistent_notification.dismiss
    data:
      notification_id: "{{ trigger.device_id }}-{{ trigger.source_entity_id }}"
```

## Battery Replaced

`battery_notes.battery_was_replaced`

The **Battery was replaced** trigger is available under **Battery Notes** in the
automation editor. It fires when a battery is marked as replaced by the
[replacement button](./entities.md#battery-replaced) or the
[Set Battery Replaced action](./actions.md#set-battery-replaced), at the same
time as the [Battery Replaced event](./events.md#battery-replaced).

### Targets

The target is optional. Omit it to trigger on replacements for all battery
notes:

``` yaml
triggers:
  - trigger: battery_notes.battery_was_replaced
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
  - trigger: battery_notes.battery_was_replaced
    target:
      area_id: kitchen
actions:
  - action: persistent_notification.create
    data:
      title: "{{ trigger.device_name }} Battery Replaced"
      message: "You just used {{ trigger.battery_type_and_quantity }} batteries"
```
