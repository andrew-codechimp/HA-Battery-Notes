"""Test battery_notes integration initialization."""

from unittest.mock import MagicMock, patch

import pytest
from awesomeversion.awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION

from custom_components.battery_notes import async_setup, async_setup_entry
from custom_components.battery_notes.const import DOMAIN, MIN_HA_VERSION
from custom_components.battery_notes.coordinator import MY_KEY, BatteryNotesDomainConfig


class TestBatteryNotesInit:
    """Test class for battery_notes initialization."""

    @pytest.mark.asyncio
    async def test_async_setup_success(self, mock_hass):
        """Test successful async_setup."""
        # Mock the domain config creation
        with patch("custom_components.battery_notes.async_get_registry") as mock_registry, \
             patch("custom_components.battery_notes.async_migrate_integration") as mock_migrate, \
             patch("custom_components.battery_notes.async_setup_services") as mock_services:

            mock_store = MagicMock()
            mock_registry.return_value = mock_store

            # Test configuration
            config = {
                DOMAIN: {
                    "enable_autodiscovery": True,
                    "user_library": "",
                    "show_all_devices": False,
                    "enable_replaced": True,
                    "hide_battery": False,
                    "round_battery": False,
                    "default_battery_low_threshold": 10,
                    "battery_increase_threshold": 25,
                }
            }

            # Call async_setup
            result = await async_setup(mock_hass, config)

            # Verify result
            assert result is True
            assert MY_KEY in mock_hass.data
            assert isinstance(mock_hass.data[MY_KEY], BatteryNotesDomainConfig)

            # Verify store was set
            domain_config = mock_hass.data[MY_KEY]
            assert domain_config.store == mock_store

            # Verify migration and services were called
            mock_migrate.assert_called_once()
            mock_services.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_setup_minimal_config(self, mock_hass):
        """Test async_setup with minimal configuration."""
        with patch("custom_components.battery_notes.async_get_registry") as mock_registry, \
             patch("custom_components.battery_notes.async_migrate_integration"), \
             patch("custom_components.battery_notes.async_setup_services"):

            mock_store = MagicMock()
            mock_registry.return_value = mock_store

            # Minimal config (using defaults)
            config = {DOMAIN: {}}

            result = await async_setup(mock_hass, config)

            assert result is True
            assert MY_KEY in mock_hass.data

            # Check defaults are applied
            domain_config = mock_hass.data[MY_KEY]
            assert domain_config.enable_autodiscovery is True
            assert domain_config.show_all_devices is False
            assert domain_config.enable_replaced is True
            assert domain_config.default_battery_low_threshold == 10

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(self, mock_hass, mock_config_entry, mock_battery_subentry):
        """Test successful async_setup_entry."""
        # Setup domain config first
        domain_config = BatteryNotesDomainConfig()
        domain_config.store = MagicMock()
        mock_hass.data[MY_KEY] = domain_config

        # Mock the subentries property to return our test subentry
        subentries_dict = {"test_subentry_id": mock_battery_subentry}
        with patch.object(mock_config_entry, 'subentries', subentries_dict):

            with patch("custom_components.battery_notes.DiscoveryManager"), \
                 patch("custom_components.battery_notes.BatteryNotesSubentryCoordinator") as mock_coordinator, \
                 patch("custom_components.battery_notes.async_call_later") as mock_call_later:

                # Mock the coordinator
                mock_coordinator_instance = MagicMock()
                mock_coordinator.return_value = mock_coordinator_instance

                # Call async_setup_entry
                result = await async_setup_entry(mock_hass, mock_config_entry)

                # Verify result
                assert result is True

                # Verify config entry runtime data is set
                assert hasattr(mock_config_entry, 'runtime_data')
                assert mock_config_entry.runtime_data.domain_config == domain_config
                assert mock_config_entry.runtime_data.store == domain_config.store

                # Verify subentry coordinators are created
                assert mock_config_entry.runtime_data.subentry_coordinators is not None
                assert "test_subentry_id" in mock_config_entry.runtime_data.subentry_coordinators

                # Verify platforms are setup
                mock_hass.config_entries.async_forward_entry_setups.assert_called_once()

                # Verify delayed discovery is scheduled
                mock_call_later.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_subentries(self, mock_hass, mock_config_entry):
        """Test async_setup_entry with no subentries."""
        # Setup domain config first
        domain_config = BatteryNotesDomainConfig()
        domain_config.store = MagicMock()
        mock_hass.data[MY_KEY] = domain_config

        # Mock empty subentries
        with patch.object(mock_config_entry, 'subentries', {}):

            with patch("custom_components.battery_notes.DiscoveryManager"), \
                 patch("custom_components.battery_notes.async_call_later"):

                result = await async_setup_entry(mock_hass, mock_config_entry)

                # Should still succeed
                assert result is True

                # Runtime data should be set
                assert hasattr(mock_config_entry, 'runtime_data')

                # Subentry coordinators should be empty
                assert mock_config_entry.runtime_data.subentry_coordinators == {}

    @pytest.mark.asyncio
    async def test_async_setup_entry_domain_config_options(self, mock_hass):
        """Test async_setup_entry applies config entry options to domain config."""
        # Setup domain config first
        domain_config = BatteryNotesDomainConfig()
        domain_config.store = MagicMock()
        mock_hass.data[MY_KEY] = domain_config

        # Create a config entry with custom options
        custom_config_entry = ConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Battery Notes Test",
            data={},
            options={
                "show_all_devices": True,
                "hide_battery": True,
                "round_battery": True,
                "default_battery_low_threshold": 15,
                "battery_increase_threshold": 30,
                "advanced_settings": {
                    "enable_autodiscovery": True,
                    "enable_replaced": True,
                    "user_library": "",
                },
            },
            source="user",
            entry_id="test_entry_id",
            unique_id="test_unique_id",
            discovery_keys=set(),
            subentries_data={},
        )

        with patch("custom_components.battery_notes.DiscoveryManager"), \
             patch("custom_components.battery_notes.async_call_later"):

            await async_setup_entry(mock_hass, custom_config_entry)

            # Verify domain config is updated with entry options
            assert domain_config.show_all_devices is True
            assert domain_config.hide_battery is True
            assert domain_config.round_battery is True
            assert domain_config.default_battery_low_threshold == 15
            assert domain_config.battery_increased_threshod == 30

    def test_ha_version_check(self):
        """Test that the integration checks Home Assistant version."""
        # This test verifies the HA version check logic exists
        # In a real scenario, this would test the actual version validation

        # Test that MIN_HA_VERSION is properly defined
        assert MIN_HA_VERSION is not None
        assert AwesomeVersion(MIN_HA_VERSION) <= AwesomeVersion(HA_VERSION)

    @pytest.mark.asyncio
    async def test_async_setup_entry_missing_domain_config(self, mock_hass, mock_config_entry):
        """Test async_setup_entry fails gracefully when domain config is missing."""
        # Don't set up domain config in hass.data

        with pytest.raises(KeyError):
            await async_setup_entry(mock_hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_coordinator_creation(self, mock_hass, mock_config_entry):
        """Test that coordinators are properly created for battery subentries."""
        # Setup domain config
        domain_config = BatteryNotesDomainConfig()
        domain_config.store = MagicMock()
        mock_hass.data[MY_KEY] = domain_config

        # Create multiple subentries with different IDs
        subentry1 = MagicMock()
        subentry1.subentry_type = "battery_note"
        subentry1.subentry_id = "subentry1"
        subentry1.unique_id = "unique1"

        subentry2 = MagicMock()
        subentry2.subentry_type = "battery_note"
        subentry2.subentry_id = "subentry2"
        subentry2.unique_id = "unique2"

        subentries_dict = {
            "subentry1": subentry1,
            "subentry2": subentry2,
        }

        # Mock the subentries property
        with patch.object(mock_config_entry, 'subentries', subentries_dict):

            with patch("custom_components.battery_notes.DiscoveryManager"), \
                 patch("custom_components.battery_notes.BatteryNotesSubentryCoordinator") as mock_coordinator, \
                 patch("custom_components.battery_notes.async_call_later"):

                await async_setup_entry(mock_hass, mock_config_entry)

                # Verify coordinator is created for each subentry
                assert mock_coordinator.call_count == 2

                # Verify coordinators are stored
                assert len(mock_config_entry.runtime_data.subentry_coordinators) == 2
                assert "subentry1" in mock_config_entry.runtime_data.subentry_coordinators
                assert "subentry2" in mock_config_entry.runtime_data.subentry_coordinators
