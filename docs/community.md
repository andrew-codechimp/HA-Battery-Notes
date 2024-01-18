# Community Contributions

These are a few contributions by the community.

## Automation Examples

### Set the battery replaced automatically  
Submitted by @danielbrunt57

```
alias: Battery Replaced
description: "Set the battery replaced automatically"
trigger:
  - platform: state
    entity_id:
      - sensor.yourdevice1_battery
      - sensor.yourdevice2_battery
    for:
      hours: 0
      minutes: 0
      seconds: 10
condition:
  - condition: template
    value_template: >-
      {{ trigger.from_state is not none and trigger.from_state.state not in
      ['unavailable','unknown'] and trigger.from_state.state|float(0) < 100 and
      trigger.to_state.state|float(0) > 98 }}
action:
  - service: battery_notes.set_battery_replaced
    data:
      device_id: "{{ device_id(trigger.entity_id) }}"
    enabled: true
  - service: notify.persistent_notification
    metadata: {}
    data:
      message: "Battery replaced: {{ state_attr(trigger.entity_id, 'friendly_name') }}"
mode: single
```

## Contributing  
If you want to contribute then [fork the repository](https://github.com/andrew-codechimp/HA-Battery-Notes), edit this page which is in the docs folder and submit a pull request.
