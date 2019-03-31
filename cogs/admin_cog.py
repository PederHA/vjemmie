import asyncio
from datetime import datetime, timedelta
from typing import Optional, Union

import discord
from discord.ext import commands

from cogs.base_cog import BaseCog, EmbedField
from ext.checks import is_admin, load_blacklist, save_blacklist


class AdminCog(BaseCog):
    @commands.Cog.listener()
    async def on_ready(self, *, activity_name: Optional[str]=None) -> None:
        """Is called when the bot is completely started up. Calls in this function need variables only a started bot can give.
        """

        activity_name = "!help" if not activity_name else activity_name
        activity = discord.Game(activity_name)
        await self.bot.change_presence(activity=activity)
        print("Client logged in")
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Is called when the bot joins a new guild. Sends an informative message to the log_channel
        Args:
            guild: The guild which the bot joined on (discord.Guild)
            """
        await self.send_log('Joined guild: ' + guild.name)
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Is called when the bot leaves a guild. Sends an informative message to the log_channel
        Args:
            guild: The guild which was left by the bot (discord.Guild)
            """
        await self.send_log('Left guild: ' + guild.name)
    
    @commands.command(aliases=["change_activity"])
    @is_admin()
    async def ca(self, ctx, activity_name: Optional[str]=None) -> None:
        await self.on_ready(activity_name=activity_name)
    
    @commands.command(name='serverlist',
                      aliases=['list'],
                      description='Prints a list of all the servers'
                                  ' this bot is a member of to the admin log_channel')
    @is_admin()
    async def serverlist(self, ctx: commands.Context) -> None:
        """This function sends a list with all the servers this bot is a member of to the self.log_channel
        Args:
            ctx: The context of the command, which is mandatory in rewrite
        """
        guilds = "\n".join([guild.name for guild in self.bot.guilds])
        await self.send_embed_message(ctx, "Guilds", guilds)

    @commands.command(name='leave',
                      description='(ID) || The bot will attempt to leave the server with the given ID.')
    @is_admin()
    async def leave(self, ctx: commands.Context, guild_id: int=None) -> None:
        """This commands makes the bot leave the server with the given ID
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            guild_id: The id of the server, which will be left (int)
            """
        guild = self.bot.get_guild(int(guild_id))
        try:
            await guild.leave()
        except discord.HTTPException:
            await self.send_log('Could not leave guild ' + guild.name)
            raise discord.DiscordException
        except AttributeError:
            await self.send_log('Guild not found ' + guild.name)
            raise discord.DiscordException
        else:
            await self.send_log('Left guild successfully ' + guild.name)

    @commands.command(name='sendtoall',
                      aliases=['send_to_all', 'send-to-all', 'broadcast'],
                      description='(textblock) || The bot will attempt to send the textblock to every server'
                                  ' he is a member of. Do NOT use for spamming purposes.')
    @is_admin()
    async def sendtoall(self, ctx: commands.Context, *args) -> None:
        """This command tries to send a message to all guilds this bot is a member of.
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            args: The words of the message to be send
            """
        message = ''
        for word in args:
            message = message + str(word) + ' '
        message = message[:-1]
        for guild in self.bot.guilds:
            _channel = guild.text_channels[0]
            _maximum = max([len(channel.members) for channel in guild.text_channels])
            for channel in guild.text_channels:
                if len(channel.members) == _maximum:
                    _channel = channel
                    break               # take the topmost channel with most members reading it
            try:
                await _channel.send(message)
            except discord.Forbidden:
                await self.send_log('Missing permissions for guild ' + guild.name)
            except discord.HTTPException:
                await self.send_log('Failed to send message to ' + guild.name + ' with a connection error')
            else:
                await self.send_log('Successfully send the message to guild ' + guild.name)

    @commands.command(name="blacklist")
    @is_admin()
    async def add_to_blacklist(self, ctx: commands.Context, member: commands.MemberConverter=None, command: str=None, *, output: bool=True) -> None:
        if member: # Proceed if discord.commands.MemberConverter returns a member
            blacklist = load_blacklist() # Get most recent version of blacklist
            if member.id not in blacklist:
                blacklist.append(member.id)
                save_blacklist(blacklist) # Save new version of blacklist
            if output:
                await ctx.send(await self.make_codeblock(f"Added {member.name} to blacklist"))
        else:
            show_cmd = self.bot.get_command("show")
            await ctx.invoke(show_cmd, "blacklist")

    @commands.command(name="show")
    @is_admin()
    async def show_xlist(self, ctx: commands.Context, list_name: str) -> None:
        list_name = list_name.lower()
        out_list = None
        if list_name in ["black", "blacklist", "blvck"]:
            out_list = load_blacklist()
        # TODO: Add other lists (commands, cogs, etc.)
        if out_list:
            out_list = [self.bot.get_user(user_id).name for user_id in out_list]
            out_msg = await self.format_output(out_list)
        else:
            out_msg = await self.make_codeblock("Blacklist is empty")
        await ctx.send(out_msg)        
    
    @commands.command(name="unblacklist", aliases=["remove_blacklist", "rblacklist"])
    @is_admin()
    async def remove_from_blacklist(self, ctx: commands.Context, member: commands.MemberConverter=None, command: str=None, *, output: bool=True) -> None:
        if member: # Proceed if discord.commands.MemberConverter returns a member
            blacklist = load_blacklist() # Get most recent version of blacklist
            if member.id in blacklist:
                blacklist.remove(member.id)
                save_blacklist(blacklist) # Save new version of blacklist
                out_msg = f"Removed {member.name} from blacklist"
        else:
            await ctx.send("Do you want to clear the entire blacklist?")
            def pred(m) -> bool:
                return m.author == ctx.message.author and m.channel == ctx.message.channel
            try:
                reply = await self.bot.wait_for("message", check=pred, timeout=10.0)
            except asyncio.TimeoutError:
                await ctx.send("No reply from user")
            else:
                r = reply.content.lower()
                if r in ["y", "yes"]:
                    save_blacklist([]) # Clear blacklist
                    out_msg = "Cleared blacklist"
                else:
                    out_msg = "Blacklist unchanged"
        if output:
            await ctx.send(await self.make_codeblock(out_msg))

    @commands.command(name="timeout")
    @is_admin()
    async def timeout(self, ctx: commands.Context, member: commands.MemberConverter, duration_min: Union[int, float]=30) -> None:
        sleep_duration_sec = 60 * duration_min
        blacklist_cmd = self.bot.get_command("blacklist")
        unblacklist_cmd = self.bot.get_command("unblacklist")
        await ctx.invoke(blacklist_cmd, member, output=False)
        await ctx.send(f"Timing out {member.name} for {sleep_duration_sec} seconds.")
        await asyncio.sleep(sleep_duration_sec)
        await ctx.invoke(unblacklist_cmd, member, output=False)
        await ctx.send(f"Timeout ended for {member.name}")

    @commands.command(name="delete_messages", aliases=["dlt"])
    @is_admin()
    async def delete_messages(self, 
                              ctx: commands.Context, 
                              member: Optional[str]=None,
                              content: Optional[str]=None) -> None:
        after = datetime.now() - timedelta(hours=2)
        # Any 1 char member name is interpreted as None
        member = await commands.MemberConverter().convert(ctx, member) if len(member)!=1 else None
        n = 0
        async for msg in ctx.message.channel.history(limit=250, after=after):
            if content and content in msg.content and msg.content != ctx.message.content:
                await msg.delete()
                n += 1
            if member and member.name == msg.author.name:
                await msg.delete()
                n += 1
        s = "s" if n>1 else ""
        await ctx.send(f"```\nDeleted {n} message{s}```")

    @commands.command(name="invitelink")
    @is_admin()
    async def invitelink(self, ctx: commands.Context, full_rights: bool=False) -> None:
        base_url = "https://discordapp.com/api/oauth2/authorize?client_id={id}&scope=bot&permissions={permissions}"
        if full_rights:
            url = base_url.format(id=self.bot.user.id, permissions=2146958839)
        else:
            url = base_url.format(id=self.bot.user.id, permissions=66582848)
        await ctx.send(url)
