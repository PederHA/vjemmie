from discord.ext import commands
import discord
from ext_module import ExtModule
from ext_module import PmForbidden
from cogs.admin_utils import load_blacklist, save_blacklist, is_admin
from cogs.base_cog import BaseCog
from typing import Union
import asyncio


class AdminCog(BaseCog):
    """This cog contains commands that can be used by the bots admin(s).
    This will not contain commands, which ban and kick a user or let the bot behave as a server admin.
    """


    async def on_resumed(self) -> None:
        """Is called when the bot made a successfull reconnect, after disconnecting
        """
        await self.send_log("Restarted successfully")

    async def on_ready(self) -> None:
        """Is called when the bot is completely started up. Calls in this function need variables only a started bot can give.
        """
        #self.send_log = ExtModule.get_send_log(self)
        activity = discord.Game(name='Wakaliwood Productions')
        await self.bot.change_presence(activity=activity)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Is called when the bot joins a new guild. Sends an informative message to the log_channel
        Args:
            guild: The guild which the bot joined on (discord.Guild)
            """
        await self.send_log('Joined guild: ' + guild.name)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Is called when the bot leaves a guild. Sends an informative message to the log_channel
        Args:
            guild: The guild which was left by the bot (discord.Guild)
            """
        await self.send_log('Left guild: ' + guild.name)

    @commands.command(name='serverlist',
                      aliases=['list'],
                      description='Prints a list of all the servers'
                                  ' this bot is a member of to the admin log_channel')
    @ExtModule.is_admin()
    async def serverlist(self, ctx: commands.Context) -> None:
        """This function sends a list with all the servers this bot is a member of to the self.log_channel
        Args:
            ctx: The context of the command, which is mandatory in rewrite
        """
        _guild_names = 'List of all guilds: '
        for guild in self.bot.guilds:
            if len(_guild_names) + len(guild.name) > 1800:  # not accurate, 200 literals buffer catch it
                await self.send_log(_guild_names[:-2])
                _guild_names = ''
            else:
                _guild_names = _guild_names + guild.name + '(' + str(guild.id) + ')' + ', '
        await self.send_log(_guild_names[:-2])

    @commands.command(name='leave',
                      description='(ID) || The bot will attempt to leave the server with the given ID.')
    @ExtModule.is_admin()
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
    @ExtModule.is_admin()
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

    @commands.command(name='adminhelp',
                      aliases=['admin-help', 'helpadmin'],
                      description='Sends you the names, aliases and description of all commands per PM!')
    @ExtModule.is_admin()
    async def adminhelp(self, ctx: commands.Context) -> None:
        """This function sends a list of all the admin commands + aliases + description to the requester
                Args:
                    ctx: The context of the command, which is mandatory in rewrite (commands.Context)
        """
        _help_string = 'command name || (aliases): || arguments || help description\n'
        for command in self.bot.commands:
            if ExtModule.is_admin_predicate not in command.checks:
                continue
            _command_help = ExtModule._help(command)
            if len(_help_string) + len(_command_help) > 1800:
                try:
                    await ctx.message.author.send('```\n' + _help_string + '\n```')
                except discord.DiscordException:
                    raise PmForbidden
                _help_string = 'command name || (aliases): || help description\n\n' + _command_help
            else:
                _help_string = _help_string + '\n\n' + _command_help
        try:
            await ctx.author.send('```\n' + _help_string + '\n```')
        except discord.DiscordException:
            raise PmForbidden

    @commands.command(name='change_activity',
                      aliases=['change_game'],
                      description='Changes the activity in the activity feed of the bot')
    @ExtModule.is_admin()
    async def change_activity(self, ctx: commands.Context, *args) -> None:
        activity_name = ""
        first_word = True
        
        for word in args:
            if not first_word:
                activity_name += " "
            activity_name += word
            first_word = False
        
        activity = discord.Game(name=activity_name)
        await self.bot.change_presence(activity=activity)
        await self.send_log(f"Changed activity to: {activity_name}")

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

    @commands.command(name="debug")
    @is_admin()
    async def load_debugger(self, ctx: commands.Context) -> None:
        cmd = [x for x in self.bot.commands if x.name == "remove_sub"][0]
        breakpoint()

