# Services

## battery_notes.set_battery_replaced

For updating the [battery replaced date](./entities.md#battery-replaced). This allows you to change the date a battery was replaced.

See how to use this service in the [community contributions](./community.md)

| Parameter                | Optional | Description                                                                                                           |
| ------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `data.device_id`      | `no`    | The device id that you want to change the battery replaced date for. |
| `data.datetime_replaced` | `yes`    | The optional datetime that you want to set the battery replaced to, if omitted the current date/time will be used. |
