# Home Assistant Battery Notes

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
[![Community Forum][forum-shield]][forum]

[![BuyMeACoffee](https://img.shields.io/badge/-buy_me_a%C2%A0coffee-gray?logo=buy-me-a-coffee&style=for-the-badge)](https://www.buymeacoffee.com/codechimp)


Integration to add battery notes to a device, with automatic discovery via a growing battery library for devices.  
Track both the battery type and also when the battery was replaced.  

*Please :star: this repo if you find it useful*

![Battery Notes](https://github.com/andrew-codechimp/HA-Battery-Notes/blob/main/images/screenshot-device.png "Battery Notes")

![Discovery](https://github.com/andrew-codechimp/HA-Battery-Notes/blob/main/images/screenshot-discovery.png "Device Discovery")

**This integration will set up the following platforms.**

Platform | Name | Description
-- | -- | --
`sensor` | Battery Type | Show battery type.
`sensor` | Battery last replaced | Date & Time the battery was last replaced.
`button` | Battery replaced | Update Battery last replaced to now.
`service` | Set battery replaced | Update Battery last replaced to now.

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrew-codechimp&repository=HA-Battery-Notes&category=Integration)

Or
Search for `Battery Notes` in HACS and install it under the "Integrations" category.

**Important**

Add the following entry to your `configuration.yaml`
```
battery_notes:
```
Restart Home Assistant
In the HA UI go to Settings -> Integrations click "+" and search for "Battery Notes"

### Manual Installation
<details>
<summary>More Details</summary>

* Using your tool of choice open the folder for your HA configuration (where you find `configuration.yaml`).
* If you do not have a `custom_components` folder there, you need to create it.
* In the `custom_components` folder create a new folder called `battery_notes`.
* Download _all_ the files from the `custom_components/battery_notes/` folder in this repository.
* Place the files you downloaded in the new folder you created.
* Add the following entry to your `configuration.yaml`  
```
battery_notes:
```
* Restart Home Assistant
* In the HA UI go to Settings -> Integrations click "+" and search for "Battery Notes"
</details>

## Configuration is done in the UI

On the "Configuration" -> "Integrations" -> "Battery Notes" screen add a new device, pick your device with a battery and add the battery type.
The battery type will then be displayed as a diagnostic sensor on the device.

## FAQ's

* Does a device have to be in the library?  
No, you can always add a device manually by going to Settings -> Integrations -> Battery Notes screen add a new device where you can enter the battery details manually.

* Why is my device not being discovered?  
It could be missing from the library or does not exactly match the name that your integration has.  ZHA and Z2M for example have different manufacturers/models for the same device, you can still add it manually or contribute to the library.

* When is the library updated?  
It updates when Home Assistant is restarted and approximately every 24 hours after that.  
It will pull the latest devices that have been merged into the main branch, if you have recently submitted a pull request for a new device it will not appear until it has been manually reviewed and merged.

* How do I remove a battery note on a device?  
Go into the Settings -> Integrations -> Battery Notes, use the menu on the right of a device and select Delete, this will only delete the battery note, not the whole device.

* Why does the device icon change?  
Unfortunately where there are multiple integrations associated with a device Home Assistant seems to choose an icon at random, I have no control over this.

* Can I edit a battery note?  
Go into Settings -> Integrations -> Battery Notes and click Configure on the device you want to edit.

* Why am I only able to see some of my devices when adding manually?  
By default Battery Notes filters the device list to only devices with a battery, if you want to add a battery note to a random device then you can disable this filtering by adding the following configuration to your `configuration.yaml` and restart Home Assistant to see all devices.
```
battery_notes:
  show_all_devices: true
```

* I only want to add notes to a few devices, can I disable auto discovery?  
If you want to disable this functionality you can add the following to your `configuration.yaml`, after a restart of Home Assistant you will not see discovered battery notes.
```
battery_notes:
  enable_autodiscovery: false
```

* How can I show my support?  
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/codechimp)



## Contributing to the Battery Library

<!-- To add a device definition to the battery library so that it will be automatically configured there are two options:

### Submit Definition via GitHub Issues Form

To add a new device via GitHub Issues, fill out [this form (BETA)](https://github.com/andrew-codechimp/HA-Battery-Notes/issues/new?template=new_device_request.yml&title=[Device]%3A+).
Upon submission of the issue, GitHub will attempt to make the required code changes automatically.

### Submit Definition via Pull Request

If you have issues with the form, or if you feel more comfortable editing JSON data, you can directly add definitions to [the library.json file](custom_components/battery_notes/data/library.json). -->
Fork the repository, add your device details to the JSON document `custom_components/battery_notes/data/library.json`, and then submit a pull request.

* The manufacturer and model should be exactly what is displayed on the Device screen within Home Assistant.
* The make & model names may be different between integrations such as Zigbee2MQTT and ZHA, if you see a similar device please duplicate the entry rather than changing it.
* Please keep devices in alphabetical order by manufacturer/model.
* The `battery_quantity` data is numeric (no quotes) and optional. If a device only requires a single battery, it should be omitted.
* The `battery_type` data should follow the most common naming for general batteries (ex. AAA, D) and the IEC naming for battery cells according to [Wikipedia](https://en.wikipedia.org/wiki/List_of_battery_sizes) (ex. CR2032, 18650)
* If a device has a bespoke rechargeable battery you can use `"battery_type": "Rechargeable"`
* For devices like smoke alarms where the battery is not replaceable you can use `"battery_type": "Irreplaceable"`
* If a device shouldn't be discovered because there are multiple revisions with the same model number but different battery types or it's optionally mains powered, it can be added to the library with a `"battery_type": "MANUAL"` to note it is a device that shouldn't have a battery definition added to the library to save removal/re-add because people don't realise there are variants.

For the example image below, your JSON entry will look like this:

```
{
    "manufacturer": "Philips",
    "model": "Hue motion sensor (9290012607)",
    "battery_type": "AAA",
    "battery_quantity": 2
},
```

![Device Details](https://github.com/andrew-codechimp/HA-Battery-Notes/blob/main/images/screenshot-device-info.png "Device Details")
<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md).

## Acknowledgements

A lot of the inspiration for this integration came from the excellent [PowerCalc by bramstroker](https://github.com/bramstroker/homeassistant-powercalc), without adapting code from PowerCalc I'd never have worked out how to add additional sensors to a device.

<!-- Huge thanks to @bmos for creating the issue form & automations for adding new devices. COMING SOON -->

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
