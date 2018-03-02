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
                        description="Searches Wowprogress for a given guild name and returns top result ")

    #@ExtModule.reaction_respond
    async def wowprogress(self, ctx: commands.Context, *args: str):
        try:    
            start_time = time.time()
            url = ("https://www.wowprogress.com/search?{}&type=guild".format(
                    urlencode({'q': ' '.join(args)}) 
                    ))
            sauce = urllib.request.urlopen(url).read()
            soup = bs.BeautifulSoup(sauce,'html.parser')
            
            #Finds the top search result and fetches url to guild page
            topr = soup.find("a", {"class" : lambda L: L and L.startswith("guild")})
            
            #Sends error message to the channel in case a guild cannot be found
            if topr == None:
                return await ctx.send("Couldn't find guild!")

            #Top result is cast to string, then appended to wowprogress URL
            #to create the complete URL to the guild page
            topr = str(topr.get("href"))
            appendresult = "https://wowprogress.com" + topr

            #Scrapes the resulting URL from the top result
            sauce = urllib.request.urlopen(appendresult).read()
            soup = bs.BeautifulSoup(sauce,"html.parser")

            #Raids Per Week
            wprw = soup.find("div", class_="raids_week")
            
            #Manage exception for guilds with unknown raid days
            

            """
            DUNNO WHAT TO DO WITH THIS YET
            #unknown = wprw.find("nobr")
            #print(unknown.string)
            #print(wprw.string)
            #if wprw.string == None:
                #rpwn = "unknown"
            
            #elif wprw.string != None:
            """

            rpw = str(wprw.string)
            rpw = rpw.split(": ", 1)[1]

                            #elif unknown.string == None:
                            #print(rpw)

            #Guild name
            gname = soup.find("title")
            gname = str(gname.string)
            gname = gname.partition("@")[0]
            gname = gname.split("Guild ", 1)[1]

            #Progression
            progress = soup.find("span", class_="innerLink ratingProgress")
            progress = progress.find("b")
            progress = str(progress.string)
            
            #World Rank
            wrank = soup.find("span", {"class" : lambda L: L and L.startswith("rank")})

            #Calculate execution time
            exetime = (time.time()-start_time)
            exetime = "{0:.1f}".format(exetime) 

            #TODO: Use .format() instead.
            #      Also, not sure what I was doing with regards to using the bs4 string method vs explicitly casting to string back then.
            return await ctx.send(appendresult + "\n```\n\n" + "Guild Name: " + gname + "\nProgress: " + progress + "\nWorld Rank: " 
                        + wrank.string + "\n" + "Raids Per Week: " + rpw + "\n```" + "\n" + "👳🏾" +  "Command executed in " + exetime + " seconds")
        except Exception:
            return await ctx.send("Guild is inactive.") #Lazy solution, but it will be correct error message in 99% of cases.      