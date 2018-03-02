from discord.ext import commands
import discord
from ext_module import ExtModule
from ext_module import PmForbidden
from random import randint


class UserCog:
    """This Cog contains Interaction enhancing commands for the User
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

    @commands.command(name='suggest',
                      aliases=['complain', 'suggestion', 'complaint'],
                      description='(textblock) || The textblock will be send as a suggestion'
                                  ' to the admins of this bot. You can also use this for bug report!')
    @ExtModule.reaction_respond
    async def suggest(self, ctx: commands.Context, *args):
        """This command sends the text given to the log_channel and pins it there.
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            args: The words the text will consist of (str)
            """
        text = ' '
        for word in args:
            text = text + str(word) + ' '
        text = text[:-1]
        _log_channel = self.bot.get_channel(self.log_channel_id)
        if _log_channel is None:
            _log_channel = self.bot.get_user(self.log_channel_id)
        await _log_channel.send('***New suggestion:***' + text)

    @commands.command(name='info',
                      aliases=['information', 'stats', 'statistics'],
                      description='Sends information about the bot')
    @ExtModule.reaction_respond
    async def info(self, ctx: commands.Context):
        """This function sends basic information about the the bot to the ctx.TextChannel
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            """
        embed=discord.Embed(title='', color=discord.Color.from_rgb(randint(0, 255), randint(0, 255), randint(0, 255)))
        embed.set_author(name='VJ Emmie',
                         icon_url='https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Flag_of_Uganda.svg/1200px-Flag_of_Uganda.svg.png')
        embed.set_thumbnail(url='https://i.imgur.com/PSLMtU6.png')
        embed.set_footer(text='Made with the Discord Python API from Rapptz',
                         icon_url='https://avatars0.githubusercontent.com/u/1695103?s=400&v=4')
        embed.add_field(name='Owner', value='Richard')
        embed.add_field(name='Running on', value='Tiger Mafia HQ Mainframe')
        embed.add_field(name='Commands', value=str(len(self.bot.commands)) + '(!help)')
        await ctx.channel.send(embed=embed)

    @commands.command(name='help',
                      aliases=['hlep', 'mayday'],
                      description='Sends you the names, aliases and description of all commands per PM!')
    @ExtModule.reaction_respond
    async def help(self, ctx: commands.Context, *args):
        """This function sends a list of all the command + aliases + description to the requester
        Args:
            ctx: The context of the command, which is mandatory in rewrite (commands.Context)
            """
        _help_string = 'command name || (aliases): || arguments || help description\n'
        for command in self.bot.commands:
            if ExtModule.is_admin_predicate in command.checks:
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