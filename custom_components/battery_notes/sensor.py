"""Sensor platform for battery_notes."""
from __future__ import annotations

import logging
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
import voluptuous as vol

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    RegistryEntryDisabler,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CONDITION,
    CONF_DOMAIN,
    CONF_ENTITIES,
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_UNIQUE_ID,
)
from .const import DOMAIN, LOGGER, CONF_DEVICE_ID, CONF_BATTERY_TYPE
from .entity import BatteryTypesEntity
from .errors import SensorConfigurationError, SensorAlreadyConfiguredError

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery_notes",
        name="Battery type",
        icon="mdi:battery-unknown",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

SENSOR_CONFIG = {
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_DEVICE_ID): cv.string,
    vol.Optional(CONF_BATTERY_TYPE): cv.string,
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    print(entry.domain + ":" + entry.title)

    entry.data.get(CONF_NAME)
    entry.data.get(CONF_DEVICE_ID)
    entry.data.get(CONF_BATTERY_TYPE)

    await _async_setup_entities(
        hass,
        async_add_entities,
        config_entry=entry,
    )

async def _async_setup_entities(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: ConfigEntry | None = None
    ) -> None:
    """Main routine to setup sensors from provided configuration."""

    try:
        entities = await create_sensors(hass, config_entry)
    except SensorConfigurationError as err:
        _LOGGER.error(err)
        return

    entities_to_add = [
        entity for entity in entities.new if isinstance(entity, SensorEntity)
    ]

    # Remove entities which are disabled because of a disabled device from the list of entities to add
    # When we add nevertheless the entity_platform code will set device_id to None and abort entity addition.
    # `async_added_to_hass` hook will not be called, which powercalc uses to bind the entity to device again
    # This causes the battery type entity to never be bound to the device again and be disabled forever.
    entity_reg = er.async_get(hass)
    for entity in entities_to_add:
        existing_entry = entity_reg.async_get(entity.entity_id)
        if (
            existing_entry
            and existing_entry.disabled_by == RegistryEntryDisabler.DEVICE
        ):
            entities_to_add.remove(entity)

    async_add_entities(entities_to_add)

async def create_sensors(
    hass: HomeAssistant,
    config_entry: ConfigEntry | None = None,
) -> EntitiesBucket:
    """Main routine to create all sensors for a given entity."""

    global_config = hass.data[DOMAIN][DOMAIN_CONFIG]

    # Set up a power sensor for one single appliance. Either by manual configuration or discovery
    if CONF_ENTITIES not in config and CONF_INCLUDE not in config:
        merged_sensor_config = get_merged_sensor_configuration(global_config, config)
        return await create_individual_sensors(
            hass,
            merged_sensor_config,
            context,
            config_entry,
            discovery_info,
        )

    # Setup power sensors for multiple appliances in one config entry
    sensor_configs = {}
    entities_to_add = EntitiesBucket()
    for entity_config in config.get(CONF_ENTITIES, []):
        # When there are nested entities, combine these with the current entities, recursively
        if CONF_ENTITIES in entity_config or context.group:
            try:
                child_entities = await create_sensors(
                    hass,
                    entity_config,
                    context=CreationContext(
                        group=context.group,
                        entity_config=entity_config,
                    ),
                )
                entities_to_add.extend_items(child_entities)
            except SensorConfigurationError as exception:
                _LOGGER.error(
                    f"Group state might be misbehaving because there was an error with an entity: {exception}",
                )
            continue

        entity_id = entity_config.get(CONF_ENTITY_ID) or str(uuid.uuid4())
        sensor_configs.update({entity_id: entity_config})

    # Automatically add a bunch of entities by area or evaluating template
    if CONF_INCLUDE in config:
        entities_to_add.existing.extend(resolve_include_entities(hass, config.get(CONF_INCLUDE)))  # type: ignore

    # Create sensors for each entity
    for sensor_config in sensor_configs.values():
        try:
            merged_sensor_config = get_merged_sensor_configuration(
                global_config,
                config,
                sensor_config,
            )
            entities_to_add.extend_items(
                await create_individual_sensors(
                    hass,
                    merged_sensor_config,
                    config_entry=config_entry,
                    context=CreationContext(
                        group=context.group,
                        entity_config=sensor_config,
                    ),
                ),
            )
        except SensorConfigurationError as error:
            _LOGGER.error(error)

    if not entities_to_add.has_entities():
        exception_message = "Could not resolve any entities"
        if CONF_CREATE_GROUP in config:
            exception_message += f" in group '{config.get(CONF_CREATE_GROUP)}'"
        raise SensorConfigurationError(exception_message)

    # Create group sensors (power, energy, utility)
    if CONF_CREATE_GROUP in config:
        entities_to_add.new.extend(
            await create_group_sensors(
                str(config.get(CONF_CREATE_GROUP)),
                get_merged_sensor_configuration(global_config, config, validate=False),
                entities_to_add.all(),
                hass=hass,
            ),
        )

    return entities_to_add

