"""DataUpdateCoordinator for TeamblueKitchen."""
from datetime import datetime, timedelta
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store

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
            update_interval=timedelta(hours=24),
        )

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

        try:
            # Depending on API, auth might be header or query param. 
            # User removed api key requirement.
            
            async with self.session.get(self.api_url) as response:
                if response.status == 401:
                    # Try alternate if needed? Or just fail.
                    pass
                response.raise_for_status()
                fresh_data = await response.json()

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

        # fresh_data expected structure:
        # {
        #   "days": [ {"date": "2023-10-23", "dish": "Pasta"} ], 
        #   "freezer": [ ... ]
        # }
        # Note: I am guessing the structure based on the previous sensor.py (which used 'week_plan' and 'items')
        
        # Merge Logic
        fresh_week_plan = fresh_data.get("week_plan", [])
        fresh_items = fresh_data.get("items", []) # Freezer items likely don't need history, just current state.

        # Update freezer directly
        self._data_cache["items"] = fresh_items

        # Merge week plan
        # We want to keep days from the current week that might have fallen off the API response.
        # But we also don't want to keep data from last year.
        # Strategy: 
        # 1. Identify the current ISO week.
        # 2. Filter our cache to only keep days that belong to the current week (or future).
        # 3. Update with fresh data.
        
        current_date = datetime.now().date()
        current_iso_week = current_date.isocalendar()[1]
        
        # Convert cache list to dict for easier merging by date
        # Check if cache is list or dict (from previous saves)
        # We will store week_plan as a DICT in the cache: "YYYY-MM-DD": {data}
        if isinstance(self._data_cache.get("week_plan"), list):
             # Migration from list to dict if needed (or just reset)
             self._data_cache["week_plan"] = {}

        cached_plan = self._data_cache["week_plan"]

        # Clean old weeks
        dates_to_remove = []
        for date_str in cached_plan:
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                if d.isocalendar()[1] != current_iso_week and d < current_date:
                    dates_to_remove.append(date_str)
            except ValueError:
                dates_to_remove.append(date_str)
        
        for d in dates_to_remove:
            del cached_plan[d]

        # Add/Update fresh data
        for item in fresh_week_plan:
            date_str = item.get("date")
            if date_str:
                cached_plan[date_str] = item

        # Save back to disk
        self._data_cache["week_plan"] = cached_plan
        await self._async_save_cache()
        
        # Return structured data for sensors
        # Convert dict back to sorted list for the sensor to consume easily
        sorted_plan = sorted(cached_plan.values(), key=lambda x: x.get("date", "9999-99-99"))
        
        # Use API's todays_meal if available, otherwise try to find it in the plan
        api_todays_meal = fresh_data.get("todays_meal")
        if not api_todays_meal:
            api_todays_meal = self._get_today_meal(sorted_plan)

        return {
            "week_plan": sorted_plan,
            "items": fresh_items,
            "todays_meal": api_todays_meal
        }

    def _get_today_meal(self, week_plan):
        today = datetime.now().strftime("%Y-%m-%d")
        for item in week_plan:
            if item.get("date") == today:
                return item.get("dish", "Ingen ret fundet")
        return "Ingen menu i dag"
