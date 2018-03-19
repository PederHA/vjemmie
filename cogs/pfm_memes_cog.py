from discord.ext import commands
import discord
from ext_module import ExtModule
import random

class PFMCog:
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

    @commands.command(aliases=["groul", "boomkin", "rapist", "gypsy"])
    async def nezgroul(self, ctx: commands.Context, *args: str):
        pics = ["https://gfycat.com/BlackandwhiteTalkativeJackal", 
                "https://cdn.discordapp.com/attachments/133332608296681472/248548242726322177/asdagfdshg.png", 
                "https://cdn.discordapp.com/attachments/133332608296681472/246292696304451586/IMG_4430.PNG", 
                "https://cdn.discordapp.com/attachments/133332608296681472/234880145889034241/unknown.png",
                "https://cdn.discordapp.com/attachments/133332608296681472/176444075858198532/nezfire.jpg", 
                "http://i.imgur.com/bVsoADA.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/343209346693595136/fatbois.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/343320623239528448/IMG_4551.png",
                "https://cdn.discordapp.com/attachments/133332608296681472/343319705978798080/IMG_4236.png"] 
        await ctx.send(random.choice(pics))

    @commands.command()
    async def pfm(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/269244591503310849/unknown.png", 
                "http://i.imgur.com/XPazNUH.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/343212431977218058/tinyrank0.jpg",
                "http://i.imgur.com/h05JuAi.png"] 
        await ctx.send(random.choice(pics))

    @commands.command()
    async def pman(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/343211786222305300/36875fb5-310f-4289-96f1-e847cc2adf241756539671.jpg"] 
        await ctx.send(random.choice(pics))

    @commands.command()
    async def verdisha(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/102179892115828736/172326946947072002/ZPwT9DS.png", 
                "http://i.imgur.com/2QiTnlp.png"] 
        await ctx.send(random.choice(pics))

    @commands.command()
    async def preach(self, ctx: commands.Context, *args: str):
        pics = ["http://i.imgur.com/yFr0xvx.png"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["tinypriestx", "deadgirlfriendx"])
    async def bigshanex(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/173224145297997824/343366782821728276/ff195d1f6191df12da16326bf97dc7d8.png"] 
        await ctx.send(random.choice(pics))

    @commands.command()
    async def hugo(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/301705840539467776/bv.png"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["brokenlenny"])
    async def lenny(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/172113824617463808/280464199581433856/unknown.png",
                "https://cdn.discordapp.com/attachments/133332608296681472/286564216217927680/IMG_2420.PNG"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["pogboom", "swagforsteve"])
    async def steve(self, ctx: commands.Context, *args: str):
        pics = ["https://gfycat.com/gifs/detail/BlandHomelyGrouper"] 
        await ctx.send(random.choice(pics))

    @commands.command()
    async def yendis(self, ctx: commands.Context, *args: str):
        pics = ["http://i.imgur.com/A3NsDKZ.png", 
                "https://cdn.discordapp.com/attachments/133332608296681472/247195749065031681/unknown.png",
                "https://cdn.discordapp.com/attachments/149839875271688192/343511801910263809/yendis.png"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["calum", "swansea", "heroin"])
    async def khunee(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/342088248819974144/5af61a34d2a8c5ba002882ab1f7a05d9.jpg", 
                "https://cdn.discordapp.com/attachments/133332608296681472/333309328494690304/image.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/324653838973796353/9047af55cfbfdce4a929a6b7c17086b7.png", 
                "https://cdn.discordapp.com/attachments/133332608296681472/314557489951801344/unknown.png",
                "https://cdn.discordapp.com/attachments/133332608296681472/197024217693159425/sad_khuneeu.jpg", 
                "https://cdn.discordapp.com/attachments/133332608296681472/206982957301366785/Screenshot_20160725-05540901.png",
                "https://cdn.discordapp.com/attachments/173224145297997824/343348685360594945/176015585cc3138fa05b89b10e6e5615.png",
                "http://i.imgur.com/TPlPUIW.png",
                "http://i.imgur.com/kiiBpmq.png",
                "https://cdn.discordapp.com/attachments/140876808529772544/344861056922812416/Shreksea.png",
                "https://i.imgur.com/uNZej45.png"]
        await ctx.message.add_reaction('\U0000267F')
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["dynei"])
    async def razjar(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/338256009740943370/image.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/190476647844151297/CkhCm4UWUAAUT6t.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/343554796470534145/raz.png",
                "https://i.redd.it/glntfeytgeoz.jpg"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["rank2"])
    async def hoob(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/343210872656756736/dreams.jpg",
                "https://cdn.discordapp.com/attachments/149839875271688192/416320428907298816/hoobys.png"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["turk", "kebab"])
    async def huya(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/336298291895730176/unknown.png", 
                "https://cdn.discordapp.com/attachments/133332608296681472/272878131944095745/C2z7OP_VIAARE8j.png",
                "https://cdn.discordapp.com/attachments/133332608296681472/227505429133918210/greek.png", 
                "http://i.imgur.com/tC6M8wJ.png", 
                "http://i.imgur.com/9QcObXT.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/192817286183124993/huyairl.png",
                "https://cdn.discordapp.com/attachments/133332608296681472/343209878619422720/Sadhuya.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/343210046198382594/ss2017-01-29at03.38.43.jpg",
                "https://gyazo.com/5d35dd4085634a555c4e397ee86f4fee",
                "https://cdn.discordapp.com/attachments/133332608296681472/343337484861702145/image.jpg"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["fidgetspinner", "420"])
    async def notey(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/332914591782928394/image.jpg", 
        "https://cdn.discordapp.com/attachments/133332608296681472/248937367535091723/unknown.png",
        "https://cdn.discordapp.com/attachments/133332608296681472/192807153965334532/unknown.png",
        "https://cdn.discordapp.com/attachments/133332608296681472/343211466213818378/Noteybreak.jpg"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["emil", "pedo", "pedorad", "email"])
    async def rad(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/343319573849833473/IMG_3920.png",
                "https://www.youtube.com/watch?v=pNWEwAIhNH0"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["travis", "triggered"])
    async def truffles(self, ctx: commands.Context, *args: str):
        pics = ["https://www.youtube.com/watch?v=zNYnTsIJqU4",
                "https://cdn.discordapp.com/attachments/133332608296681472/309831544699355136/unknown.png",
                "https://cdn.discordapp.com/attachments/133332608296681472/278711774822268938/unknown.png"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["zizzka", "janis"])
    async def zizzkka(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/336259933366517761/zizzkka_is_a_nig.jpg", 
                "https://cdn.discordapp.com/attachments/133332608296681472/239562154812899329/unknown.png",
                "https://cdn.discordapp.com/attachments/133332608296681472/226136520606613505/WoWScrnShot_091616_022514.jpg",
                "https://cdn.discordapp.com/attachments/133332608296681472/215562907218477056/unknown.png"] 
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["affix"])
    async def affixes(self, ctx: commands.Context, *args: str):
        pics = "https://cdn.discordapp.com/attachments/133332608296681472/337622973114613771/ss2017-05-27at06.33.42.png" 
        await ctx.send(pics)

    @commands.command(aliases=["gays"])
    async def frosty(self, ctx: commands.Context, *args: str):
        pics = "https://www.youtube.com/watch?v=UFXYYVm5kos" 
        await ctx.send(pics)

    @commands.command(aliases=["daevi"])
    async def tekk(self, ctx: commands.Context, *args: str):
        pics = ["This is the beginning of your direct message history with Daevi.\n[20:26] Tekk: i am sorry i called you a nigger",
                "https://i.imgur.com/s5MhmnD.png"]
        await ctx.send(random.choice(pics))

    @commands.command(aliases=["liam", "fattydoobies", "doobieshank"])
    async def doobies(self, ctx: commands.Context, *args: str):
        pics = ["https://cdn.discordapp.com/attachments/133332608296681472/343320054584049665/IMG_4099.png", 
                "https://cdn.discordapp.com/attachments/133332608296681472/343320054584049664/IMG_3900.png"] 
        await ctx.send(random.choice(pics))

    @commands.command()
    async def psio(self, ctx: commands.Context, *args: str):
        with open('memes/psio.txt', 'r', encoding='utf8') as meme:
            await ctx.send(meme.read())
    
    @commands.command()
    async def goodshit(self, ctx: commands.Context, *args: str):
        with open('memes/goodshit.txt', 'r', encoding='utf8') as meme:
            await ctx.send(meme.read())