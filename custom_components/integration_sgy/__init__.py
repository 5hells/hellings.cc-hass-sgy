"""
Custom integration to integrate integration_sgy with Home Assistant.

For more details about this integration, please refer to
https://github.com/5hells/hellings.cc-hass-sgy
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
import asyncio

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import IntegrationBlueprintApiClient
from .const import DOMAIN, LOGGER, CONF_API_BASE, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from .coordinator import BlueprintDataUpdateCoordinator
from .data import IntegrationBlueprintData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import IntegrationBlueprintConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]

# List of frontend card directories
FRONTEND_CARDS = [
    "schoology-announcements",
    "schoology-assignments",
    "schoology-overdue",
    "schoology-upcoming",
]

# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    # Register static path for frontend cards
    hass.http.register_static_path(
        f"/frontend/{DOMAIN}",
        hass.config.path(f"custom_components/{DOMAIN}/frontend"),
    )

    update_interval_minutes = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    coordinator = BlueprintDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(minutes=update_interval_minutes),
    )
    entry.runtime_data = IntegrationBlueprintData(
        client=IntegrationBlueprintApiClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
            api_base=entry.data.get(CONF_API_BASE) or "x.schoology.com",
        ),
        coordinator=coordinator,
        integration=async_get_loaded_integration(hass, DOMAIN),
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Automatically add frontend card resources to Lovelace
    async def _add_lovelace_resources():
        """Add Lovelace resources with delay to ensure Lovelace is loaded."""
        await asyncio.sleep(2)  # Wait for Lovelace to initialize
        if "lovelace" in hass.data:
            try:
                lovelace_data = hass.data["lovelace"]
                LOGGER.debug("Lovelace data type: %s", type(lovelace_data))
                if hasattr(lovelace_data, "resources"):
                    resources = lovelace_data.resources
                    LOGGER.debug("Resources object: %s, type: %s", resources, type(resources))
                    if resources and hasattr(resources, "async_create_item"):
                        for card in FRONTEND_CARDS:
                            url = f"/frontend/{DOMAIN}/{card}/card.js"
                            try:
                                existing = await resources.async_get_items()
                                LOGGER.debug("Existing resources: %s", [r.get("url") for r in existing])
                                if not any(res.get("url") == url for res in existing):
                                    await resources.async_create_item({"res_type": "module", "url": url})
                                    LOGGER.info("Added Lovelace resource: %s", url)
                                else:
                                    LOGGER.debug("Lovelace resource already exists: %s", url)
                            except Exception as e:
                                LOGGER.warning("Failed to add Lovelace resource %s: %s", url, e)
                    else:
                        LOGGER.warning("Resources object not available or missing async_create_item method")
                else:
                    LOGGER.warning("Lovelace data does not have resources attribute")
            except Exception as e:
                LOGGER.warning("Failed to access Lovelace data: %s", e)
        else:
            LOGGER.info("Lovelace not in hass.data after delay, skipping automatic resource addition")

    # Try to add resources immediately and also schedule delayed addition
    hass.async_create_task(_add_lovelace_resources())

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
