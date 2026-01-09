"""A Schoology API sensor for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

from .entity import IntegrationBlueprintEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import BlueprintDataUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="announcements",
        name="Schoology Announcements",
        icon="mdi:bullhorn",
    ),
    SensorEntityDescription(
        key="upcoming_events",
        name="Schoology Upcoming Events",
        icon="mdi:calendar",
    ),
    SensorEntityDescription(
        key="upcoming_assignments",
        name="Schoology Upcoming Assignments",
        icon="mdi:clipboard-text",
    ),
    SensorEntityDescription(
        key="overdue_assignments",
        name="Schoology Overdue Assignments",
        icon="mdi:alert-circle-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        IntegrationBlueprintSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )

# @overriding_this_is_totally_okay("native_value")
def overriding_this_is_totally_okay(property_fn):
    classx = property_fn.__self__.__class__
    wrapper = property(property_fn)
    setattr(classx, property_fn.__name__, wrapper)
    def wrapper_getter(self):
        return property_fn(self)
    return wrapper_getter

class IntegrationBlueprintSensor(IntegrationBlueprintEntity, SensorEntity):
    """integration_blueprint Sensor class."""

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self.coordinator.last_update_success

    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        # Ensure unique id per sensor type
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{entity_description.key}"

    @property
    def native_value(self) -> int | None:
        """Return the count of items for this sensor."""
        items = self.coordinator.data.get(self.entity_description.key) or []
        try:
            return len(items)
        except Exception:  # len() may fail if items is not a list
            return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra attributes including the items list."""
        items = self.coordinator.data.get(self.entity_description.key) or []
        return {"items": items}
