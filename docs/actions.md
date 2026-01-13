# Actions

## battery_notes.set_battery_replaced

For updating the [battery replaced date](./entities.md#battery-replaced). This allows you to change the date a battery was replaced.

See how to use this action in the [community contributions](./community.md)

| Data attribute           | Optional | Description                                                                                                           |
| ------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `device_id`      | `yes`    | The device id that you want to change the battery replaced date for. |
| `source_entity_id`      | `yes`    | The entity id that you want to change the battery replaced date for (only used for entity associated battery notes). |
| `datetime_replaced` | `yes`    | The optional datetime that you want to set the battery replaced to, if omitted the current date/time will be used. |

You must specify either a device_id or entity_id, entity_id will be used in preference if both are specified.  This allows the action to work with battery notes associated with both a device and also an individual entity, whether it is part of a device or not.

## battery_notes.check_battery_last_replaced

For raising events for devices that haven't replaced their battery.  

The action will raise a seperate [battery_not_replaced](./events.md/#battery-not-replaced) event for each device where its last replaced date is older than the number of days specified.  

If you do not want an event raised for certain devices such as rechargeable then disable the battery_last_replaced sensor entity for that device.  

You can use this action to schedule checks on batteries that is convenient to you, e.g. once a week etc.  

See how to use this action in the [community contributions](./community.md)

| Data attribute           | Optional | Description                                                                                                           |
| ------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `days_last_replaced`     | `no`    |  The number of days since a device last had its battery replaced. |

## battery_notes.check_battery_last_reported

For raising events for devices that haven't reported their battery level.  

The action will raise a seperate [battery_not_reported](./events.md/#battery-not-reported) event for each device where its last reported date is older than the number of days specified.  

You can use this action to schedule checks on batteries that is convenient to you, e.g. when you wake up, once a week etc.  

See how to use this action in the [community contributions](./community.md)

| Data attribute           | Optional | Description                                                                                                           |
| ------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `days_last_reported`      | `no`    |  The number of days since a device last reported its battery level. |

## battery_notes.check_battery_low

For raising events for devices that have a battery low status.  

The action will raise a seperate [battery_threshold](./events.md/#battery-threshold) event for each device that have a battery low status.  

You can use this action as a reminder that is convenient to you, e.g. when you wake up, once a week etc.  The event has a boolean data item `reminder` to determine if the event was raised by this action or the device battery going to a low state.

See how to use this action in the [community contributions](./community.md)
