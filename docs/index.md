# Battery Notes for Home Assistant

Integration to add battery notes to a device or entity, with automatic discovery via a growing [battery library](library.md) for devices.  
Track the battery type, when the battery was replaced, when a battery is low based on device or global thresholds and also when a battery hasn't been reported for a while.  
Battery low, replaced and not reported are all via events and services, you have the option of creating your own automations for these or using the predefined ones in [community](./community.md).  

*Please :star: this repo on [GitHub](https://github.com/andrew-codechimp/HA-Battery-Notes) if you find it useful*  
*If you want to show your support please*

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/codechimp)


## Features

The integration will add additional diagnostic entities to your device.

![device example](./assets/screenshot-device.png)

* [Entities](./entities.md)
* [Services](./services.md)
* [Events](./events.md)

## How to use Battery Notes
Once you have [installed the integration](https://github.com/andrew-codechimp/HA-Battery-Notes#installation) you will hopefully have some devices discovered and you can follow the Notification to confirm their details and add them, if you don't have devices discovered you can add them manually.

![device discovery](./assets/screenshot-discovery.png)

## To add a battery note manually
* Go to Settings/Integrations and click Add Integration.
* Select Battery Notes.
* Choose Device or Entity and click next. Device will automatically detect a battery and will work for most common devices, you should use entity if your device has multiple batteries or when an entity does not have a device.
* Choose your device or entity from the drop down and click next.
* Enter the battery type and quantity and optionally a battery low threshold and click submit.

!!! info

    The library is updated automatically with new devices approximately every 24 hours from starting Home Assistant, if you have added a device to the library using [this form](https://github.com/andrew-codechimp/HA-Battery-Notes/issues/new?template=new_device_request.yml&title=[Device]%3A+) then this will take about a day to be discovered once it's approved and added.

## Battery Low Template
This is for advanced use where a device does not have a typical battery percentage (or it is innacurate) but still provides an indication of the level, such as a string, boolean or voltage.  
You can specify a template that must return true when the battery is deemed low.  

Example templates  
```
{{ states('sensor.mysensor_battery_low') }}
{{ states('sensor.mysensor_battery_level') == "Low" }}
{{ states('sensor.mysensor_battery_voltage') | float(5) < 1 }}
```

!!! info

    If a template is specified then the battery percentage will be ignored when evaluating threshold and increased events. 


## Community Contributions

A collection of community contributions can be found on the [community contributions](./community.md) page. 


## FAQ

Before raising anything, please read through the [faq](./faq.md). If you have questions, then you can raise a [discussion](https://github.com/andrew-codechimp/HA-Battery-Notes/discussions). If you have found a bug or have a feature request please [raise it](https://github.com/andrew-codechimp/HA-Battery-Notes/issues) using the appropriate report template.

