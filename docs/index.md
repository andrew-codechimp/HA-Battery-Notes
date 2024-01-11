# Home Assistant Battery Notes

Integration to add battery notes to a device, with automatic discovery via a growing [battery library](https://github.com/andrew-codechimp/HA-Battery-Notes/blob/main/library.md) for devices.  
Track both the battery type and also when the battery was replaced.  

## Features

The integration will add additional diagnostic entities to your device.

![device example](./assets/screenshot-device.png)

* [Entities](./entities.md)
* [Services](./services.md)

## How to use Battery Notes
Once you have [installed the integration](https://github.com/andrew-codechimp/HA-Battery-Notes#installation), you will hopefully have some devices discovered and you can follow the Notification to confirm their details and add them, if you don't have devices discovered you can add them manually.

![device discovery](./assets/screenshot-discovery.png)

## To add a battery note manually
* Go to Settings/Integrations and click Add Integration.
* Select Battery Notes.
* Choose your device from the drop down and click next.
* Enter the battery type and quantity and click submit.

!!! info

    The library is updated automatically with new devices approximately every 24 hours from starting Home Assistant, if you have added a device to the library using [this form](https://github.com/andrew-codechimp/HA-Battery-Notes/issues/new?template=new_device_request.yml&title=[Device]%3A+) then this will take about a day to be discovered once it's approved and added.

## Community Contributions

A collection of community contributions can be found on the [community contributions](./community.md) page.

## FAQ

Before raising anything, please read through the [faq](./faq.md). If you have questions, then you can raise a [discussion](https://github.com/andrew-codechimp/HA-Battery-Notes/discussions). If you have found a bug or have a feature request please [raise it](https://github.com/andrew-codechimp/HA-Battery-Notes/issues) using the appropriate report template.

