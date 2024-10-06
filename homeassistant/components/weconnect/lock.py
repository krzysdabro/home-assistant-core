"""Lock entity for WeConnect integration."""

import asyncio
from typing import Any, cast

from weconnect.domain import Domain
from weconnect.elements.access_status import AccessStatus
from weconnect.elements.control_operation import AccessControlOperation
from weconnect.errors import ControlError
from weconnect.weconnect import Vehicle

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WeConnectConfigEntry
from .coordinator import WeConnectCoordinator
from .entity import WeConnectEntity
from .utils import get_domain


class WeConnectLock(WeConnectEntity, LockEntity):
    """Lock entity for WeConnect integration."""

    def __init__(self, coordinator: WeConnectCoordinator, vehicle: Vehicle) -> None:
        """Initialize the lock entity."""
        super().__init__(coordinator, vehicle)

        self._attr_name = None
        self._attr_unique_id = self.vin

    @property
    def is_locked(self) -> bool | None:
        """Return the lock state."""
        if (domain := get_domain(self.vehicle, "access", "accessStatus")) is None:
            return None

        access_status: AccessStatus = cast(AccessStatus, domain)
        return access_status.overallStatus.value == AccessStatus.OverallState.SAFE  # type: ignore[no-any-return]

    @property
    def icon(self) -> str:
        """Return the entity icon."""
        return "mdi:car-door-lock" if self.is_locked else "mdi:car-door-lock-open"

    async def wait_for_state(
        self, state: AccessStatus.OverallState, timeout: int = 60, interval: int = 5
    ) -> None:
        """Wait for the state of the lock to change."""
        async with asyncio.timeout(timeout):
            while True:
                await self.hass.async_add_executor_job(
                    self.vehicle.updateStatus, False, False, [Domain.ACCESS]
                )

                domain = get_domain(self.vehicle, "access", "accessStatus")
                access_status: AccessStatus = cast(AccessStatus, domain)
                if access_status.overallStatus.value == state:
                    break

                await asyncio.sleep(interval)

    async def set_access_control(self, operation: AccessControlOperation) -> None:
        """Set the access control of the vehicle."""

        def _set_value() -> None:
            self.vehicle.controls.accessControl.value = operation

        try:
            await self.hass.async_add_executor_job(_set_value)
            await self.wait_for_state(
                AccessStatus.OverallState.UNSAFE
                if operation == AccessControlOperation.UNLOCK
                else AccessStatus.OverallState.SAFE
            )
        except ControlError as err:
            raise HomeAssistantError(err) from err
        except TimeoutError as err:
            raise HomeAssistantError("Operation timed out") from err

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the vehicle."""
        self._attr_is_locking = True
        self.async_write_ha_state()

        try:
            await self.set_access_control(AccessControlOperation.LOCK)
        finally:
            self._attr_is_locking = False
            self.async_write_ha_state()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the vehicle."""
        self._attr_is_unlocking = True
        self.async_write_ha_state()

        try:
            await self.set_access_control(AccessControlOperation.UNLOCK)
        finally:
            self._attr_is_unlocking = False
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle the update of the coordinator."""
        self._attr_is_locking = False
        self._attr_is_unlocking = False

        if (domain := get_domain(self.vehicle, "access", "accessStatus")) is not None:
            access_status: AccessStatus = cast(AccessStatus, domain)
            self._attr_extra_state_attributes = {}

            for door in access_status.doors:
                d = access_status.doors[door]
                if d.openState.value == AccessStatus.Door.OpenState.UNSUPPORTED:
                    continue
                self._attr_extra_state_attributes[f"door_{door}"] = d.openState.value

            for window in access_status.windows:
                w = access_status.windows[window]
                if w.openState.value == AccessStatus.Window.OpenState.UNSUPPORTED:
                    continue
                self._attr_extra_state_attributes[f"window_{window}"] = (
                    w.openState.value
                )

        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WeConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WeConnect lock entity."""
    coordinator = config_entry.runtime_data.coordinator

    async_add_entities(
        WeConnectLock(coordinator, vehicle) for vehicle in coordinator.vehicles
    )
