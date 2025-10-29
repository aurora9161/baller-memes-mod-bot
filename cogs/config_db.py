import discord
from discord.ext import commands
from discord import app_commands
from utils.database import DB

class ConfigDB(commands.Cog):
    """Persist /config changes to the database and load on startup."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Prime cache from DB for all guilds
        for guild in self.bot.guilds:
            settings = await DB.get_guild_settings(guild.id)
            self.bot.guild_configs[guild.id] = {
                'prefix': settings.get('prefix', self.bot.config.get('default_prefix', '!')),
                'mod_role': settings.get('mod_role_id'),
                'admin_role': settings.get('admin_role_id'),
                'mute_role': settings.get('mute_role_id'),
                'log_channel': settings.get('log_channel_id'),
                'mod_log_channel': settings.get('mod_log_channel_id'),
                'member_log_channel': settings.get('member_log_channel_id'),
                'message_log_channel': settings.get('message_log_channel_id'),
                'welcome_channel': settings.get('welcome_channel_id'),
                'automod_enabled': settings.get('automod_enabled', 1) == 1,
                'warn_threshold': settings.get('warn_threshold', 3)
            }

    # Hooks to persist config updates from existing /config commands
    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        # Expect cogs/config.py to set ctx.config_update dict when changing settings
        payload = getattr(ctx, 'config_update', None)
        if not payload or not isinstance(payload, dict):
            return
        guild_id = ctx.guild.id
        # Map known keys to DB columns
        mapping = {
            'prefix': 'prefix',
            'mod_role': 'mod_role_id',
            'admin_role': 'admin_role_id',
            'mute_role': 'mute_role_id',
            'log_channel': 'log_channel_id',
            'mod_log_channel': 'mod_log_channel_id',
            'member_log_channel': 'member_log_channel_id',
            'message_log_channel': 'message_log_channel_id',
            'welcome_channel': 'welcome_channel_id',
            'warn_threshold': 'warn_threshold',
            'automod_enabled': 'automod_enabled'
        }
        db_update = {}
        for k, v in payload.items():
            if k in mapping:
                db_update[mapping[k]] = v
        if db_update:
            await DB.update_guild_settings(guild_id, **db_update)

async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigDB(bot))
