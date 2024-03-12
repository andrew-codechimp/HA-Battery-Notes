# Library

The library contains user contributed device definitions to allow discovery of the most popular devices.  
The library is updated when Home Assistant is restarted and approximately every 24 hours after that.  
It will pull the latest devices that have been merged into the main branch, if you have recently submitted a pull request for a new device it will not appear until it has been manually reviewed and merged.

# Contributing to the library

## Submit Definition via GitHub Issues Form

[!["New Device Request"](./assets/new-device-request.png)](https://github.com/andrew-codechimp/HA-Battery-Notes/issues/new?template=new_device_request.yml&title=[Device]%3A+)

Upon submission using the form above GitHub will attempt to make the required code changes automatically.

## Submit Definition via Pull Request

Fork the repository, add your device details to the JSON document `custom_components/battery_notes/data/library.json`, and then submit a pull request. Do not enable GitHub Actions (disabled by default) as this will mess with the pull request and are unnecessary for a library submission.

* The manufacturer and model should be exactly what is displayed on the Device screen within Home Assistant.
* The make & model names may be different between integrations such as Zigbee2MQTT and ZHA, if you see a similar device please duplicate the entry rather than changing it.
* Please keep devices in alphabetical order by manufacturer/model.
* The `battery_quantity` data is numeric (no quotes) and optional. If a device only requires a single battery, it should be omitted.
* The `battery_type` data should follow the most common naming for general batteries (ex. AAA, D) and the IEC naming for battery cells according to [Wikipedia](https://en.wikipedia.org/wiki/List_of_battery_sizes) (ex. CR2032, 18650)
* If a device has a bespoke rechargeable battery you can use `"battery_type": "Rechargeable"`
* For devices like smoke alarms where the battery is not replaceable you can use `"battery_type": "Irreplaceable"`
* If a device shouldn't be discovered because there are multiple revisions with the same model number but different battery types it can be added to the library with a `"battery_type": "MANUAL"` to note it is a device that shouldn't have a battery definition added to the library to save removal/re-add because people don't realise there are variants.

For the example image below, your JSON entry will look like this:

```
{
    "manufacturer": "Philips",
    "model": "Hue motion sensor (9290012607)",
    "hw_version": "Some specific hardware detail", < Optional, only use if two devices have the same model and the hw_version are different.
    "battery_type": "AAA",
    "battery_quantity": 2  < Only use if more than 1 battery
},
```

![device details](./assets/screenshot-device-info.png)
