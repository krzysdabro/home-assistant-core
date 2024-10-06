"""Device tracker for WeConnect integration."""

from typing import cast

from weconnect.elements.parking_position import ParkingPosition
from weconnect.weconnect import Vehicle

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WeConnectConfigEntry
from .coordinator import WeConnectCoordinator
from .entity import WeConnectEntity
from .utils import get_domain


class WeConnectDeviceTracker(WeConnectEntity, TrackerEntity):
    """Device tracker for WeConnect integration."""

    def __init__(self, coordinator: WeConnectCoordinator, vehicle: Vehicle) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, vehicle)

        self._attr_name = None
        self._attr_unique_id = self.vin
        self._attr_translation_key = "car"
        self._attr_source_type = SourceType.GPS

    @property
    def parking_position(self) -> tuple[float, float] | None:
        """Return the parking position."""
        if (domain := get_domain(self.vehicle, "parking", "parkingPosition")) is None:
            return None

        parking_position: ParkingPosition = cast(ParkingPosition, domain)
        return (parking_position.latitude.value, parking_position.longitude.value)

    @property
    def latitude(self) -> float | None:
        """Return the latitude."""
        return self.parking_position[0] if self.parking_position else None

    @property
    def longitude(self) -> float | None:
        """Return the longitude."""
        return self.parking_position[1] if self.parking_position else None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WeConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeConnect device tracker entity."""
    coordinator = config_entry.runtime_data.coordinator

    async_add_entities(
        WeConnectDeviceTracker(coordinator, vehicle) for vehicle in coordinator.vehicles
    )
