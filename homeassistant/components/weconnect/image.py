"""Image entity for WeConnect integration."""

from datetime import datetime
from io import BytesIO

from weconnect.weconnect import Vehicle

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WeConnectConfigEntry
from .coordinator import WeConnectCoordinator
from .entity import WeConnectEntity


class WeConnectImage(WeConnectEntity, ImageEntity):
    """Image entity for WeConnect integration."""

    vehicle_image: BytesIO | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: WeConnectCoordinator,
        vehicle: Vehicle,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(coordinator, vehicle)
        ImageEntity.__init__(self, hass)

        self._attr_name = None
        self._attr_unique_id = self.vin
        self._attr_content_type = "image/png"

        if "car" in self.vehicle.pictures:
            self.vehicle_image = BytesIO()
            self.vehicle.pictures["car"].value.save(self.vehicle_image, "PNG")
            self._attr_image_last_updated = datetime.now()

    async def async_image(self) -> bytes | None:
        """Return the image of the vehicle."""
        return self.vehicle_image.getvalue() if self.vehicle_image else None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WeConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeConnect image entity."""
    coordinator = config_entry.runtime_data.coordinator

    async_add_entities(
        WeConnectImage(hass, coordinator, vehicle) for vehicle in coordinator.vehicles
    )
