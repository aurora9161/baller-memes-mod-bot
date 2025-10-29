import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.database import DB

class AutomodDB(commands.Cog):
    """Persist /automod settings and serve from DB for automod cog."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Nothing to pre-load globally; automod cog should read from DB when needed.
        pass

    @commands.hybrid_command(name="automod_set", description="Persist AutoMod setting to database")
    @app_commands.describe(setting="Setting key", value="Value to set (true/false/number)")
    @commands.has_permissions(administrator=True)
    async def automod_set(self, ctx: commands.Context, setting: str, value: str):
        valid = {
            'spam_detection': bool,
            'auto_delete_invites': bool,
            'profanity_filter': bool,
            'link_filter': bool,
            'caps_filter': bool,
            'repeated_text_filter': bool,
            'auto_dehoist': bool,
            'raid_protection': bool,
            'max_mentions': int,
            'max_emoji': int
        }
        if setting not in valid:
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Setting", description=f"Valid: {', '.join(valid.keys())}", color=discord.Color.red()))
        try:
            if valid[setting] == bool:
                parsed = value.lower() in ("true","1","yes","on","enable")
                parsed = 1 if parsed else 0
            else:
                parsed = int(value)
                if parsed < 0:
                    raise ValueError("Value must be positive")
        except Exception as e:
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Value", description=str(e), color=discord.Color.red()))
        await DB.update_automod_settings(ctx.guild.id, **{setting: parsed})
        await ctx.send(embed=discord.Embed(title="✅ AutoMod Updated", description=f"{setting} = {value}", color=discord.Color.green()))

async def setup(bot: commands.Bot):
    await bot.add_cog(AutomodDB(bot))
