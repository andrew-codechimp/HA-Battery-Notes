# FAQ

## Does a device have to be in the library?

No, you can always add a device manually by going to Settings -> Integrations -> Battery Notes screen add a new device where you can enter the battery details manually.

## Why is my device not being discovered?

It could be missing from the [library](https://github.com/andrew-codechimp/HA-Battery-Notes/blob/main/library.md) or does not exactly match the name that your integration has. ZHA and Z2M for example have different manufacturers/models for the same device, you can still add it manually or contribute to the library.

## When is the library updated?

It updates when Home Assistant is restarted and approximately every 24 hours after that.  
It will pull the latest devices that have been merged into the main branch, if you have recently submitted a pull request for a new device it will not appear until it has been manually reviewed and merged.

## How do I remove a battery note on a device?

Go into the Settings -> Integrations -> Battery Notes, use the menu on the right of a device and select Delete, this will only delete the battery note, not the whole device.

## Can I edit a battery note?

Go into Settings -> Integrations -> Battery Notes and click Configure on the device you want to edit.

## Why am I only able to see some of my devices when adding manually?

By default Battery Notes filters the device list to only devices with a battery, if you want to add a battery note to a random device then you can disable this filtering by turning on the Show all devices configuration setting.

## I only want to add notes to a few devices, can I disable auto discovery?

If you want to disable this functionality you can turn off auto discovery in the configuration settings

## I don't want to track battery replacement, can I disable this?

Yes, you can turn off enable replaced within configuration settings. _new_ devices added to battery notes will have the battery replaced sensor and button disabled. Any devices you have previously added to Battery Notes you will have to disable/enable these sensors manually, which also means you can just enable specific sensors of important ones you want to track.

## My device doesn't show a Battery+ sensor

This is usually because the device does not have a battery percentage, you can create one if your device has a voltage, low indicator or similar by following [these instructions](entities.md/#adding-a-battery-percentage)

## My device is not picking up the proper battery percentage for Battery+

If your device has a different percentage, perhaps a max charge indicator Battery Notes cannot identify the correct battery percentage to monitor. You can either hide the entity you want Battery+ to ignore or you can remove the Battery Notes device, then re-add as an Entity Association Type manually and choose the correct battery percentage to monitor.

## How do I create a battery low template

The best way to do this is to test in the developer tools/template section for your sensor.  
Be aware that Home Assistant shows friendly alternatives for some sensors, so when you are seeing Normal/Low this may really be a bool, testing in the template tool will allow you to determine the correct template to use. Start by adapting one of these.

```
{{ states('sensor.mysensor_battery_low') }}
{{ states('sensor.mysensor_battery_level') == "Low" }}
{{ states('sensor.mysensor_battery_voltage') | float(5) < 1 }}
```

Once you have got your template correct you can copy/paste it into the battery notes configuration section for that device and it will use that for detecting the battery is low and raising the battery notes event.

## My Shelly device is not showing a Battery+

There seems to have been an issue with the Shelly integration at some point where the battery entity was not created properly and therefore Battery Notes cannot find it. To fix this do the following:

- Remove the battery note from the Shelly device
- Remove the Shelly device from the Shelly integration
- Re-Add the Shelly device
- Add the battery note to the device

## Battery Notes is not showing in the integrations list within a device page (new with version 3)

The way Battery Notes associate with a device has had to change due to a change within Home Assistant.  
You will still see your battery note entities within the device page and they work exactly the same, but you will not see Battery Notes listed in the integrations at the top.  
You can edit a battery note for a device by going into the Battery Notes integration, choosing the device and configuring it there.  
A Battery Note no longer has entities itself, but you can still see all the entities, grouped by device, by clicking on the xx entities just under the Battery Notes service within the integration page.  

## How do I install pre-release versions via HACS

Within Home Assistant go to Settings -> Integrations -> HACS  
Select Services  
Select Battery Notes  
In the Diagnostics panel select the +1 entity not shown  
Select Pre-release  
Select the cog icon  
Select Enable  
Select Update and wait for the entity to be enabled  
Turn on the Pre-release toggle  
HACS will now show updates available for pre-releases if there are any

## How do I uninstall Battery Notes

Within Home Assistant go to Settings -> Integrations -> Battery Notes  
Click on the three dots for the top Battery Notes service and select Delete  
Go to HACS from your sidebar  
Click on the three dots next to Battery Notes and select Remove  
Restart Home Assistant

## How can I show my support?

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/codechimp)
