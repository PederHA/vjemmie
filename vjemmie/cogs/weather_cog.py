import xmltodict
from discord.ext import commands
from geopy import Nominatim

from ..utils.http import get
from .base_cog import BaseCog


class WeatherCog(BaseCog):
    """Weather data commands."""

    EMOJI = ":umbrella:"
    geolocator = Nominatim(user_agent="VJEMMIE")

    @commands.command()
    async def weather(self, ctx: commands.Context, location: str) -> None:
        """Get temperature and wind speed for a location."""

        loc_data = self.geolocator.geocode(location)
        # Round longitude and latitude to 2 decimal points, and cast to string
        longitude = str(round(loc_data.longitude, 2))
        latitude = str(round(loc_data.latitude, 2))

        # Request weather forecast from met.no API using longitude and latitude
        r = await get(
            "https://api.met.no/weatherapi/locationforecast/1.9/"
            f"?lat={latitude}&lon={longitude}"
        )

        # Parse returned XML data to dict
        weather_info = xmltodict.parse(r.text, process_namespaces=True)

        # Get weather data for current time
        weather_now = weather_info["weatherdata"]["product"]["time"][0]
        now_temp_c = weather_now["location"]["temperature"]["@value"]
        now_wind_mps = weather_now["location"]["windSpeed"]["@mps"]

        await ctx.send(f"{location.capitalize()}: {now_temp_c}°C, {now_wind_mps} m/s")
