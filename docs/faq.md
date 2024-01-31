# FAQ

* Does a device have to be in the library?  
No, you can always add a device manually by going to Settings -> Integrations -> Battery Notes screen add a new device where you can enter the battery details manually.

* Why is my device not being discovered?  
It could be missing from the [library](https://github.com/andrew-codechimp/HA-Battery-Notes/blob/main/library.md) or does not exactly match the name that your integration has.  ZHA and Z2M for example have different manufacturers/models for the same device, you can still add it manually or contribute to the library.

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
  show_all_devices: True
```

* I only want to add notes to a few devices, can I disable auto discovery?  
If you want to disable this functionality you can add the following to your `configuration.yaml`, after a restart of Home Assistant you will not see discovered battery notes.
```
battery_notes:
  enable_autodiscovery: False
```

* I don't want to track battery replacement, can I disable this?  
Yes, you can add the following to your `configuration.yaml`, after a restart of Home Assistant *new* devices added to battery notes will have the battery replaced sensor and button disabled.  Any devices you have previously added to Battery Notes you will have to disable/enable these sensors manually, which also means you can just enable specific sensors of important ones you want to track.
```
battery_notes:
  enable_replaced: False
```

* How can I show my support?  
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/codechimp)
