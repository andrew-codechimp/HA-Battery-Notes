# Entities

You'll get the following entities for each device you have added to battery notes.

## Battery Type
`sensor.{{device_name}}_battery_type`

The battery quantity and type display in an easy to use single entity.  The quantity is only shown if more than 1.

| Attribute | Type | Description |
|-----------|------|-------------|
| `battery_quantity` | `int` | The quantity of batteries |
| `battery_type` | `string` | The type of batteries |

## Battery Last Replaced
`sensor.{{device_name}}_battery_last_replaced`

The last time the battery of the device was replaced.

## Battery Replaced
`button.{{device_name}}_battery_replaced`

A button to set the battery_last_replaced entity to now.

