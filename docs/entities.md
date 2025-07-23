# Entities

You'll get the following entities for each device you have added to battery notes.

## Battery+
`sensor.{{device_name}}_battery_plus`

An enhanced battery sensor that duplicates the normal battery but with additional attributes specific to battery notes, Battery+ sensors are only added device type battery notes that have a battery percentage sensor, see below for adding a battery percentage if your device does not have one.  
Use the battery+ sensor on dashboards with secondary information fields/templates etc to display battery notes specific details along with the battery level.  
The original battery can optionally be hidden by adding a [configuration setting](./configuration.md).

See how to use this entity in the [community contributions](./community.md)

| Attribute | Type | Description |
|-----------|------|-------------|
| `battery_quantity` | `int` | The quantity of batteries |
| `battery_type` | `string` | The type of batteries |
| `battery_type_and_quantity` | `string` | The type of batteries with the quantity if more than 1 |
| `battery_last_replaced` | `string` | The date and time the battery was last replaced |
| `battery_low` | `bool` | An indicator of whether the battery is low based on the device or global threshold |
| `battery_low_threshold` | `int` | The device or global threshold for when the battery is low |
| `battery_last_reported` | `datetime` | The datetime when the battery level was last reported |
| `battery_last_reported_level` | `float` | The level when the battery was last reported |
| `device_id` | `string` | The device_id of the device |
| `device_name` | `string` | The name of the device |
| `source_entity_id` | `string` | The entity_id the battery note is associated with |

### Adding a battery percentage
If your device does not have a battery percentage but does have a battery voltage or other indicative sensor you can create a helper to add a calculated percentage. Battery Notes will create the Battery+ sensor from this. You can create the helper as follows   

- Within Settings > Devices & Services > Helpers press Create Helper
- Select a Template helper
- Select Template a sensor
- Give the template a name of MyDevice Battery (ensuring MyDevice exactly matches the name of the device will drop the device name from the Device sensors view and just show battery)
- The state template should reference the sensor and return a percentage  
Example of voltage sensor with a maximum capacity of 3 volts   
```{{ (states('sensor.my_sensor_voltage')|float(0) / 3 * 100) | round(0) }}```  
Example of low sensor, returning either 100% or 10%  
```{{ 10 if states('binary_sensor.my_sensor_low')  == true else 100 }}```  
- Unit of measurement should be %
- Device class should be battery
- State class should be measurement
- Device should be the device you want the template associated with (this is important otherwise Battery Notes will not find the helper)
- Save the helper 
- Within Settings > Devices & Services > Integrations > Battery Notes find the device you added the template to and click on the 3 dots and select Reload
- You will now have a Battery+ sensor for this device

!!! info

    You must create the template via a helper for it to be associated with the device.  YAML templates do not have the ability to be associated.


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
`binary_sensor.{{device_name}}_battery_plus_low`

A boolean sensor indicating if the battery is low, true when the battery is below the device or global threshold.  
If the device has a battery percentage then this will be automatically created.  
If the device does not have a battery percentage but does have a battery low boolean that is a battery class then this will be automatically created and listen for changes on the original battery low sensor, raising events when the battery is low or high.  
If you have specified a manual template then this will be created, reflecting the state of the template, raising events when the battery is low or high.

| Attribute | Type | Description |
|-----------|------|-------------|
| `battery_low_threshold` | `int` | The device or global threshold for when the battery is low |
| `battery_quantity` | `int` | The quantity of batteries |
| `battery_type` | `string` | The type of batteries |
| `battery_type_and_quantity` | `string` | The type of batteries with the quantity if more than 1 |
| `battery_last_replaced` | `string` | The date and time the battery was last replaced |
| `device_id` | `string` | The device_id of the device |
| `device_name` | `string` | The name of the device |
| `source_entity_id` | `string` | The entity_id the battery note is associated with |
