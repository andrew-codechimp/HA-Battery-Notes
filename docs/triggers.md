# Triggers

## Battery Low

`battery_notes.battery_became_low`

The **Battery became low** trigger is available under **Battery Notes** in the
automation editor. It listens to the [Battery Threshold event](./events.md#battery-threshold)
and fires when `battery_low` is true, according to the selected event types below.
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

### Event Types

Use the **Event types** option in the automation editor, or `options.event_types`
in YAML, to choose which low battery events trigger the automation:

This field is required and defaults to **All**. If omitted in YAML, validation
fills it with `all`.

| Option                | YAML value              | Behavior                                                                              |
| --------------------- | ----------------------- | ------------------------------------------------------------------------------------- |
| All                   | `all`                   | Trigger on both low battery transitions and reminders.                                 |
| Low-state transitions | `low_state_transitions` | Trigger when a battery becomes low. Ignore reminders.                                  |
| Reminders             | `reminders`             | Trigger only on reminders raised by [Check Battery Low](./actions.md#check-battery-low). |

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

| Member                               | Type                 | Description                                                    |
| ------------------------------------ | -------------------- | -------------------------------------------------------------- |
| `trigger.battery_low`                | `bool`               | Always true for this trigger.                                  |
| `trigger.battery_low_threshold`      | `int`                | The effective battery low threshold.                           |
| `trigger.battery_increase_threshold` | `int`                | The effective battery increase threshold.                      |
| `trigger.battery_level`              | `float` or `null`    | The current battery percentage.                                |
| `trigger.previous_battery_level`     | `float` or `null`    | The previous battery percentage.                               |
| `trigger.battery_last_replaced`      | `datetime` or `null` | The recorded replacement date.                                 |
| `trigger.reminder`                   | `bool`               | True for an action reminder, false for a low-state transition. |

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
      event_types: all
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

## Battery Was Not Reported

`battery_notes.battery_was_not_reported`

The **Battery was not reported** trigger listens to the
[Battery Not Reported event](./events.md#battery-not-reported) raised by the
[Check Battery Last Reported action](./actions.md#check-battery-last-reported).
The action raises an event for each eligible battery note whose last report is
older than `days_last_reported`, or which has never reported.

Call or schedule `battery_notes.check_battery_last_reported` with `raise_events`
enabled (the default) to fire this trigger. Time passing alone does not fire it;
the trigger does not run the check or set the day limit.

Automations using this trigger must use `mode: queued`. One check action call
can raise events for multiple battery notes in quick succession, and queued
mode lets the automation process each event in order.

``` yaml
mode: queued
triggers:
  - trigger: battery_notes.battery_was_not_reported
    target:
      area_id: kitchen
```

It supports the same [targets as Battery Replaced](#targets), with an omitted
target matching all battery notes and `target: {}` matching none. It has no
additional options. Targets are resolved for each event.

All [Battery Not Reported event fields](./events.md#battery-not-reported) are
available directly on `trigger`, including `trigger.device_name`,
`trigger.battery_last_reported`, `trigger.battery_last_reported_days`, and
`trigger.battery_last_reported_level`. The last reported date, day count, and
level can be null when the battery has never reported.

## Battery Was Not Replaced

`battery_notes.battery_was_not_replaced`

The **Battery was not replaced** trigger listens to the
[Battery Not Replaced event](./events.md#battery-not-replaced) raised by the
[Check Battery Last Replaced action](./actions.md#check-battery-last-replaced).
The action raises an event for each eligible battery note whose replacement
date is older than `days_last_replaced`. Notes without a replacement date or
with a disabled last-replaced sensor are skipped.

Call or schedule `battery_notes.check_battery_last_replaced` with `raise_events`
enabled (the default) to fire this trigger. Time passing alone does not fire it;
the trigger does not run the check or set the day limit.

Automations using this trigger must use `mode: queued`. One check action call
can raise events for multiple battery notes in quick succession, and queued
mode lets the automation process each event in order.

``` yaml
mode: queued
triggers:
  - trigger: battery_notes.battery_was_not_replaced
    target:
      area_id: kitchen
```

It supports the same [targets as Battery Replaced](#targets), with an omitted
target matching all battery notes and `target: {}` matching none. It has no
additional options. Targets are resolved for each event.

All [Battery Not Replaced event fields](./events.md#battery-not-replaced) are
available directly on `trigger`, including `trigger.device_name`,
`trigger.battery_last_replaced`, `trigger.battery_last_replaced_days`, and
`trigger.battery_type_and_quantity`.

### Scheduling the Check Actions

This example runs both checks each morning. Their events fire matching
automations using the triggers above. The checks can raise an event for each
qualifying battery note on every run. Automations using these triggers must
use `mode: queued` to handle multiple events.

``` yaml
alias: Check Battery Reports and Replacements
triggers:
  - trigger: time
    at: "09:00:00"
actions:
  - action: battery_notes.check_battery_last_reported
    data:
      days_last_reported: 7
      raise_events: true
  - action: battery_notes.check_battery_last_replaced
    data:
      days_last_replaced: 365
      raise_events: true
```

## Battery Has Increased

`battery_notes.battery_has_increased`

The **Battery has increased** trigger listens to the
[Battery Increased event](./events.md#battery-increased). For percentage sources,
it fires when the new level is at least the previous level plus the battery
note's effective increase threshold. The global default is 25 percentage points;
a per-note threshold of 0 uses the global setting. The trigger does not set a
separate threshold.

Binary battery sources and low battery templates also raise an increased event
when their low state becomes healthy, with nominal levels of 100 and 0 for the
current and previous levels.

It supports the same [targets as Battery Replaced](#targets). Omit the target
to include all battery notes; `target: {}` matches none. Target membership is
resolved for each event. There are no additional options.

All [Battery Increased event fields](./events.md#battery-increased) are available
directly on `trigger`, including `trigger.battery_level`,
`trigger.previous_battery_level`, `trigger.battery_increase_threshold`, and
`trigger.battery_last_replaced`. The increased event does not include a
`reminder` field.

The trigger does not automatically update the replacement date. To record an
increase as a battery replacement, connect it to Set Battery Replaced:

``` yaml
alias: Record Battery Replacement After Increase
mode: queued
triggers:
  - trigger: battery_notes.battery_has_increased
actions:
  - action: battery_notes.set_battery_replaced
    data:
      device_id: "{{ trigger.device_id }}"
      source_entity_id: "{{ trigger.source_entity_id }}"
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
