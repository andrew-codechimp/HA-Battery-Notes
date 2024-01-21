# Entities

You'll get the following entities for each device you have added to battery notes.

## Battery+
`sensor.{{device_name}}_battery_plus`

An enhanced battery sensor that mirrors the normal battery but with additional attributes specific to battery notes.
The original battery can optionally be hidden by adding a [configuration setting](./configuration.md).

| Attribute | Type | Description |
|-----------|------|-------------|
| `battery_quantity` | `int` | The quantity of batteries |
| `battery_type` | `string` | The type of batteries |
| `battery_type_and_quantity` | `string` | The type of batteries with the quantity if more than 1 |
| `battery_last_replaced` | `string` | The date and time the battery was last replaced |
| `battery_low` | `bool` | An indicator of whether the battery is low based on the device or global threshold |
| `battery_low_threshold` | `int` | The device or global threshold for when the battery is low. |

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

## Battery Low
`sensor.{{device_name}}_battery_low`

A boolean sensor indicating if the battery is low, true when the battery is below the device or global threshold.

| Attribute | Type | Description |
|-----------|------|-------------|
| `battery_low_threshold` | `int` | The device or global threshold for when the battery is low. |