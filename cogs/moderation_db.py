import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
from typing import Optional
from utils.database import DB

class ModerationDB(commands.Cog):
    """Drop-in DB persistence for existing moderation commands (warns, actions, settings)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Helpers to persist settings from config commands
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        # Ensure records exist
        await DB.get_guild_settings(guild.id)
        await DB.get_automod_settings(guild.id)

    # Public commands that utilize DB
    @commands.hybrid_command(name="warnings", description="View warnings for a user")
    @app_commands.describe(member="Member to view warnings for")
    @commands.has_permissions(manage_messages=True)
    async def view_warnings(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        member = member or ctx.author
        rows = await DB.get_warnings(ctx.guild.id, member.id)
        if not rows:
            return await ctx.send(embed=discord.Embed(title="📋 Warnings", description=f"{member.mention} has no warnings.", color=discord.Color.green()))
        desc = []
        for r in rows[:10]:
            desc.append(f"• ID `{r['id']}` • <t:{int(__import__('datetime').datetime.fromisoformat(r['created_at']).timestamp())}:R> • by <@{r['moderator_id']}>\nReason: {r['reason'] or 'No reason'}")
        embed = discord.Embed(title=f"📋 Warnings for {member}", description="\n\n".join(desc), color=discord.Color.orange())
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clearwarnings", description="Clear all warnings for a user")
    @app_commands.describe(member="Member to clear warnings for")
    @commands.has_permissions(manage_messages=True)
    async def clear_warnings(self, ctx: commands.Context, member: discord.Member):
        deleted = await DB.clear_warnings(ctx.guild.id, member.id)
        await ctx.send(embed=discord.Embed(title="✅ Cleared Warnings", description=f"Removed {deleted} warning(s) for {member.mention}", color=discord.Color.green()))

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        # Persist key moderation actions if present in context flags (to be set by moderation cog)
        data = getattr(ctx, 'modlog_payload', None)
        if data and isinstance(data, dict):
            await DB.log_mod_action(
                guild_id=ctx.guild.id,
                action=data.get('action', 'unknown'),
                target_id=data.get('target_id', 0),
                moderator_id=ctx.author.id,
                reason=data.get('reason'),
                duration_seconds=data.get('duration_seconds'),
                extra=data.get('extra')
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationDB(bot))
