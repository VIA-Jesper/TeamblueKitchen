"""DataUpdateCoordinator for TeamblueKitchen."""
from datetime import datetime, timedelta
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION = 1

class TeamblueCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, session, api_url: str):
        """Initialize."""
        self.session = session
        self.api_url = api_url
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data_cache = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None, # We use a manual schedule instead
        )

        # Schedule update every day at 00:01
        async_track_time_change(
            self.hass,
            self._async_scheduled_update,
            hour=0,
            minute=1,
            second=0,
        )

    async def _async_scheduled_update(self, _now=None):
        """Trigger update at scheduled time."""
        _LOGGER.debug("Running scheduled midnight update for TeamblueKitchen")
        await self.async_request_refresh()

    async def _async_load_cache(self):
        """Load data from storage."""
        data = await self._store.async_load()
        if data:
            self._data_cache = data
        else:
            self._data_cache = {"week_plan": {}, "items": []}

    async def _async_save_cache(self):
        """Save data to storage."""
        await self._store.async_save(self._data_cache)

    async def _async_update_data(self):
        """Fetch data from API and merge with cache."""
        if self._data_cache is None:
            await self._async_load_cache()

        fresh_items = self._data_cache.get("items", [])
        
        try:
            async with self.session.get(self.api_url, timeout=10) as response:
                response.raise_for_status()
                fresh_data = await response.json()
                
                # Check for changes
                data_changed = False
                
                # Update freezer
                fresh_items = fresh_data.get("items", [])
                if self._data_cache.get("items") != fresh_items:
                    self._data_cache["items"] = fresh_items
                    data_changed = True

                # Merge week plan
                fresh_week_plan = fresh_data.get("week_plan", [])
                if isinstance(self._data_cache.get("week_plan"), list):
                     self._data_cache["week_plan"] = {}

                cached_plan = self._data_cache["week_plan"]
                current_date = datetime.now().date()

                # Clean old data: Remove anything older than 7 days
                cutoff_date = current_date - timedelta(days=7)
                dates_to_remove = [
                    d_str for d_str in cached_plan
                    if datetime.strptime(d_str, "%Y-%m-%d").date() < cutoff_date
                ]
                for d in dates_to_remove:
                    del cached_plan[d]
                    data_changed = True

                # Add/Update fresh data and check if it actually changes anything
                for item in fresh_week_plan:
                    date_str = item.get("date")
                    if date_str:
                        if cached_plan.get(date_str) != item:
                            cached_plan[date_str] = item
                            data_changed = True

                if data_changed:
                    self._data_cache["week_plan"] = cached_plan
                    await self._async_save_cache()
                    _LOGGER.info("TeamblueKitchen data updated and saved")

        except Exception as err:
            _LOGGER.warning("Could not update TeamblueKitchen from API, using cached data: %s", err)
            if not self._data_cache.get("week_plan") and not self._data_cache.get("items"):
                raise UpdateFailed(f"API down and no cached data available: {err}")

        # Always process what we have in cache
        cached_plan = self._data_cache.get("week_plan", {})
        sorted_plan = sorted(cached_plan.values(), key=lambda x: x.get("date", "9999-99-99"))
        
        return {
            "week_plan": sorted_plan,
            "items": self._data_cache.get("items", []),
            "todays_meal": self._get_today_meal(sorted_plan)
        }

    def _get_today_meal(self, week_plan):
        today = datetime.now().strftime("%Y-%m-%d")
        for item in week_plan:
            if item.get("date") == today:
                return item.get("dish", "Ingen ret fundet")
        return "Ingen menu i dag"
