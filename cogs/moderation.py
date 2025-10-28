import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
import re
from typing import Optional, Union

class Moderation(commands.Cog):
    """Advanced moderation commands with hybrid support"""
    
    def __init__(self, bot):
        self.bot = bot
        self.muted_users = {}  # guild_id: {user_id: unmute_time}
        self.temp_bans = {}    # guild_id: {user_id: unban_time}
        self.user_warnings = {} # guild_id: {user_id: [warnings]}
        self.check_temp_actions.start()
    
    def cog_unload(self):
        self.check_temp_actions.cancel()
    
    async def cog_check(self, ctx):
        """Check if user has moderation permissions"""
        if ctx.author.guild_permissions.manage_messages or ctx.author.guild_permissions.administrator:
            return True
        
        guild_config = self.bot.guild_configs.get(ctx.guild.id, {})
        mod_role_id = guild_config.get('mod_role')
        if mod_role_id and discord.utils.get(ctx.author.roles, id=mod_role_id):
            return True
        
        raise commands.MissingPermissions(['manage_messages'])
    
    @tasks.loop(minutes=1)
    async def check_temp_actions(self):
        """Check for expired temporary mutes and bans"""
        current_time = datetime.utcnow()
        
        # Check temp mutes
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
        
        # Check temp bans
        for guild_id, banned in list(self.temp_bans.items()):
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            for user_id, unban_time in list(banned.items()):
                if current_time >= unban_time:
                    try:
                        user = await self.bot.fetch_user(user_id)
                        await guild.unban(user, reason="Temporary ban expired")
                        del self.temp_bans[guild_id][user_id]
                    except discord.NotFound:
                        del self.temp_bans[guild_id][user_id]
                    except Exception:
                        pass
    
    @check_temp_actions.before_loop
    async def before_check_temp_actions(self):
        await self.bot.wait_until_ready()
    
    def parse_duration(self, duration_str: str) -> Optional[timedelta]:
        """Parse duration string like '1h', '30m', '1d'"""
        if not duration_str:
            return None
        
        pattern = r'(\d+)([smhd])'
        matches = re.findall(pattern, duration_str.lower())
        
        if not matches:
            return None
        
        total_seconds = 0
        for amount, unit in matches:
            amount = int(amount)
            if unit == 's':
                total_seconds += amount
            elif unit == 'm':
                total_seconds += amount * 60
            elif unit == 'h':
                total_seconds += amount * 3600
            elif unit == 'd':
                total_seconds += amount * 86400
        
        return timedelta(seconds=total_seconds)
    
    async def get_or_create_mute_role(self, guild):
        """Get or create mute role with proper permissions"""
        guild_config = self.bot.guild_configs.get(guild.id, {})
        mute_role_id = guild_config.get('mute_role')
        
        if mute_role_id:
            mute_role = guild.get_role(mute_role_id)
            if mute_role:
                return mute_role
        
        # Create mute role
        mute_role = await guild.create_role(
            name="Muted",
            color=discord.Color.dark_gray(),
            reason="Auto-created mute role"
        )
        
        # Set permissions for all channels
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
                await channel.set_permissions(
                    mute_role,
                    send_messages=False,
                    speak=False,
                    add_reactions=False,
                    reason="Mute role setup"
                )
        
        # Update guild config
        if guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[guild.id] = {}
        self.bot.guild_configs[guild.id]['mute_role'] = mute_role.id
        
        return mute_role
    
    @commands.hybrid_command(name="ban", description="Ban a member from the server")
    @app_commands.describe(
        member="The member to ban",
        duration="Duration for temporary ban (e.g., 1h, 30m, 1d)",
        reason="Reason for the ban",
        delete_messages="Days of messages to delete (0-7)"
    )
    async def ban(self, ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason provided", delete_messages: int = 0):
        """Ban a member with optional temporary duration"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot ban someone with a higher or equal role!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot ban yourself!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        temp_duration = None
        if duration:
            temp_duration = self.parse_duration(duration)
            if not temp_duration:
                embed = discord.Embed(
                    title="❌ Invalid Duration",
                    description="Please use format like: 1h, 30m, 1d, 2h30m",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
        
        # Delete messages validation
        if delete_messages < 0 or delete_messages > 7:
            delete_messages = 0
        
        try:
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title="🔨 You have been banned",
                    description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}",
                    color=discord.Color.red()
                )
                if temp_duration:
                    dm_embed.add_field(name="Duration", value=str(temp_duration), inline=False)
                    dm_embed.add_field(name="Expires", value=f"<t:{int((datetime.utcnow() + temp_duration).timestamp())}:F>", inline=False)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass
            
            # Ban the member
            await member.ban(reason=f"[{ctx.author}] {reason}", delete_message_days=delete_messages)
            
            # Handle temporary ban
            if temp_duration:
                if ctx.guild.id not in self.temp_bans:
                    self.temp_bans[ctx.guild.id] = {}
                self.temp_bans[ctx.guild.id][member.id] = datetime.utcnow() + temp_duration
            
            # Success embed
            embed = discord.Embed(
                title="🔨 Member Banned",
                color=discord.Color.red()
            )
            embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if temp_duration:
                embed.add_field(name="Duration", value=str(temp_duration), inline=True)
                embed.add_field(name="Expires", value=f"<t:{int((datetime.utcnow() + temp_duration).timestamp())}:F>", inline=True)
            
            if delete_messages > 0:
                embed.add_field(name="Messages Deleted", value=f"{delete_messages} days", inline=True)
            
            embed.timestamp = datetime.utcnow()
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to ban this member!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to ban member: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user="User ID or username#discriminator to unban",
        reason="Reason for the unban"
    )
    async def unban(self, ctx, user: str, *, reason: str = "No reason provided"):
        """Unban a user from the server"""
        try:
            # Try to parse as user ID first
            if user.isdigit():
                user_obj = await self.bot.fetch_user(int(user))
            else:
                # Try to find by name#discriminator
                banned_users = [entry async for entry in ctx.guild.bans()]
                user_obj = None
                for ban_entry in banned_users:
                    if str(ban_entry.user) == user or ban_entry.user.name == user:
                        user_obj = ban_entry.user
                        break
                
                if not user_obj:
                    embed = discord.Embed(
                        title="❌ User Not Found",
                        description="Could not find a banned user with that name or ID.",
                        color=discord.Color.red()
                    )
                    return await ctx.send(embed=embed)
            
            await ctx.guild.unban(user_obj, reason=f"[{ctx.author}] {reason}")
            
            # Remove from temp bans if exists
            if ctx.guild.id in self.temp_bans and user_obj.id in self.temp_bans[ctx.guild.id]:
                del self.temp_bans[ctx.guild.id][user_obj.id]
            
            embed = discord.Embed(
                title="✅ Member Unbanned",
                color=discord.Color.green()
            )
            embed.add_field(name="User", value=f"{user_obj} ({user_obj.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            
            await ctx.send(embed=embed)
            
        except discord.NotFound:
            embed = discord.Embed(
                title="❌ User Not Banned",
                description="This user is not banned from the server.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to unban user: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="kick", description="Kick a member from the server")
    @app_commands.describe(
        member="The member to kick",
        reason="Reason for the kick"
    )
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot kick someone with a higher or equal role!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot kick yourself!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        try:
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title="👢 You have been kicked",
                    description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}",
                    color=discord.Color.orange()
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass
            
            await member.kick(reason=f"[{ctx.author}] {reason}")
            
            embed = discord.Embed(
                title="👢 Member Kicked",
                color=discord.Color.orange()
            )
            embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to kick this member!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to kick member: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="mute", description="Mute a member")
    @app_commands.describe(
        member="The member to mute",
        duration="Duration of the mute (e.g., 1h, 30m, 1d)",
        reason="Reason for the mute"
    )
    async def mute(self, ctx, member: discord.Member, duration: str = "1h", *, reason: str = "No reason provided"):
        """Mute a member with optional duration"""
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot mute someone with a higher or equal role!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot mute yourself!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        mute_duration = self.parse_duration(duration)
        if not mute_duration:
            embed = discord.Embed(
                title="❌ Invalid Duration",
                description="Please use format like: 1h, 30m, 1d, 2h30m",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        try:
            mute_role = await self.get_or_create_mute_role(ctx.guild)
            
            if mute_role in member.roles:
                embed = discord.Embed(
                    title="❌ Already Muted",
                    description="This member is already muted!",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
            
            await member.add_roles(mute_role, reason=f"[{ctx.author}] {reason}")
            
            # Add to muted users tracking
            if ctx.guild.id not in self.muted_users:
                self.muted_users[ctx.guild.id] = {}
            self.muted_users[ctx.guild.id][member.id] = datetime.utcnow() + mute_duration
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title="🔇 You have been muted",
                    description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}\n**Duration:** {mute_duration}",
                    color=discord.Color.dark_gray()
                )
                dm_embed.add_field(name="Expires", value=f"<t:{int((datetime.utcnow() + mute_duration).timestamp())}:F>", inline=False)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass
            
            embed = discord.Embed(
                title="🔇 Member Muted",
                color=discord.Color.dark_gray()
            )
            embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Duration", value=str(mute_duration), inline=True)
            embed.add_field(name="Expires", value=f"<t:{int((datetime.utcnow() + mute_duration).timestamp())}:F>", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to mute this member!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to mute member: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unmute", description="Unmute a member")
    @app_commands.describe(
        member="The member to unmute",
        reason="Reason for the unmute"
    )
    async def unmute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Unmute a member"""
        guild_config = self.bot.guild_configs.get(ctx.guild.id, {})
        mute_role_id = guild_config.get('mute_role')
        
        if not mute_role_id:
            embed = discord.Embed(
                title="❌ No Mute Role",
                description="No mute role has been set up for this server.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role or mute_role not in member.roles:
            embed = discord.Embed(
                title="❌ Not Muted",
                description="This member is not muted!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        try:
            await member.remove_roles(mute_role, reason=f"[{ctx.author}] {reason}")
            
            # Remove from muted users tracking
            if ctx.guild.id in self.muted_users and member.id in self.muted_users[ctx.guild.id]:
                del self.muted_users[ctx.guild.id][member.id]
            
            embed = discord.Embed(
                title="🔊 Member Unmuted",
                color=discord.Color.green()
            )
            embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to unmute this member!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to unmute member: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="warn", description="Warn a member")
    @app_commands.describe(
        member="The member to warn",
        reason="Reason for the warning"
    )
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member"""
        if member == ctx.author:
            embed = discord.Embed(
                title="❌ Error",
                description="You cannot warn yourself!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Initialize warnings if not exists
        if ctx.guild.id not in self.user_warnings:
            self.user_warnings[ctx.guild.id] = {}
        if member.id not in self.user_warnings[ctx.guild.id]:
            self.user_warnings[ctx.guild.id][member.id] = []
        
        # Add warning
        warning_data = {
            'reason': reason,
            'moderator': ctx.author.id,
            'timestamp': datetime.utcnow().isoformat(),
            'id': len(self.user_warnings[ctx.guild.id][member.id]) + 1
        }
        self.user_warnings[ctx.guild.id][member.id].append(warning_data)
        
        warning_count = len(self.user_warnings[ctx.guild.id][member.id])
        
        # Try to DM the user
        try:
            dm_embed = discord.Embed(
                title="⚠️ You have been warned",
                description=f"**Server:** {ctx.guild.name}\n**Reason:** {reason}\n**Warning #{warning_count}**",
                color=discord.Color.yellow()
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass
        
        embed = discord.Embed(
            title="⚠️ Member Warned",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Warning Count", value=f"{warning_count}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.timestamp = datetime.utcnow()
        
        # Check for automatic actions based on warning count
        guild_config = self.bot.guild_configs.get(ctx.guild.id, {})
        warn_threshold = guild_config.get('warn_threshold', 3)
        
        if warning_count >= warn_threshold:
            embed.add_field(
                name="⚠️ Warning Threshold Reached",
                value=f"This member has reached {warning_count} warnings!",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="warnings", description="View warnings for a member")
    @app_commands.describe(
        member="The member to view warnings for (leave empty for yourself)"
    )
    async def warnings(self, ctx, member: discord.Member = None):
        """View warnings for a member"""
        if not member:
            member = ctx.author
        
        if ctx.guild.id not in self.user_warnings or member.id not in self.user_warnings[ctx.guild.id]:
            embed = discord.Embed(
                title="📋 No Warnings",
                description=f"{member.mention} has no warnings.",
                color=discord.Color.green()
            )
            return await ctx.send(embed=embed)
        
        warnings = self.user_warnings[ctx.guild.id][member.id]
        
        embed = discord.Embed(
            title=f"📋 Warnings for {member.display_name}",
            description=f"Total warnings: **{len(warnings)}**",
            color=discord.Color.yellow()
        )
        
        for i, warning in enumerate(warnings[-10:], 1):  # Show last 10 warnings
            moderator = self.bot.get_user(warning['moderator'])
            mod_name = moderator.mention if moderator else f"<@{warning['moderator']}>"
            timestamp = datetime.fromisoformat(warning['timestamp'])
            
            embed.add_field(
                name=f"Warning #{warning['id']}",
                value=f"**Reason:** {warning['reason']}\n**Moderator:** {mod_name}\n**Date:** <t:{int(timestamp.timestamp())}:f>",
                inline=False
            )
        
        if len(warnings) > 10:
            embed.set_footer(text=f"Showing last 10 of {len(warnings)} warnings")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="clearwarns", description="Clear warnings for a member")
    @app_commands.describe(
        member="The member to clear warnings for",
        amount="Number of warnings to clear (leave empty to clear all)"
    )
    @commands.has_permissions(administrator=True)
    async def clearwarns(self, ctx, member: discord.Member, amount: int = None):
        """Clear warnings for a member"""
        if ctx.guild.id not in self.user_warnings or member.id not in self.user_warnings[ctx.guild.id]:
            embed = discord.Embed(
                title="❌ No Warnings",
                description=f"{member.mention} has no warnings to clear.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        warnings = self.user_warnings[ctx.guild.id][member.id]
        original_count = len(warnings)
        
        if amount is None:
            # Clear all warnings
            self.user_warnings[ctx.guild.id][member.id] = []
            cleared_count = original_count
        else:
            # Clear specific amount (from the end)
            amount = min(amount, original_count)
            self.user_warnings[ctx.guild.id][member.id] = warnings[:-amount] if amount > 0 else warnings
            cleared_count = amount
        
        embed = discord.Embed(
            title="✅ Warnings Cleared",
            description=f"Cleared **{cleared_count}** warning(s) for {member.mention}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Remaining Warnings", value=len(self.user_warnings[ctx.guild.id][member.id]), inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="purge", description="Delete multiple messages")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        member="Only delete messages from this member"
    )
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        """Delete multiple messages"""
        if amount < 1 or amount > 100:
            embed = discord.Embed(
                title="❌ Invalid Amount",
                description="Please provide a number between 1 and 100.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        def check(m):
            if member:
                return m.author == member
            return True
        
        try:
            deleted = await ctx.channel.purge(limit=amount, check=check)
            
            embed = discord.Embed(
                title="🗑️ Messages Deleted",
                description=f"Successfully deleted **{len(deleted)}** message(s).",
                color=discord.Color.green()
            )
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)
            
            if member:
                embed.add_field(name="Target User", value=member.mention, inline=True)
            
            embed.timestamp = datetime.utcnow()
            
            # Send confirmation message that deletes itself
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to delete messages: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="slowmode", description="Set channel slowmode")
    @app_commands.describe(
        seconds="Slowmode duration in seconds (0 to disable, max 21600)",
        channel="Channel to set slowmode for (current channel if not specified)"
    )
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int, channel: discord.TextChannel = None):
        """Set slowmode for a channel"""
        if not channel:
            channel = ctx.channel
        
        if seconds < 0 or seconds > 21600:  # Discord's max slowmode is 6 hours
            embed = discord.Embed(
                title="❌ Invalid Duration",
                description="Slowmode must be between 0 and 21600 seconds (6 hours).",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        try:
            await channel.edit(slowmode_delay=seconds)
            
            if seconds == 0:
                embed = discord.Embed(
                    title="✅ Slowmode Disabled",
                    description=f"Disabled slowmode for {channel.mention}.",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="⏱️ Slowmode Enabled",
                    description=f"Set slowmode to **{seconds}** seconds for {channel.mention}.",
                    color=discord.Color.blue()
                )
            
            embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
            embed.timestamp = datetime.utcnow()
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to edit this channel!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to set slowmode: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))