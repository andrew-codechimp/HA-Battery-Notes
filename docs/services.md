# Services

## battery_notes.set_battery_replaced

For updating the [battery replaced date](./entities.md#battery-replaced). This allows you to change the date a battery was replaced.

See how to use this service in the [community contributions](./community.md)

| Parameter                | Optional | Description                                                                                                           |
| ------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `data.device_id`      | `no`    | The device id that you want to change the battery replaced date for. |
| `data.datetime_replaced` | `yes`    | The optional datetime that you want to set the battery replaced to, if omitted the current date/time will be used. |

## battery_notes.check_battery_last_reported

For raising events for devices that haven't reported their battery level.  

The service will raise a seperate [battery_not_reported](./events.md/#battery_not_reported) event for each device where its last reported date is older than the number of days specified.  

You can use this service call to schedule checks on batteries that is convenient to you, e.g. when you wake up, once a week etc.  

See how to use this service in the [community contributions](./community.md)

| Parameter                | Optional | Description                                                                                                           |
| ------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `data.days`      | `no`    |  The number of days since a device last reported its battery level. |

## battery_notes.check_battery_low

For raising events for devices that have a battery low status.  

The service will raise a seperate [battery_threshold](./events.md/#battery_threshold) event for each device that have a battery low status.  

You can use this service call as a reminder that is convenient to you, e.g. when you wake up, once a week etc.  The event has a boolean data item `reminder` to determine if the event was raised by this service or the device battery going to a low state.

See how to use this service in the [community contributions](./community.md)

