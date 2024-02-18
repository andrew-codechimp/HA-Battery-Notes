"""Web sockets for battery_notes."""
import voluptuous as vol
import logging
from datetime import datetime

from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.components.http.data_validator import RequestDataValidator
from homeassistant.helpers import config_validation as cv
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_NAME,
    ATTR_SERVICE,
    CONF_SERVICE_DATA,
    ATTR_STATE,
)

from homeassistant.components.websocket_api import (decorators, async_register_command)

from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from .const import (
    DOMAIN,
    DATA,
    ATTR_DEVICE_ID,
    ATTR_REMOVE,
)

import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

@callback
@decorators.websocket_command({
    vol.Required("type"): "alarmo_config_updated",
})

@decorators.async_response
async def handle_subscribe_updates(hass, connection, msg):
    """Handle subscribe updates."""

    @callback
    def async_handle_event():
        """Forward events to websocket."""
        connection.send_message({
            "id": msg["id"],
            "type": "event",
        })
    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass,
        "alarmo_update_frontend",
        async_handle_event
    )
    connection.send_result(msg["id"])


class BatteryNotesDevicesView(HomeAssistantView):
    """Battery view."""

    url = "/api/batterynotes/devices"
    name = "api:batterynotes:devices"

    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required(ATTR_DEVICE_ID): cv.string,
                vol.Optional(ATTR_REMOVE): cv.boolean,
            }
        )
    )
    async def post(self, request, data):
        """Handle config update request."""
        hass = request.app["hass"]
        for device in hass.data[DOMAIN][DATA].devices:
            if device.device_id == data[ATTR_DEVICE_ID]:

                del data[ATTR_DEVICE_ID]

                device_entry = {"battery_last_replaced": datetime.utcnow()}

                device.coordinator.async_update_device_config(
                    device_id=device.device_id, data=device_entry
                )

                _LOGGER.debug(
                    "Device %s battery replaced via websocket",
                    device.device_id
                )

                async_dispatcher_send(hass, "batterynotes_update_frontend")
                return self.json({"success": True})

        return self.json({"success": False})


@callback
def websocket_get_devices(hass, connection, msg):
    """Publish devices data."""
    devices = hass.data[DOMAIN][DATA].devices

    items = []
    for v in devices.values():
        items.append((v.coordinator.device_id, v.coordinator))

    connection.send_result(msg["id"], dict(items))


async def async_register_websockets(hass):

    hass.http.register_view(BatteryNotesDevicesView)

    async_register_command(
        hass,
        handle_subscribe_updates
    )

    async_register_command(
        hass,
        "batterynotes/devices",
        websocket_get_devices,
        websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
            {vol.Required("type"): "batterynotes/devices"}
        ),
    )
