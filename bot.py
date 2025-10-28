import discord
from discord.ext import commands
import asyncio
import logging
import json
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

class BallerMemesBot(commands.Bot):
    def __init__(self):
        # Load configuration
        self.config = self.load_config()
        
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.moderation = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=self.prefix_callable,
            intents=intents,
            description="Baller Memes Moderation Bot - Advanced Discord Moderation",
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        # Bot data
        self.guild_configs = {}
        self.mod_logs = {}
        
    def load_config(self):
        """Load bot configuration from config.json"""
        config_path = Path('config.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Create default config
            default_config = {
                "token": "YOUR_BOT_TOKEN_HERE",
                "default_prefix": "!",
                "owner_ids": [],
                "database_url": "sqlite:///data/moderation.db",
                "embed_color": 0x00ff00,
                "support_server": "",
                "invite_link": "",
                "moderation": {
                    "auto_dehoist": True,
                    "auto_delete_invites": False,
                    "spam_detection": True,
                    "raid_protection": True,
                    "max_mentions": 5,
                    "max_emoji": 10,
                    "slowmode_threshold": 5,
                    "profanity_filter": True,
                    "link_filter": False,
                    "caps_filter": True,
                    "repeated_text_filter": True
                },
                "logging": {
                    "mod_actions": True,
                    "message_edits": True,
                    "message_deletes": True,
                    "member_updates": True,
                    "voice_updates": False
                }
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def prefix_callable(self, bot, message):
        """Synchronous dynamic prefix resolver compatible with commands.Bot."""
        try:
            if message.guild is None:
                return self.config.get('default_prefix', '!')
            guild_config = self.guild_configs.get(message.guild.id, {})
            return guild_config.get('prefix', self.config.get('default_prefix', '!'))
        except Exception:
            return '!'
    
    async def load_extensions(self):
        cogs_dir = Path('cogs')
        if not cogs_dir.exists():
            cogs_dir.mkdir()
        loaded = failed = 0
        for cog_file in cogs_dir.glob('*.py'):
            if cog_file.name.startswith('_'):
                continue
            cog_name = f'cogs.{cog_file.stem}'
            try:
                await self.load_extension(cog_name)
                logging.info(f'Loaded cog: {cog_name}')
                loaded += 1
            except Exception as e:
                logging.error(f'Failed to load cog {cog_name}: {e}')
                failed += 1
        logging.info(f'Loaded {loaded} cogs, {failed} failed')
    
    async def on_ready(self):
        logging.info(f'{self.user} has connected to Discord!')
        logging.info(f'Bot is in {len(self.guilds)} guilds')
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.guilds)} servers | /help")
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        logging.info(f'Joined guild: {guild.name} ({guild.id})')
        self.guild_configs[guild.id] = {
            'prefix': self.config.get('default_prefix', '!'),
            'mod_role': None,
            'admin_role': None,
            'mute_role': None,
            'log_channel': None,
            'mod_log_channel': None,
            'member_log_channel': None,
            'message_log_channel': None,
            'welcome_channel': None,
            'automod_enabled': True,
            'warn_threshold': 3
        }
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.guilds)} servers | /help")
        await self.change_presence(activity=activity)
    
    async def on_guild_remove(self, guild):
        logging.info(f'Left guild: {guild.name} ({guild.id})')
        self.guild_configs.pop(guild.id, None)
        self.mod_logs.pop(guild.id, None)
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"{len(self.guilds)} servers | /help")
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ Missing Permissions", description=f"You need: {', '.join(error.missing_permissions)}", color=discord.Color.red())
            return await ctx.send(embed=embed)
        if isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(title="❌ Bot Missing Permissions", description=f"I need: {', '.join(error.missing_permissions)}", color=discord.Color.red())
            return await ctx.send(embed=embed)
        if isinstance(error, commands.MemberNotFound):
            return await ctx.send(embed=discord.Embed(title="❌ Member Not Found", description=f"{error.argument}", color=discord.Color.red()))
        if isinstance(error, commands.UserNotFound):
            return await ctx.send(embed=discord.Embed(title="❌ User Not Found", description=f"{error.argument}", color=discord.Color.red()))
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(embed=discord.Embed(title="⏰ Cooldown", description=f"Wait {error.retry_after:.2f}s", color=discord.Color.orange()))
        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send(embed=discord.Embed(title="❌ Guild Only", description="Use this in a server.", color=discord.Color.red()))
        if isinstance(error, commands.BadArgument):
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Argument", description=str(error), color=discord.Color.red()))
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(embed=discord.Embed(title="❌ Missing Argument", description=f"{error.param.name}", color=discord.Color.red()))
        if isinstance(error, commands.CheckFailure):
            return await ctx.send(embed=discord.Embed(title="❌ Access Denied", description=str(error), color=discord.Color.red()))
        logging.error(f'Ignoring exception in command {ctx.command}:', exc_info=error)
        await ctx.send(embed=discord.Embed(title="❌ Error", description="Unexpected error occurred.", color=discord.Color.red()))
    
    async def setup_hook(self):
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        await self.load_extensions()
        try:
            synced = await self.tree.sync()
            logging.info(f'Synced {len(synced)} slash commands')
        except Exception as e:
            logging.error(f'Failed to sync commands: {e}')

async def main():
    bot = BallerMemesBot()
    token = bot.config.get('token') or os.getenv('BOT_TOKEN')
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logging.error("No bot token provided! Set token in config.json or BOT_TOKEN env var.")
        return
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logging.info('Bot shutdown requested')
    except Exception as e:
        logging.error(f'Bot error: {e}')
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())
