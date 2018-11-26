import discord
from discord.ext import commands
import requests
from geopy import Nominatim
import xmltodict
from pprint import pprint
from cogs.base_cog import BaseCog

class WeatherCog(BaseCog):
    """
    Holds various weather commands, with data obtained
    via the met.no weather API.
    """
    
    @commands.command()
    async def weather(self, ctx: commands.Context, loc: str) -> None:
        # Instantiate Nominatim geopy object
        geolocator = Nominatim(user_agent="VJEMMIE")
        
        location = geolocator.geocode(loc)
        # Round longitude and latitude to 2 decimal points, and cast to string
        longitude = str(round(location.longitude, 2))
        latitude = str(round(location.latitude, 2))
        
        # Request weather forecast from met.no API using `longitude` and `latitude`
        r = requests.get("https://api.met.no/weatherapi/locationforecast/1.9/"
                         f"?lat={latitude}&lon={longitude}") 
        # Parse returned XML data to dict
        weather_info = xmltodict.parse(r.text, process_namespaces=True)

        # Get weather data for current time
        weather_now = weather_info["weatherdata"]["product"]["time"][0]
        now_temp_c = weather_now["location"]["temperature"]["@value"]
        now_wind_mps = weather_now["location"]["windSpeed"]["@mps"]
        
        await ctx.send(f"{loc.capitalize()}: {now_temp_c}°C, {now_wind_mps} m/s")