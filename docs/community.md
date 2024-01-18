# Community Contributions

## Automation Tips

To call the battery replaced service from an entity trigger you will need the device_id, here's an easy way to get this

```
action:
  - service: battery_notes.set_battery_replaced
    data:
      device_id: "{{ device_id(trigger.entity_id) }}"
```

## Contributing

If you want to contribute then [fork the repository](https://github.com/andrew-codechimp/HA-Battery-Notes), edit this page which is in the docs folder and submit a pull request.
