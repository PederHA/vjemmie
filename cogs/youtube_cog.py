import bs4 as bs
from discord.ext import commands
import discord
from ext_module import ExtModule
import time
from urllib.parse import urlencode
import urllib.request
from cogs.base_cog import BaseCog

class YouTubeCog(BaseCog):
    """YouTube commands
    """
    
    @commands.command(name='youtube',
                        aliases=['yt', 'utube'],
                        description='YouTube search that returns top result for search query.')                       
    async def youtube(self, ctx: commands.Context, *args: str):
        start_time = time.time()
        
        url = ("https://www.youtube.com/results?{}".format(
                urlencode({'search_query': ' '.join(args)}) 
                ))
        sauce = urllib.request.urlopen(url).read()
        soup = bs.BeautifulSoup(sauce,"html.parser")
        
        link = soup.find("div", class_="yt-lockup-thumbnail contains-addto").find("a", class_=" yt-uix-sessionlink spf-link ").get("href")
        
        exetime = (time.time()-start_time)
        exetime = "{0:.1f}".format(exetime)

        await ctx.send(("https://youtube.com{}").format(link))
