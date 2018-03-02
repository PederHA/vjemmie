import bs4 as bs
from discord.ext import commands
import discord
from ext_module import ExtModule
import time
from urllib.parse import urlencode
import urllib.request

class YTCog:
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
    
    @commands.command(name='youtube',
                        aliases=['yt', 'utube'],
                        description='YouTube search that returns top result for search query.')
    
    @ExtModule.reaction_respond
    async def youtube(self, ctx: commands.Context, *args: str):
        print(args)
        start_time = time.time()
        url = ("https://www.youtube.com/results?{}".format(
                urlencode({'search_query': ' '.join(args)}) 
                ))
        sauce = urllib.request.urlopen(url).read()
        soup = bs.BeautifulSoup(sauce,"html.parser")
        topr = soup.find("div", class_="yt-lockup-thumbnail contains-addto")
        link = topr.find("a", class_=" yt-uix-sessionlink spf-link ")
        """
        print(link.get("href"))
        topresult = link.get("href")
        print (topresult) 
        """
        exetime = (time.time()-start_time)
        exetimestr = "{0:.1f}".format(exetime)
        return await ctx.send("https://youtube.com" + link.get("href"))
        #+ "\nCommand executed in: " + exetimestr + " seconds.")