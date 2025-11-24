# Configuration

Global configuration settings can be changed by selecting the configuration cog on the main Battery Notes service.

| Name             | Description                                                                              |
| ---------------- | ---------------------------------------------------------------------------------------- |
| Show all devices | Will show all devices in the manual add dropdown, rather than just those with batteries. |
| Hide battery | Hide the standard battery when adding Battery+. This will not effect existing dashboards, automations etc.|
| Round battery | Round battery+ to whole percentages.|
| Default battery low threshold | The default threshold where a devices battery_low entity is set to true and the battery_notes_battery_threshold event is fired, can be overriden per device in device configuration. |
|Battery increase threshold | The threshold where the battery_notes_battery_increased event is fired, use this event for battery replaced automations. The threshold is the difference in increase between previous and current battery level. |
| Auto discovery | Will automatically match devices against the library and create a setup flow within the integrations page, this occurs at instegration startup and repeats every 24 hours. |
| Enable battery replaced | New battery notes will have a battery replaced sensor and butoon. If disabled new devices added to battery notes will have the battery replaced sensor and button disabled. Any battery notes you have previously added you will have to disable/re-enable these sensors manually, which also means you can enable specific sensors of important ones you want to track. |
| User library | If specified then a user library file will be searched prior to the main library, the user library must be in the same format as the library and placed in the same folder (config/.storage/battery_notes). Only really used for dev purposes. |

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
