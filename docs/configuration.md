# Configuration

You can add these options to change the default behaviour of Battery Notes by adding them to your Home Assistant configuration.yaml under the battery_notes: property, like so:

```
battery_notes:
  enable_autodiscovery: true
  show_all_devices: false
  enable_replaced: true
```

A restart of Home Assistant is required for the changed to take effect.

Name | Type | Requirement | Default | Description |
-- | -- | -- | -- | -- |
enable_autodiscovery | Boolean | Optional | True | If set to true will automatically match devices against the library and create a setup flow within the integrations page. |
show_all_devices | Boolean | Optional | False | If set to true will show all devices in the manual add dropdown, rather than just those with batteries. |
enable_replaced | Boolean | Optional | True | If set to false new devices added to battery notes will have the battery replaced sensor and button disabled.  Any devices you have previously added to Battery Notes you will have to disable these sensors manually, which also means you can enable specific sensors of important ones you want to track. |
hide_battery | Boolean | Optional | False | Hide the standard battery when adding Battery+. |
user_library | String | Optional |  | If specified then a user library file will be searched prior to the main library, the user library must be in the same format as the library and placed in the same folder. Only really used for dev purposes. |

# Debug Logging

To analyse issues on your installation it might be helpful to enable debug logging.

You can enable debug logging by going to the Battery Notes integration page. You can use the button below.

[![Open your Home Assistant instance and show Battery Notes.](https://my.home-assistant.io/badges/integrations.svg)](https://my.home-assistant.io/redirect/integration/?domain=battery_notes)

Next click `Enable debug logging`

**Alternatively**

Add the following to configuration.yaml:

```
    logger:
      default: warning
      logs:
        custom_components.battery_notes: debug
```
