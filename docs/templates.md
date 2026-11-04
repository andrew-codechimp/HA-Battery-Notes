# Templates

## Battery Percentage Template

Use a percentage template when a device does not provide an accurate battery
percentage but does report a voltage, binary low-battery state, or another
indication of its battery level. Battery Notes creates a Battery+ sensor from the
template, which must return a percentage from 0 to 100.

See [reusable percentage examples](#battery-percentage-examples) for versions that
find their source automatically, allowing you to write a template once and copy/paste it
without changing entity IDs.

**Linear voltage: 0 volts = 0%, 3 volts = 100%**

``` jinja
{% set v = states('sensor.my_sensor_voltage') %}
{{ (v | float / 3 * 100) | round(0)
   if is_number(v) else 'unknown' }}
```

**Calibrated voltage: 2 volts = 10%, 3 volts = 100%**

``` jinja
{% set v = states('sensor.my_sensor_voltage') %}
{{ (((v | float - 2) / (3 - 2)) * 90 + 10) | round(0)
   if is_number(v) else 'unknown' }}
```

**Binary low-battery state: low = 9%, normal = 100%**

``` jinja
{% set low = states('binary_sensor.my_sensor_low') %}
{{ 9 if low == 'on' else 100 if low == 'off' else 'unknown' }}
```

## Battery Low Template

Percentage templates already drive low-battery detection using the configured
threshold. Use a low template when you need a separate rule. It must return true
when the battery is low and false when it is healthy. Return `unknown` when the
source reading cannot be used.

See [reusable low-battery examples](#battery-low-examples) for versions that
find their source automatically, allowing you to write a template once and copy/paste it
without changing entity IDs.

Pass through a binary low-battery sensor's state. Its `on` and `off` values are
accepted as true and false, while `unknown` and `unavailable` are preserved.

``` jinja
{{ states('binary_sensor.mysensor_battery_low') }}
```

**Detect a text state of `Low`**

``` jinja
{% set level = states('sensor.mysensor_battery_level') %}
{{ level == 'Low'
   if level not in ['unknown', 'unavailable'] else 'unknown' }}
```

**Detect a voltage below 1 volt**

``` jinja
{% set v = states('sensor.mysensor_battery_voltage') %}
{{ (v | float) < 1 if is_number(v) else 'unknown' }}
```

!!! info

    If a template is specified then the battery percentage will be ignored when evaluating threshold and increased events.

## Reusable source selection

Battery Notes can find a source entity on the note's device, allowing the same
template to be copy/pasted for several devices without editing entity IDs. Use
`battery_notes_source()` to select the source. It returns an entity ID to pass to
`states()`, `is_state()`, `state_attr()`, or another template function:

``` text
battery_notes_source('domain', 'device_class')
battery_notes_source('domain', 'device_class', 'unit_of_measurement')
```

**Example source calls**

| Source call                                        | Matches                          |
| -------------------------------------------------- | -------------------------------- |
| `battery_notes_source('sensor', 'battery', '%')`   | A battery percentage sensor      |
| `battery_notes_source('sensor', 'voltage', 'V')`   | A voltage sensor reporting volts |
| `battery_notes_source('binary_sensor', 'battery')` | A binary low-battery sensor      |

The supported domains are `sensor` and `binary_sensor`. The unit of measurement is
optional; omitting it matches any unit. Specifying `V` does not convert a reading
from `mV` to volts. Specify the unit when the calculation depends on it.

Arguments must be quoted strings, rather than variables or expressions, and must
be passed in the order shown. The function name is case-sensitive. Domain, device
class, and unit matching are case-insensitive; `percentage` is also accepted for `%`.

Each source call must match exactly one entity. Missing or ambiguous matches are
logged as template errors and use the normal unavailable/retain-state behaviour.
Use an explicit entity ID when a device has multiple matching sources.

For an entity based note, sources are selected from the entity's device. If the entity
has no device, only that entity is considered. Disabled entities and entities
created by Battery Notes are excluded.

These source calls work in Battery Notes' percentage and low templates. To test
the calculation in Home Assistant's template tools, replace each
`battery_notes_source(...)` call with a quoted entity ID first, for example
`states('sensor.my_sensor_voltage')`.

### Battery percentage examples

Use these in the **Battery Percentage Template** option.

**Linear voltage: 0 volts = 0%, 3 volts = 100%**

``` jinja
{% set v = states(battery_notes_source('sensor', 'voltage', 'V')) %}
{{ (v | float / 3 * 100) | round(0)
   if is_number(v) else 'unknown' }}
```

**Calibrated voltage: 2 volts = 10%, 3 volts = 100%**

``` jinja
{% set v = states(battery_notes_source('sensor', 'voltage', 'V')) %}
{{ (((v | float - 2) / (3 - 2)) * 90 + 10) | round(0)
   if is_number(v) else 'unknown' }}
```

**Binary low-battery state: low = 9%, normal = 100%**

``` jinja
{% set low = states(battery_notes_source('binary_sensor', 'battery')) %}
{{ 9 if low == 'on' else 100 if low == 'off' else 'unknown' }}
```

### Battery low examples

Use these in the **Battery Low Template** option.

**Detect a text state of `Low`**

This example requires a sensor with the `battery` device class that reports text
states. If the text sensor has no device class, use its explicit entity ID instead
of `battery_notes_source()`. Use the actual state value, rather than its translated
display text.

``` jinja
{% set level = states(battery_notes_source('sensor', 'battery')) %}
{{ level == 'Low'
   if level not in ['unknown', 'unavailable'] else 'unknown' }}
```

**Detect a voltage below 1 volt**

``` jinja
{% set v = states(battery_notes_source('sensor', 'voltage', 'V')) %}
{{ (v | float) < 1 if is_number(v) else 'unknown' }}
```
