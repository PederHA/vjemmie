from discord.ext import commands
import discord
from ext_module import ExtModule
import requests
import shutil
from cogs.base_cog import BaseCog
import unicodedata


class TestingCog(BaseCog):
    """Testing Bot Commands
    """

    @commands.command(name="spotify")
    async def spotify_test(self, ctx: commands.Context, *args) -> None:
        if ctx.message.author.activity.__class__ == discord.activity.Spotify:
            album_cover_url = ctx.message.author.activity.album_cover_url
            self.download_album_art(album_cover_url)
            embed = discord.Embed(title="Spotify", 
                                  description=f"{ctx.message.author.activity.artist} - {ctx.message.author.activity.title}", 
                                  type="link", 
                                  url=f"https://open.spotify.com/track/{ctx.message.author.activity.track_id}", 
                                  provider=(None, "Spotify") 
                                 )
            await ctx.send(f"**{ctx.message.author.name}** is currently listening to: " 
                          f"{ctx.message.author.activity.artist} - "
                          f"{ctx.message.author.activity.title}",
                          embed=embed, file=discord.File("temp/album_cover.jpeg"))
        else:
            await ctx.send("Unable to read Spotify information.")

    def download_album_art(self, url):
        r = requests.get(url, stream=True)
        with open("temp/album_cover.jpeg", 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)   

    @commands.command(name="get_msg")
    async def get_msg(self, ctx: commands.Context, *args) -> None:
        message = int(args[0])
        new_channel = self.bot.get_channel(340921036201525248)
        new_msg = await new_channel.get_message(message)
        for m in new_msg.embeds:
            #print(dir(m))
            pass

        #print(dir(new_msg))
        for embed in new_msg.embeds:
            print(dir(embed))
            print(dir(embed.footer))
            print(embed.footer.text)
    
    
    @commands.command(name="emojis")
    async def emojis(self, ctx:commands.Context, emoji: str, *message) -> None:
        msg = list(message)
        msg.append("")
        msg.insert(0, "")
        await ctx.send(emoji.join(msg))


    @commands.command(name="sheriff")
    async def sheriff(self, ctx: commands.Context, emoji: str) -> None:
        out = """
        \n⁯⁯⁯⁯ 
⠀ ⠀ ⠀    🤠
　   {e}{e}{e}
    {e}   {e}　{e}
    👇  {e}{e} 👇
  　  {e}　{e}
　   {e}　 {e}
　   👢     👢
    """.format(e=emoji)
        try:
            emoji_name = unicodedata.name(emoji)
        except:
            if ":" in emoji:
                emoji_name = emoji.split(":", 3)[1]
            else:
                emoji_name = None
        if emoji_name is not None:
            out += f"\nI am the sheriff of {emoji_name.title()}"
        await ctx.send(out)
    
    @commands.command(name="add_sound")
    async def get_attachment(self, ctx: commands.Context) -> None:
        if hasattr(ctx.message, "attachments") and ctx.message.attachments:
            directories = {
                # Will expand
                "mp3": "sounds"
            }
            # Get attachment info
            attachment = ctx.message.attachments[0]
            file_name, extension = attachment.filename.split(".")
            # Get directory for file type
            directory = directories.get(extension)
            # Raise exception if file type is not recognized
            if not directory:
                raise discord.DiscordException("Invalid file format")   
            # Download & save file
            sound_file = await self.download_from_url(attachment.url)
            with open(f"{directory}/{attachment.filename}", "wb") as f:
                f.write(sound_file)
            await ctx.send(f"Saved file {attachment.filename}")
        else:
            raise discord.DiscordException("Message has no attachment!")
