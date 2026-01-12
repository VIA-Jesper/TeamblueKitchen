"""Sensor platform for TeamblueKitchen."""
from __future__ import annotations

import logging
import urllib.parse
import hashlib
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TeamblueCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: TeamblueCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        TodaysMealSensor(coordinator),
        WeekPlanSensor(coordinator),
        FreezerCountSensor(coordinator),
    ])

class BaseSensor(CoordinatorEntity[TeamblueCoordinator], SensorEntity):
    """Base class for TeamblueKitchen sensors."""

    def __init__(self, coordinator: TeamblueCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "main")},
            "name": "Teamblue Kitchen",
            "manufacturer": "TeamBlue",
        }

class TodaysMealSensor(BaseSensor):
    """Sensor showing today's meal."""

    _attr_unique_id = "teamblue_todays_meal"
    _attr_name = "Dagens Ret"
    _attr_icon = "mdi:food"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor based on current date."""
        week_plan = self.coordinator.data.get("week_plan", [])
        today = datetime.now().strftime("%Y-%m-%d")
        
        for item in week_plan:
            if item.get("date") == today:
                return item.get("dish", "Ingen ret fundet")
                
        return "Ingen menu i dag"

    @property
    def entity_picture(self) -> str | None:
        """Return a generated image for the dish."""
        try:
            dish = self.native_value
            if not dish or dish in ["Ingen data", "Ingen menu i dag", "Unknown"]:
                return None
            
            # Clean string to avoid URL issues
            clean_dish = urllib.parse.quote(dish)
            
            # Use date as seed to keep image stable throughout the day
            today = datetime.now().strftime("%Y-%m-%d")
            seed = int(hashlib.sha256(today.encode('utf-8')).hexdigest(), 16) % 10000
            
            # Use pollination.ai for free AI generation of the food image
            return f"https://image.pollinations.ai/prompt/delicious%20food%20photo%20of%20{clean_dish}?width=1024&height=1024&nologo=true&seed={seed}&model=flux"
        except Exception as e:
            _LOGGER.warning("Error generating image URL: %s", e)
            return None

    @property
    def extra_state_attributes(self):
        """Return details about the meal."""
        week_plan = self.coordinator.data.get("week_plan", [])
        today_date = datetime.now().strftime("%Y-%m-%d")
        
        # Find full object for today to give more attributes if available
        today_obj = next((x for x in week_plan if x.get("date") == today_date), None)
        
        if today_obj:
            return today_obj
        return {}

class WeekPlanSensor(BaseSensor):
    """Sensor showing the summary of the week plan."""
    
    _attr_unique_id = "teamblue_week_plan"
    _attr_name = "Ugeplan"
    _attr_icon = "mdi:calendar-week"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        # Just return current week number or a simple summary
        week_num = datetime.now().isocalendar()[1]
        return f"Uge {week_num}"

    @property
    def extra_state_attributes(self):
        """Return the full week plan as attributes."""
        week_plan = self.coordinator.data.get("week_plan", [])
        
        # Format it nicely by weekday name
        attributes = {}
        for item in week_plan:
            date_str = item.get("date")
            try:
                # Get Danish day name if possible, or just English
                d = datetime.strptime(date_str, "%Y-%m-%d")
                # Simple mapping for Danish
                days = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
                day_name = days[d.weekday()]
                attributes[day_name] = item.get("dish", "")
            except Exception:
                pass
        
        # Also include the raw list for frontend iteration
        attributes["raw_plan"] = week_plan
        # Add a simple list of all dishes for easy searching in automations
        attributes["dishes"] = [item.get("dish", "") for item in week_plan]
        return attributes

class FreezerCountSensor(BaseSensor):
    """Sensor showing number of items in freezer."""

    _attr_unique_id = "teamblue_freezer_count"
    _attr_name = "Fryser Indhold"
    _attr_icon = "mdi:fridge"
    _attr_native_unit_of_measurement = "retter"

    @property
    def native_value(self) -> int:
        """Return number of items."""
        items = self.coordinator.data.get("items", [])
        return len(items)

    @property
    def extra_state_attributes(self):
        """Return the list of items."""
        items = self.coordinator.data.get("items", [])
        return {"items": items}