async def create_individual_sensors(
    hass: HomeAssistant,
    sensor_config: dict,
    config_entry: ConfigEntry | None = None,
) -> EntitiesBucket:
    """Create entities (power, energy, utility_meters) which track the appliance."""

    source_entity = await create_source_entity(sensor_config[CONF_ENTITY_ID], hass)

    if (used_unique_ids := hass.data[DOMAIN].get(DATA_USED_UNIQUE_IDS)) is None:
        used_unique_ids = hass.data[DOMAIN][
            DATA_USED_UNIQUE_IDS
        ] = []  # pragma: no cover
    try:
        await check_entity_not_already_configured(
            sensor_config,
            source_entity,
            hass,
            used_unique_ids,
        )
    except SensorAlreadyConfiguredError as error:
        # Include previously discovered/configured entities in group when no specific configuration
        if context.group and list(context.entity_config.keys()) == [CONF_ENTITY_ID]:
            return EntitiesBucket([], error.get_existing_entities())
        raise error

    entities_to_add: list[Entity] = []
    energy_sensor: EnergySensor | None = None

    try:
        power_sensor = await create_power_sensor(
            hass,
            sensor_config,
            source_entity,
            config_entry,
        )

        entities_to_add.append(power_sensor)
    except PowercalcSetupError:
        return EntitiesBucket()

    # Create energy sensor which integrates the power sensor
    if sensor_config.get(CONF_CREATE_ENERGY_SENSOR):
        energy_sensor = await create_energy_sensor(
            hass,
            sensor_config,
            power_sensor,
            source_entity,
        )
        entities_to_add.append(energy_sensor)
        if isinstance(power_sensor, VirtualPowerSensor):
            power_sensor.set_energy_sensor_attribute(energy_sensor.entity_id)

    if energy_sensor:
        entities_to_add.extend(
            await create_utility_meters(hass, energy_sensor, sensor_config),
        )

    await attach_entities_to_source_device(
        config_entry,
        entities_to_add,
        hass,
        source_entity,
    )

    # Update several registries
    hass.data[DOMAIN][
        DATA_DISCOVERED_ENTITIES if discovery_info else DATA_CONFIGURED_ENTITIES
    ].update(
        {source_entity.entity_id: entities_to_add},
    )

    if source_entity.domain not in hass.data[DOMAIN][DATA_DOMAIN_ENTITIES]:
        hass.data[DOMAIN][DATA_DOMAIN_ENTITIES][source_entity.domain] = []

    hass.data[DOMAIN][DATA_DOMAIN_ENTITIES][source_entity.domain].extend(
        entities_to_add,
    )

    # Keep track for which unique_id's we generated sensors already
    unique_id = sensor_config.get(CONF_UNIQUE_ID) or source_entity.unique_id
    if unique_id:
        used_unique_ids.append(unique_id)

    return EntitiesBucket(new=entities_to_add, existing=[])


async def attach_entities_to_source_device(
    config_entry: ConfigEntry | None,
    entities_to_add: list[Entity],
    hass: HomeAssistant,
    source_entity: SourceEntity,
) -> None:
    """Set the entity to same device as the source entity, if any available."""
    if source_entity.entity_entry and source_entity.device_entry:
        device_id = source_entity.device_entry.id
        device_registry = dr.async_get(hass)
        for entity in (
            entity for entity in entities_to_add if isinstance(entity, BaseEntity)
        ):
            try:
                entity.source_device_id = source_entity.device_entry.id  # type: ignore
            except AttributeError:  # pragma: no cover
                _LOGGER.error(f"{entity.entity_id}: Cannot set device id on entity")
        if (
            config_entry
            and config_entry.entry_id not in source_entity.device_entry.config_entries
        ):
            device_registry.async_update_device(
                device_id,
                add_config_entry_id=config_entry.entry_id,
            )

