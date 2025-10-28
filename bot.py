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
            command_prefix=self.get_prefix,
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
                "database_url": "sqlite:///moderation.db",
                "embed_color": 0x00ff00,
                "support_server": "",
                "invite_link": ""
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
    
    async def get_prefix(self, bot, message):
        """Dynamic prefix system"""
        if not message.guild:
            return self.config.get('default_prefix', '!')
        
        guild_config = self.guild_configs.get(message.guild.id, {})
        return guild_config.get('prefix', self.config.get('default_prefix', '!'))
    
    async def load_extensions(self):
        """Load all cogs from the cogs directory"""
        cogs_dir = Path('cogs')
        if not cogs_dir.exists():
            cogs_dir.mkdir()
            
        loaded = 0
        failed = 0
        
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
        """Bot ready event"""
        logging.info(f'{self.user} has connected to Discord!')
        logging.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | /help"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        """When bot joins a new guild"""
        logging.info(f'Joined guild: {guild.name} ({guild.id})')
        
        # Initialize guild config
        self.guild_configs[guild.id] = {
            'prefix': self.config.get('default_prefix', '!'),
            'mod_role': None,
            'admin_role': None,
            'mute_role': None,
            'log_channel': None,
            'welcome_channel': None,
            'automod_enabled': True,
            'warn_threshold': 3
        }
    
    async def on_guild_remove(self, guild):
        """When bot leaves a guild"""
        logging.info(f'Left guild: {guild.name} ({guild.id})')
        
        # Clean up guild data
        if guild.id in self.guild_configs:
            del self.guild_configs[guild.id]
        if guild.id in self.mod_logs:
            del self.mod_logs[guild.id]
    
    async def setup_hook(self):
        """Setup hook called when bot starts"""
        await self.load_extensions()
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logging.info(f'Synced {len(synced)} slash commands')
        except Exception as e:
            logging.error(f'Failed to sync commands: {e}')

async def main():
    bot = BallerMemesBot()
    
    # Get token from config or environment
    token = bot.config.get('token') or os.getenv('BOT_TOKEN')
    
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logging.error("No bot token provided! Please set BOT_TOKEN in config.json or environment variable.")
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