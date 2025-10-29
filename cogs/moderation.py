import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
import re
from typing import Optional, Union
from cogs.db_hooks import ConfigPersistHooks
from utils.database import DB

class Moderation(commands.Cog):
    """Advanced moderation commands with hybrid support (DB persisted)"""
    
    def __init__(self, bot):
        self.bot = bot
        self.muted_users = {}  # guild_id: {user_id: unmute_time}
        self.temp_bans = {}    # guild_id: {user_id: unban_time}
        self.user_warnings = {} # in-memory for quick view; persisted in DB
        self.check_temp_actions.start()
    
    def cog_unload(self):
        self.check_temp_actions.cancel()
    
    async def cog_check(self, ctx):
        if ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.administrator:
            return True
        guild_config = self.bot.guild_configs.get(ctx.guild.id, {})
        mod_role_id = guild_config.get('mod_role')
        if mod_role_id and discord.utils.get(ctx.author.roles, id=mod_role_id):
            return True
        raise commands.MissingPermissions(['manage_messages'])
    
    @tasks.loop(minutes=1)
    async def check_temp_actions(self):
        current_time = datetime.utcnow()
        # temp mutes
        for guild_id, muted in list(self.muted_users.items()):
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            for user_id, unmute_time in list(muted.items()):
                if current_time >= unmute_time:
                    member = guild.get_member(user_id)
                    if member:
                        guild_config = self.bot.guild_configs.get(guild_id, {})
                        mute_role_id = guild_config.get('mute_role')
                        if mute_role_id:
                            mute_role = guild.get_role(mute_role_id)
                            if mute_role and mute_role in member.roles:
                                await member.remove_roles(mute_role, reason="Temporary mute expired")
                    del self.muted_users[guild_id][user_id]
        # temp bans
        for guild_id, banned in list(self.temp_bans.items()):
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            for user_id, unban_time in list(banned.items()):
                if current_time >= unban_time:
                    try:
                        user = await self.bot.fetch_user(user_id)
                        await guild.unban(user, reason="Temporary ban expired")
                    except discord.NotFound:
                        pass
                    finally:
                        if user_id in self.temp_bans.get(guild_id, {}):
                            del self.temp_bans[guild_id][user_id]
    
    @check_temp_actions.before_loop
    async def before_check_temp_actions(self):
        await self.bot.wait_until_ready()
    
    def parse_duration(self, duration_str: str) -> Optional[timedelta]:
        if not duration_str:
            return None
        pattern = r'(\d+)([smhd])'
        matches = re.findall(pattern, duration_str.lower())
        if not matches:
            return None
        total_seconds = 0
        for amount, unit in matches:
            amount = int(amount)
            total_seconds += amount * ({'s':1,'m':60,'h':3600,'d':86400}[unit])
        return timedelta(seconds=total_seconds)
    
    async def get_or_create_mute_role(self, guild):
        guild_config = self.bot.guild_configs.get(guild.id, {})
        mute_role_id = guild_config.get('mute_role')
        if mute_role_id:
            mute_role = guild.get_role(mute_role_id)
            if mute_role:
                return mute_role
        mute_role = await guild.create_role(name="Muted", color=discord.Color.dark_gray(), reason="Auto-created mute role")
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
                await channel.set_permissions(mute_role, send_messages=False, speak=False, add_reactions=False, reason="Mute role setup")
        if guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[guild.id] = {}
        self.bot.guild_configs[guild.id]['mute_role'] = mute_role.id
        await ConfigPersistHooks.set_config_update(type('obj', (), {'__dict__': {'guild': guild}}), mute_role=mute_role.id)  # no ctx here; best effort
        return mute_role
    
    @commands.hybrid_command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban", duration="Duration (e.g., 1h, 30m, 1d)", reason="Reason", delete_messages="Days of messages to delete (0-7)")
    async def ban(self, ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason provided", delete_messages: int = 0):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(embed=discord.Embed(title="❌ Error", description="You cannot ban someone with a higher or equal role!", color=discord.Color.red()))
        if member == ctx.author:
            return await ctx.send(embed=discord.Embed(title="❌ Error", description="You cannot ban yourself!", color=discord.Color.red()))
        temp_duration = self.parse_duration(duration) if duration else None
        if duration and not temp_duration:
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Duration", description="Use formats like 1h, 30m, 1d, 2h30m", color=discord.Color.red()))
        delete_messages = delete_messages if 0 <= delete_messages <= 7 else 0
        try:
            try:
                dm = discord.Embed(title="🔨 You have been banned", description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}", color=discord.Color.red())
                if temp_duration:
                    dm.add_field(name="Duration", value=str(temp_duration), inline=False)
                    dm.add_field(name="Expires", value=f"<t:{int((datetime.utcnow()+temp_duration).timestamp())}:F>", inline=False)
                await member.send(embed=dm)
            except discord.Forbidden:
                pass
            await member.ban(reason=f"[{ctx.author}] {reason}", delete_message_days=delete_messages)
            if temp_duration:
                self.temp_bans.setdefault(ctx.guild.id, {})[member.id] = datetime.utcnow() + temp_duration
            await ConfigPersistHooks.set_modlog_payload(ctx, action="ban", target_id=member.id, reason=reason, duration_seconds=(temp_duration.total_seconds() if temp_duration else None), extra=json.dumps({"delete_messages_days": delete_messages}))
            embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
            embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            if temp_duration:
                embed.add_field(name="Duration", value=str(temp_duration), inline=True)
                embed.add_field(name="Expires", value=f"<t:{int((datetime.utcnow()+temp_duration).timestamp())}:F>", inline=True)
            if delete_messages:
                embed.add_field(name="Messages Deleted", value=f"{delete_messages} days", inline=True)
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Permission Error", description="I don't have permission to ban this member!", color=discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="❌ Error", description=f"Failed to ban member: {str(e)}", color=discord.Color.red()))
    
    @commands.hybrid_command(name="unban", description="Unban a user from the server")
    @app_commands.describe(user="User ID or username#discriminator to unban", reason="Reason for the unban")
    async def unban(self, ctx, user: str, *, reason: str = "No reason provided"):
        try:
            if user.isdigit():
                user_obj = await self.bot.fetch_user(int(user))
            else:
                banned_users = [entry async for entry in ctx.guild.bans()]
                user_obj = next((be.user for be in banned_users if str(be.user) == user or be.user.name == user), None)
                if not user_obj:
                    return await ctx.send(embed=discord.Embed(title="❌ User Not Found", description="No banned user matched.", color=discord.Color.red()))
            await ctx.guild.unban(user_obj, reason=f"[{ctx.author}] {reason}")
            if ctx.guild.id in self.temp_bans and user_obj.id in self.temp_bans[ctx.guild.id]:
                del self.temp_bans[ctx.guild.id][user_obj.id]
            await ConfigPersistHooks.set_modlog_payload(ctx, action="unban", target_id=user_obj.id, reason=reason)
            embed = discord.Embed(title="✅ Member Unbanned", color=discord.Color.green())
            embed.add_field(name="User", value=f"{user_obj} ({user_obj.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(title="❌ User Not Banned", description="This user is not banned.", color=discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="❌ Error", description=f"Failed to unban user: {str(e)}", color=discord.Color.red()))
    
    @commands.hybrid_command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(embed=discord.Embed(title="❌ Error", description="You cannot kick someone with a higher or equal role!", color=discord.Color.red()))
        if member == ctx.author:
            return await ctx.send(embed=discord.Embed(title="❌ Error", description="You cannot kick yourself!", color=discord.Color.red()))
        try:
            try:
                await member.send(embed=discord.Embed(title="👢 You have been kicked", description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}", color=discord.Color.orange()))
            except discord.Forbidden:
                pass
            await member.kick(reason=f"[{ctx.author}] {reason}")
            await ConfigPersistHooks.set_modlog_payload(ctx, action="kick", target_id=member.id, reason=reason)
            embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange())
            embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Permission Error", description="I don't have permission to kick this member!", color=discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="❌ Error", description=f"Failed to kick member: {str(e)}", color=discord.Color.red()))
    
    @commands.hybrid_command(name="mute", description="Mute a member")
    @app_commands.describe(member="The member to mute", duration="Duration of the mute (e.g., 1h, 30m, 1d)", reason="Reason for the mute")
    async def mute(self, ctx, member: discord.Member, duration: str = "1h", *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(embed=discord.Embed(title="❌ Error", description="You cannot mute someone with a higher or equal role!", color=discord.Color.red()))
        if member == ctx.author:
            return await ctx.send(embed=discord.Embed(title="❌ Error", description="You cannot mute yourself!", color=discord.Color.red()))
        mute_duration = self.parse_duration(duration)
        if not mute_duration:
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Duration", description="Use formats like 1h, 30m, 1d, 2h30m", color=discord.Color.red()))
        try:
            mute_role = await self.get_or_create_mute_role(ctx.guild)
            if mute_role in member.roles:
                return await ctx.send(embed=discord.Embed(title="❌ Already Muted", description="This member is already muted!", color=discord.Color.red()))
            await member.add_roles(mute_role, reason=f"[{ctx.author}] {reason}")
            self.muted_users.setdefault(ctx.guild.id, {})[member.id] = datetime.utcnow() + mute_duration
            try:
                dm = discord.Embed(title="🔇 You have been muted", description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}\n**Duration:** {mute_duration}", color=discord.Color.dark_gray())
                dm.add_field(name="Expires", value=f"<t:{int((datetime.utcnow()+mute_duration).timestamp())}:F>", inline=False)
                await member.send(embed=dm)
            except discord.Forbidden:
                pass
            await ConfigPersistHooks.set_modlog_payload(ctx, action="mute", target_id=member.id, reason=reason, duration_seconds=mute_duration.total_seconds())
            embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.dark_gray())
            embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Duration", value=str(mute_duration), inline=True)
            embed.add_field(name="Expires", value=f"<t:{int((datetime.utcnow()+mute_duration).timestamp())}:F>", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Permission Error", description="I don't have permission to mute this member!", color=discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="❌ Error", description=f"Failed to mute member: {str(e)}", color=discord.Color.red()))
    
    @commands.hybrid_command(name="unmute", description="Unmute a member")
    @app_commands.describe(member="The member to unmute", reason="Reason for the unmute")
    async def unmute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        guild_config = self.bot.guild_configs.get(ctx.guild.id, {})
        mute_role_id = guild_config.get('mute_role')
        if not mute_role_id:
            return await ctx.send(embed=discord.Embed(title="❌ No Mute Role", description="No mute role has been set up for this server.", color=discord.Color.red()))
        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role or mute_role not in member.roles:
            return await ctx.send(embed=discord.Embed(title="❌ Not Muted", description="This member is not muted!", color=discord.Color.red()))
        try:
            await member.remove_roles(mute_role, reason=f"[{ctx.author}] {reason}")
            if ctx.guild.id in self.muted_users and member.id in self.muted_users[ctx.guild.id]:
                del self.muted_users[ctx.guild.id][member.id]
            await ConfigPersistHooks.set_modlog_payload(ctx, action="unmute", target_id=member.id, reason=reason)
            embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green())
            embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Permission Error", description="I don't have permission to unmute this member!", color=discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="❌ Error", description=f"Failed to unmute member: {str(e)}", color=discord.Color.red()))
    
    @commands.hybrid_command(name="warn", description="Warn a member")
    @app_commands.describe(member="The member to warn", reason="Reason for the warning")
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member == ctx.author:
            return await ctx.send(embed=discord.Embed(title="❌ Error", description="You cannot warn yourself!", color=discord.Color.red()))
        warning_id = await DB.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        await ConfigPersistHooks.set_modlog_payload(ctx, action="warn", target_id=member.id, reason=reason, extra=json.dumps({"warning_id": warning_id}))
        try:
            await member.send(embed=discord.Embed(title="⚠️ You have been warned", description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}", color=discord.Color.yellow()))
        except discord.Forbidden:
            pass
        rows = await DB.get_warnings(ctx.guild.id, member.id)
        embed = discord.Embed(title="⚠️ Member Warned", color=discord.Color.yellow())
        embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Warning Count", value=f"{len(rows)}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        warn_threshold = self.bot.guild_configs.get(ctx.guild.id, {}).get('warn_threshold', 3)
        if len(rows) >= warn_threshold:
            embed.add_field(name="⚠️ Warning Threshold Reached", value=f"This member has reached {len(rows)} warnings!", inline=False)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="clearwarns", description="Clear warnings for a member")
    @app_commands.describe(member="The member to clear warnings for", amount="Number of warnings to clear (leave empty to clear all)")
    @commands.has_permissions(administrator=True)
    async def clearwarns(self, ctx, member: discord.Member, amount: int = None):
        rows = await DB.get_warnings(ctx.guild.id, member.id)
        if not rows:
            return await ctx.send(embed=discord.Embed(title="❌ No Warnings", description=f"{member.mention} has no warnings to clear.", color=discord.Color.red()))
        if amount is None:
            deleted = await DB.clear_warnings(ctx.guild.id, member.id)
        else:
            # Partial clear: delete newest N by id
            ids = [r['id'] for r in rows][:amount]
            deleted = 0
            async with (await DB.connect()) as conn:
                for wid in ids:
                    cur = await conn.execute("DELETE FROM warnings WHERE id=?", (wid,))
                    deleted += cur.rowcount
                await conn.commit()
        await ConfigPersistHooks.set_modlog_payload(ctx, action="clearwarns", target_id=member.id, reason=f"Cleared {deleted} warnings")
        remaining = await DB.get_warnings(ctx.guild.id, member.id)
        embed = discord.Embed(title="✅ Warnings Cleared", description=f"Removed {deleted} warning(s) for {member.mention}", color=discord.Color.green())
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Remaining Warnings", value=len(remaining), inline=True)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="purge", description="Delete multiple messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)", member="Only delete messages from this member")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        if amount < 1 or amount > 100:
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Amount", description="Provide 1-100.", color=discord.Color.red()))
        def check(m):
            return (m.author == member) if member else True
        try:
            deleted = await ctx.channel.purge(limit=amount, check=check)
            await ConfigPersistHooks.set_modlog_payload(ctx, action="purge", target_id=(member.id if member else 0), reason=f"Deleted {len(deleted)} messages", extra=json.dumps({"channel_id": ctx.channel.id}))
            embed = discord.Embed(title="🗑️ Messages Deleted", description=f"Successfully deleted **{len(deleted)}** message(s).", color=discord.Color.green())
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
            if member:
                embed.add_field(name="Target User", value=member.mention, inline=True)
            embed.timestamp = datetime.utcnow()
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            try:
                await msg.delete()
            except discord.NotFound:
                pass
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Permission Error", description="I don't have permission to delete messages!", color=discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="❌ Error", description=f"Failed to delete messages: {str(e)}", color=discord.Color.red()))
    
    @commands.hybrid_command(name="slowmode", description="Set channel slowmode")
    @app_commands.describe(seconds="Slowmode duration in seconds (0-21600)", channel="Channel to set slowmode for (current if not specified)")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        if seconds < 0 or seconds > 21600:
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Duration", description="Slowmode must be between 0 and 21600 seconds.", color=discord.Color.red()))
        try:
            await channel.edit(slowmode_delay=seconds)
            embed = discord.Embed(title=("✅ Slowmode Disabled" if seconds==0 else "⏱️ Slowmode Enabled"), description=(f"Disabled slowmode for {channel.mention}." if seconds==0 else f"Set slowmode to **{seconds}** seconds for {channel.mention}."), color=(discord.Color.green() if seconds==0 else discord.Color.blue()))
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(title="❌ Permission Error", description="I don't have permission to edit this channel!", color=discord.Color.red()))
        except Exception as e:
            await ctx.send(embed=discord.Embed(title="❌ Error", description=f"Failed to set slowmode: {str(e)}", color=discord.Color.red()))

async def setup(bot):
    await bot.add_cog(Moderation(bot))
