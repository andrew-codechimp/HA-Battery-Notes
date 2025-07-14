# Battery Notes for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![Downloads][download-latest-shield]]()
[![HACS Installs][hacs-installs-shield]]()
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

Integration to add battery notes to a device or entity, with automatic discovery via a growing [battery library](library.md) for devices.  
Track the battery type, when the battery was replaced, when a battery is low based on device or global thresholds and also when a battery hasn't been reported for a while.

**Dashboard cards usage**

A battery+ sensor provides useful attributes for easy use in dashboards, the standard battery can optionally be hidden.

**Notifications and automations**

Battery low, replaced and not reported are all exposed via events and actions, using these you can create your own automations to generate notifications or other actions, there are some predefined ones in [community](https://andrew-codechimp.github.io/HA-Battery-Notes/community).

_Please :star: this repo if you find it useful_  
_If you want to show your support please_

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/codechimp)

![Battery Notes](https://raw.githubusercontent.com/andrew-codechimp/ha-battery-notes/main/docs/assets/screenshot-device.png "Battery Notes")

![Discovery](https://raw.githubusercontent.com/andrew-codechimp/ha-battery-notes/main/docs/assets/screenshot-discovery.png "Device Discovery")

## Installation

**Important**

Once you have installed battery notes using either HACS or manually as per the instructions below you must add the following entry to your `configuration.yaml`, then restart Home Assistant. This will enable discovery of your devices.

```
battery_notes:
```

If you need to add a device that is not automatically discovered from the library go to Settings -> Integrations click "+" and search for "Battery Notes"

### HACS Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrew-codechimp&repository=HA-Battery-Notes&category=Integration)

Or
Search for `Battery Notes` in HACS and install it under the "Integrations" category.

### Manual Installation

<details>
<summary>More Details</summary>

- You should take the battery_notes.zip file from the latest [published release](https://github.com/andrew-codechimp/ha-battery-notes/releases).
- To install, place the contents of `custom_components` into the `<config directory>/custom_components` folder of your Home Assistant installation.
- Add the following entry to your `configuration.yaml`

```
battery_notes:
```

- Restart Home Assistant
- In the HA UI go to Settings -> Integrations click "+" and search for "Battery Notes"
</details>

## Docs

To get full use of the integration, read the documentation. It contains community quick starts as well as details on all the actions, events and entities.

[!["Documentation"](https://raw.githubusercontent.com/andrew-codechimp/ha-battery-notes/main/docs/assets/documentation.png)](https://andrew-codechimp.github.io/HA-Battery-Notes/)

## Contributing to the Battery Library

[!["New Device Request"](https://raw.githubusercontent.com/andrew-codechimp/ha-battery-notes/main/docs/assets/new-device-request.png)](https://github.com/andrew-codechimp/HA-Battery-Notes/issues/new?template=new_device_request.yml&title=[Device]%3A+)

To add a device definition to the battery library so that it will be automatically configured fill out the above form or see the [docs](https://andrew-codechimp.github.io/HA-Battery-Notes/library) for adding via pull request.

## Translations

To add a new language translation to Battery Notes see [here](https://andrew-codechimp.github.io/HA-Battery-Notes/translations)

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md).

## Acknowledgements

A lot of the inspiration for this integration came from the excellent [PowerCalc by bramstroker](https://github.com/bramstroker/homeassistant-powercalc), without adapting code from PowerCalc I'd never have worked out how to add additional sensors to a device.

Huge thanks to @bmos for creating the issue form & automations for adding new devices.

Thanks to everyone who has submitted devices to the library.

<!---->

[battery_notes]: https://github.com/andrew-codechimp/HA-Battery-Notes
[commits-shield]: https://img.shields.io/github/commit-activity/y/andrew-codechimp/HA-Battery-Notes.svg?style=for-the-badge
[commits]: https://github.com/andrew-codechimp/HA-Battery-Notes/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/t/custom-component-battery-notes/613821
[license-shield]: https://img.shields.io/github/license/andrew-codechimp/HA-Battery-Notes.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/andrew-codechimp/HA-Battery-Notes.svg?style=for-the-badge
[releases]: https://github.com/andrew-codechimp/HA-Battery-Notes/releases
[download-latest-shield]: https://img.shields.io/github/downloads/andrew-codechimp/ha-battery-notes/latest/total?style=for-the-badge
[hacs-installs-shield]: https://img.shields.io/endpoint.svg?url=https%3A%2F%2Flauwbier.nl%2Fhacs%2Fbattery_notes&style=for-the-badge
