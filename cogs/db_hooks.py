import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.database import DB

class ConfigPersistHooks(commands.Cog):
    """Hooks for existing config & moderation cogs to set ctx.* payloads for DB cogs."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Patch patterns for existing commands via after_invoke if needed
    # Example helper methods other cogs can import/use:
    @staticmethod
    async def set_config_update(ctx: commands.Context, **kwargs):
        """Attach a config update payload to ctx for config_db cog to persist."""
        current = getattr(ctx, 'config_update', {})
        if not isinstance(current, dict):
            current = {}
        current.update(kwargs)
        setattr(ctx, 'config_update', current)

    @staticmethod
    async def set_modlog_payload(ctx: commands.Context, **kwargs):
        """Attach a moderation action payload to ctx for moderation_db cog to persist."""
        setattr(ctx, 'modlog_payload', kwargs)

async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigPersistHooks(bot))