async def create_energy_sensor(
    hass: HomeAssistant,
    sensor_config: ConfigType,
    power_sensor: PowerSensor,
    source_entity: SourceEntity,
) -> EnergySensor:
    """Create the energy sensor entity."""
    # User specified an existing energy sensor with "energy_sensor_id" option. Just return that one
    if CONF_ENERGY_SENSOR_ID in sensor_config:
        ent_reg = er.async_get(hass)
        energy_sensor_id = sensor_config[CONF_ENERGY_SENSOR_ID]
        entity_entry = ent_reg.async_get(energy_sensor_id)
        if entity_entry is None:
            raise SensorConfigurationError(
                f"No energy sensor with id {energy_sensor_id} found in your HA instance. "
                "Double check `energy_sensor_id` setting",
            )
        return RealEnergySensor(
            entity_entry.entity_id,
            entity_entry.name or entity_entry.original_name,
            entity_entry.unique_id,
        )

    # User specified an existing power sensor with "power_sensor_id" option. Try to find a corresponding energy sensor
    if CONF_POWER_SENSOR_ID in sensor_config and isinstance(
        power_sensor,
        RealPowerSensor,
    ):
        # User can force the energy sensor creation with "force_energy_sensor_creation" option.
        # If they did, don't look for an energy sensor
        if (
            CONF_FORCE_ENERGY_SENSOR_CREATION not in sensor_config
            or not sensor_config.get(CONF_FORCE_ENERGY_SENSOR_CREATION)
        ):
            real_energy_sensor = find_related_real_energy_sensor(hass, power_sensor)
            if real_energy_sensor:
                _LOGGER.debug(
                    f"Found existing energy sensor '{real_energy_sensor.entity_id}' "
                    f"for the power sensor '{power_sensor.entity_id}'",
                )
                return real_energy_sensor
            _LOGGER.debug(
                f"No existing energy sensor found for the power sensor '{power_sensor.entity_id}'",
            )
        else:
            _LOGGER.debug(
                f"Forced energy sensor generation for the power sensor '{power_sensor.entity_id}'",
            )

    # Create an energy sensor based on riemann integral integration, which uses the virtual powercalc sensor as source.
    name = generate_energy_sensor_name(
        sensor_config,
        sensor_config.get(CONF_NAME),
        source_entity,
    )
    unique_id = None
    if power_sensor.unique_id:
        unique_id = f"{power_sensor.unique_id}_energy"

    entity_id = generate_energy_sensor_entity_id(
        hass,
        sensor_config,
        source_entity,
        unique_id=unique_id,
    )
    entity_category = sensor_config.get(CONF_ENERGY_SENSOR_CATEGORY)

    unit_prefix = get_unit_prefix(hass, sensor_config, power_sensor)

    _LOGGER.debug("Creating energy sensor: %s", name)
    return VirtualEnergySensor(
        source_entity=power_sensor.entity_id,
        unique_id=unique_id,
        entity_id=entity_id,
        entity_category=entity_category,
        name=name,
        round_digits=sensor_config.get(CONF_ENERGY_SENSOR_PRECISION),  # type: ignore
        unit_prefix=unit_prefix,
        unit_time=TIME_HOURS,  # type: ignore
        integration_method=sensor_config.get(CONF_ENERGY_INTEGRATION_METHOD)
        or DEFAULT_ENERGY_INTEGRATION_METHOD,
        powercalc_source_entity=source_entity.entity_id,
        powercalc_source_domain=source_entity.domain,
        sensor_config=sensor_config,
    )

class BatteryTypesSensor(BatteryTypesEntity, SensorEntity):
    """battery_notes Sensor class."""

    def __init__(
        self,
        coordinator: BatteryTypesDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("body")