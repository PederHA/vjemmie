import bs4 as bs
from discord.ext import commands
import discord
from ext_module import ExtModule
import time
from urllib.parse import urlencode
import urllib.request


class WPCog:
    """PUBG Bot Commands
    """

    def __init__(self, bot: commands.Bot, log_channel_id: int=None):
        """The constructor of the UserCog class, assigns the important variables
        Args:
            bot: The bot the commands will be added to (commands.Bot)
            log_channel_id: The id of the log_channel (int)
        """
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.send_log = None                # will be assigned
        self.bot.remove_command('help')

    async def on_ready(self):
        """Is called when the bot is completely started up. Calls in this function need variables only a started bot can give.
        """
        self.send_log = ExtModule.get_send_log(self)

    @commands.command(name="wowprogress",
                      aliases=["wp", "wowp"],
                      description="Searches WoWprogress for a given guild name, and returns top result.")
    async def wowprogress(self, ctx: commands.Context, *args: str):
        try:
            start_time = time.time()
            url = ("https://www.wowprogress.com/search?{}&type=guild".format(
                urlencode({'q': ' '.join(args)})
            ))
            
            sauce = urllib.request.urlopen(url).read()
            soup = bs.BeautifulSoup(sauce, 'html.parser')

            # Finds the top search result and fetches url to guild page
            top_result = soup.find(
                "a", {"class": lambda L: L and L.startswith("guild")})

            # Sends error message to the channel in case a guild cannot be found
            if top_result == None:
                return await ctx.send("Couldn't find guild!")

            # Top result is cast to string, then appended to wowprogress URL
            # to create the full website URL to the guild page
            top_result = str(top_result.get("href"))
            guild_wp_url = "https://wowprogress.com" + top_result

            # Scrapes the resulting URL from the top result
            sauce = urllib.request.urlopen(guild_wp_url).read()
            soup = bs.BeautifulSoup(sauce, "html.parser")

            # Raids Per Week
            raids_per_week = soup.find("div", class_="raids_week")

            # Manage exception for guilds with unknown raid days

            """
            DUNNO WHAT TO DO WITH THIS YET
            #unknown = raids_per_week.find("nobr")
            #print(unknown.string)
            #print(raids_per_week.string)
            #if raids_per_week.string == None:
                #rpwn = "unknown"
            
            #elif raids_per_week.string != None:
            """

            raids_per_week = str(raids_per_week.string).split(": ", 1)[1]

            # Guild name
            guild_name = soup.find("title")
            guild_name = str(guild_name.string).partition("@")[0].split("Guild ", 1)[1]

            # Progression
            progress = soup.find("span", class_="innerLink ratingProgress")
            progress = progress.find("b")
            progress = str(progress.string)

            # World Rank
            world_rank = soup.find("span", {"class": lambda L: L and L.startswith("rank")})
            world_rank = world_rank.string

            # Calculate execution time
            exetime = (time.time()-start_time)
            exetime = "{0:.1f}".format(exetime)

            # TODO: Markdown formatting (bold).    
            await ctx.send(guild_wp_url + ("\n\n```markdown\n"
                                            "Guild Name: {}\n"
                                            "Progress: {}\n"
                                            "World Rank: {}\n"
                                            "Raids Per Week: {}\n"
                                            "```\n"
                                            "👳🏾Command executed in {} seconds").format(guild_name, progress, world_rank, raids_per_week, exetime))        
        except Exception:
            # Lazy solution, but this will be the correct error message to return in 99% of cases.
            await ctx.send("Guild is inactive.")
