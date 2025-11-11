# Battery Notes - AI Coding Instructions

## Project Overview
Battery Notes is a Home Assistant custom integration that tracks battery information for IoT devices. It uses a **sub-entry architecture** where a single config entry can manage multiple battery devices via ConfigSubentry objects.

## Architecture & Core Components

### Config Entry Structure (Critical)
- **Main Config Entry**: Domain-level configuration (`BatteryNotesConfigEntry`)
- **Sub-entries**: Individual device configurations (`ConfigSubentry`) stored in `config_entry.runtime_data.subentries`
- **Coordinators**: Each sub-entry has its own `BatteryNotesSubentryCoordinator` in `config_entry.runtime_data.subentry_coordinators[subentry_id]`

**Key Pattern**: Always iterate through `subentry_coordinators.values()` not the main coordinator when looking for devices.

### Entity Inheritance Structure
- `BatteryNotesEntity` (base class in `entity.py`) - handles device association and common setup
- Sensor classes inherit from both `BatteryNotesEntity` and HA sensor classes
- Example: `class BatteryNotesTypeSensor(BatteryNotesEntity, RestoreSensor)`

### Device Discovery & Library
- `library/library.json`: 10K+ device definitions with battery types
- `discovery.py`: Auto-discovers devices and creates config entries
- Device matching: `manufacturer` + `model` (+ optional `hw_version`)

## Key File Responsibilities

### Core Files
- `__init__.py`: Config entry setup, sub-entry management, platform loading
- `coordinator.py`: Data coordination, battery level tracking, event firing
- `config_flow.py`: UI configuration flows for manual device addition
- `services.py`: Battery replacement service handlers
- `entity.py`: Base entity class with device association logic

### Platform Files
- `sensor.py`: Battery type, battery+, and last replaced sensors
- `binary_sensor.py`: Battery low binary sensors
- `button.py`: Battery replaced action buttons

### Supporting Files
- `library.py`: Device library management and updates
- `discovery.py`: Automatic device discovery from library
- `const.py`: All constants, service schemas, event names
- `store.py`: Persistent storage for user data

## Development Workflow

### Local Development
```bash
# Start HA development server on port 8123
./scripts/develop

# Lint code
./scripts/lint

# Check types (if mypy installed)
mypy custom_components/battery_notes/ --check-untyped-defs
```

### File Structure Conventions
- Put constants in `const.py` with proper categorization
- Use dataclasses for configuration objects
- Service schemas defined in `const.py`, handlers in `services.py`
- All entities extend `BatteryNotesEntity` base class

## Critical Patterns

### Sub-entry Iteration Pattern
```python
# CORRECT - iterate through sub-entry coordinators
for config_entry in hass.config_entries.async_loaded_entries(DOMAIN):
    if not config_entry.runtime_data.subentry_coordinators:
        continue
    for coordinator in config_entry.runtime_data.subentry_coordinators.values():
        if coordinator.device_id == target_device_id:
            # Process device
```

### Entity Registration Pattern
```python
# Use unique_id from coordinator + description suffix
self._attr_unique_id = f"{coordinator.device_id}_{description.unique_id_suffix}"

# Handle entity naming based on device association
if coordinator.source_entity_id and not coordinator.device_id:
    self._attr_translation_placeholders = {"device_name": coordinator.device_name + " "}
```

### Service Implementation Pattern
```python
# Always validate device exists before processing
device_found = False
for coordinator in subentry_coordinators.values():
    if coordinator.device_id == device_id:
        device_found = True
        # Process service call
        break

if not device_found:
    _LOGGER.error("Device %s not configured in Battery Notes", device_id)
    return None
```

## Testing & Validation

### Type Checking
- Project uses mypy with `--check-untyped-defs`
- All major classes use type hints
- ConfigEntry typing: `BatteryNotesConfigEntry = ConfigEntry[BatteryNotesData]`

### Linting
- Uses `ruff` for code formatting and linting
- Config in `pyproject.toml`
- Run `./scripts/lint` before commits

## Integration Points

### Home Assistant APIs
- Device Registry: Link entities to HA devices
- Entity Registry: Manage entity lifecycle
- Event Bus: Fire battery events (`EVENT_BATTERY_THRESHOLD`, `EVENT_BATTERY_REPLACED`)
- Config Flow: Handle UI configuration

### External Dependencies
- Library updates from `https://battery-notes-data.codechimp.org/library.json`
- Version checking with `awesomeversion`
- Data validation with `voluptuous`

## Common Tasks

### Adding New Entity Types
1. Create entity description in appropriate platform file
2. Extend `BatteryNotesEntity` base class
3. Add to platform's `async_setup_entry` function
4. Register constants in `const.py`

### Adding New Services
1. Define schema in `const.py`
2. Implement handler in `services.py` using sub-entry iteration pattern
3. Register in `__init__.py` `async_setup_entry`
4. Add service definition to `services.yaml`
