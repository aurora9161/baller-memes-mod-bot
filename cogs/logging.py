import discord
from discord.ext import commands
from datetime import datetime
import asyncio

class Logging(commands.Cog):
    """Comprehensive logging system for moderation actions and server events"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def get_log_channel(self, guild, log_type="general"):
        """Get the appropriate log channel for the guild"""
        guild_config = self.bot.guild_configs.get(guild.id, {})
        
        # Try specific log channel first, then general log channel
        log_channels = {
            "mod": guild_config.get('mod_log_channel'),
            "member": guild_config.get('member_log_channel'),
            "message": guild_config.get('message_log_channel'),
            "general": guild_config.get('log_channel')
        }
        
        channel_id = log_channels.get(log_type) or log_channels.get('general')
        if channel_id:
            return guild.get_channel(channel_id)
        return None
    
    async def log_action(self, guild, embed, log_type="general"):
        """Send log embed to appropriate channel"""
        log_channel = self.get_log_channel(guild, log_type)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log member joins"""
        embed = discord.Embed(
            title="📥 Member Joined",
            color=discord.Color.green()
        )
        embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=str(member.guild.member_count), inline=True)
        
        # Check account age
        account_age = datetime.utcnow() - member.created_at
        if account_age.days < 7:
            embed.add_field(name="⚠️ New Account", value=f"Account is {account_age.days} days old", inline=False)
            embed.color = discord.Color.orange()
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await self.log_action(member.guild, embed, "member")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log member leaves"""
        embed = discord.Embed(
            title="📤 Member Left",
            color=discord.Color.red()
        )
        embed.add_field(name="Member", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Member Count", value=str(member.guild.member_count), inline=True)
        
        # Check if they had roles
        if len(member.roles) > 1:  # More than @everyone
            roles = [role.mention for role in member.roles[1:]][:10]  # Limit to 10 roles
            embed.add_field(name="Roles", value=" ".join(roles), inline=False)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await self.log_action(member.guild, embed, "member")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log member updates (nickname, roles, etc.)"""
        if before.nick != after.nick:
            embed = discord.Embed(
                title="✏️ Nickname Changed",
                color=discord.Color.blue()
            )
            embed.add_field(name="Member", value=f"{after} ({after.id})", inline=True)
            embed.add_field(name="Before", value=before.nick or "None", inline=True)
            embed.add_field(name="After", value=after.nick or "None", inline=True)
            embed.timestamp = datetime.utcnow()
            
            await self.log_action(after.guild, embed, "member")
        
        # Check role changes
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title="🎭 Roles Updated",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Member", value=f"{after} ({after.id})", inline=False)
                
                if added_roles:
                    embed.add_field(name="➕ Added Roles", value=" ".join([role.mention for role in added_roles]), inline=False)
                
                if removed_roles:
                    embed.add_field(name="➖ Removed Roles", value=" ".join([role.mention for role in removed_roles]), inline=False)
                
                embed.timestamp = datetime.utcnow()
                await self.log_action(after.guild, embed, "member")
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log message deletions"""
        if message.author.bot or not message.guild:
            return
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.red()
        )
        embed.add_field(name="Author", value=f"{message.author} ({message.author.id})", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Message ID", value=str(message.id), inline=True)
        
        # Content (truncated if too long)
        content = message.content[:1000] if message.content else "*No text content*"
        if message.attachments:
            content += f"\n\n**Attachments:** {len(message.attachments)}"
        
        embed.add_field(name="Content", value=f"```{content}```", inline=False)
        embed.timestamp = datetime.utcnow()
        
        await self.log_action(message.guild, embed, "message")
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log message edits"""
        if before.author.bot or not before.guild or before.content == after.content:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.orange()
        )
        embed.add_field(name="Author", value=f"{after.author} ({after.author.id})", inline=True)
        embed.add_field(name="Channel", value=after.channel.mention, inline=True)
        embed.add_field(name="Message ID", value=str(after.id), inline=True)
        
        # Before content
        before_content = before.content[:500] if before.content else "*No text content*"
        embed.add_field(name="Before", value=f"```{before_content}```", inline=False)
        
        # After content
        after_content = after.content[:500] if after.content else "*No text content*"
        embed.add_field(name="After", value=f"```{after_content}```", inline=False)
        
        embed.add_field(name="Jump to Message", value=f"[Click here]({after.jump_url})", inline=False)
        embed.timestamp = datetime.utcnow()
        
        await self.log_action(after.guild, embed, "message")
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log channel creation"""
        embed = discord.Embed(
            title="📝 Channel Created",
            color=discord.Color.green()
        )
        embed.add_field(name="Channel", value=f"{channel.mention} ({channel.id})", inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace('_', ' ').title(), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.timestamp = datetime.utcnow()
        
        await self.log_action(channel.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log channel deletion"""
        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            color=discord.Color.red()
        )
        embed.add_field(name="Channel", value=f"#{channel.name} ({channel.id})", inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace('_', ' ').title(), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.timestamp = datetime.utcnow()
        
        await self.log_action(channel.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Log role creation"""
        embed = discord.Embed(
            title="🎭 Role Created",
            color=discord.Color.green()
        )
        embed.add_field(name="Role", value=f"{role.mention} ({role.id})", inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.timestamp = datetime.utcnow()
        
        await self.log_action(role.guild, embed)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Log role deletion"""
        embed = discord.Embed(
            title="🗑️ Role Deleted",
            color=discord.Color.red()
        )
        embed.add_field(name="Role", value=f"{role.name} ({role.id})", inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Members", value=str(len(role.members)), inline=True)
        embed.timestamp = datetime.utcnow()
        
        await self.log_action(role.guild, embed)
    
    @commands.hybrid_command(name="logs", description="View recent logs")
    @commands.has_permissions(manage_messages=True)
    async def view_logs(self, ctx, log_type: str = "all", amount: int = 10):
        """View recent server logs"""
        if amount < 1 or amount > 50:
            amount = 10
        
        valid_types = ["mod", "member", "message", "all"]
        if log_type not in valid_types:
            embed = discord.Embed(
                title="❌ Invalid Log Type",
                description=f"Valid types: {', '.join(valid_types)}",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Get appropriate log channel
        if log_type == "all":
            log_channel = self.get_log_channel(ctx.guild, "general")
        else:
            log_channel = self.get_log_channel(ctx.guild, log_type)
        
        if not log_channel:
            embed = discord.Embed(
                title="❌ No Log Channel",
                description=f"No log channel configured for type: {log_type}",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        try:
            messages = [message async for message in log_channel.history(limit=amount)]
            
            if not messages:
                embed = discord.Embed(
                    title="📝 No Logs Found",
                    description=f"No recent logs in {log_channel.mention}",
                    color=discord.Color.orange()
                )
                return await ctx.send(embed=embed)
            
            embed = discord.Embed(
                title=f"📋 Recent {log_type.title()} Logs",
                description=f"Showing last {len(messages)} logs from {log_channel.mention}",
                color=discord.Color.blue()
            )
            
            for i, message in enumerate(reversed(messages[-10:]), 1):  # Show last 10
                if message.embeds:
                    log_embed = message.embeds[0]
                    embed.add_field(
                        name=f"{i}. {log_embed.title or 'Log Entry'}",
                        value=f"<t:{int(message.created_at.timestamp())}:R>",
                        inline=True
                    )
            
            embed.add_field(
                name="View Full Logs", 
                value=f"Check {log_channel.mention} for complete log history", 
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="Cannot access log channel!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))