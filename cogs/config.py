import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime
import asyncio

class Configuration(commands.Cog):
    """Server configuration and setup commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_group(name="config", description="Server configuration commands")
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        """Base configuration command group"""
        if ctx.invoked_subcommand is None:
            await self.show_config(ctx)
    
    async def show_config(self, ctx):
        """Show current server configuration"""
        guild_config = self.bot.guild_configs.get(ctx.guild.id, {})
        
        embed = discord.Embed(
            title=f"⚙️ Configuration for {ctx.guild.name}",
            color=discord.Color.blue()
        )
        
        # Basic settings
        embed.add_field(
            name="Basic Settings",
            value=f"**Prefix:** `{guild_config.get('prefix', self.bot.config.get('default_prefix', '!'))}\n**Warn Threshold:** {guild_config.get('warn_threshold', 3)}",
            inline=False
        )
        
        # Roles
        mod_role = ctx.guild.get_role(guild_config.get('mod_role')) if guild_config.get('mod_role') else None
        admin_role = ctx.guild.get_role(guild_config.get('admin_role')) if guild_config.get('admin_role') else None
        mute_role = ctx.guild.get_role(guild_config.get('mute_role')) if guild_config.get('mute_role') else None
        
        embed.add_field(
            name="Roles",
            value=f"**Moderator:** {mod_role.mention if mod_role else 'Not set'}\n**Admin:** {admin_role.mention if admin_role else 'Not set'}\n**Mute:** {mute_role.mention if mute_role else 'Auto-created'}",
            inline=True
        )
        
        # Channels
        log_channel = ctx.guild.get_channel(guild_config.get('log_channel')) if guild_config.get('log_channel') else None
        mod_log_channel = ctx.guild.get_channel(guild_config.get('mod_log_channel')) if guild_config.get('mod_log_channel') else None
        welcome_channel = ctx.guild.get_channel(guild_config.get('welcome_channel')) if guild_config.get('welcome_channel') else None
        
        embed.add_field(
            name="Channels",
            value=f"**General Log:** {log_channel.mention if log_channel else 'Not set'}\n**Mod Log:** {mod_log_channel.mention if mod_log_channel else 'Not set'}\n**Welcome:** {welcome_channel.mention if welcome_channel else 'Not set'}",
            inline=True
        )
        
        # AutoMod status
        automod_config = self.bot.config.get('moderation', {})
        automod_status = {
            'Spam Detection': automod_config.get('spam_detection', True),
            'Invite Filter': automod_config.get('auto_delete_invites', False),
            'Profanity Filter': automod_config.get('profanity_filter', True),
            'Link Filter': automod_config.get('link_filter', False),
            'Raid Protection': automod_config.get('raid_protection', True)
        }
        
        automod_text = '\n'.join([f"**{k}:** {'✅' if v else '❌'}" for k, v in automod_status.items()])
        embed.add_field(name="AutoMod Status", value=automod_text, inline=False)
        
        embed.set_footer(text="Use /config <setting> to modify these settings")
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @config.command(name="prefix", description="Set the bot prefix for this server")
    @app_commands.describe(new_prefix="The new prefix to use")
    async def set_prefix(self, ctx, new_prefix: str):
        """Set bot prefix"""
        if len(new_prefix) > 5:
            embed = discord.Embed(
                title="❌ Invalid Prefix",
                description="Prefix must be 5 characters or less!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if ctx.guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[ctx.guild.id] = {}
        
        self.bot.guild_configs[ctx.guild.id]['prefix'] = new_prefix
        
        embed = discord.Embed(
            title="✅ Prefix Updated",
            description=f"Bot prefix changed to `{new_prefix}`",
            color=discord.Color.green()
        )
        embed.add_field(name="Set by", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @config.command(name="modrole", description="Set the moderator role")
    @app_commands.describe(role="The role to set as moderator role")
    async def set_mod_role(self, ctx, role: discord.Role):
        """Set moderator role"""
        if ctx.guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[ctx.guild.id] = {}
        
        self.bot.guild_configs[ctx.guild.id]['mod_role'] = role.id
        
        embed = discord.Embed(
            title="✅ Moderator Role Set",
            description=f"Moderator role set to {role.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Set by", value=ctx.author.mention, inline=True)
        embed.add_field(name="Role Members", value=str(len(role.members)), inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @config.command(name="adminrole", description="Set the administrator role")
    @app_commands.describe(role="The role to set as administrator role")
    async def set_admin_role(self, ctx, role: discord.Role):
        """Set administrator role"""
        if ctx.guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[ctx.guild.id] = {}
        
        self.bot.guild_configs[ctx.guild.id]['admin_role'] = role.id
        
        embed = discord.Embed(
            title="✅ Administrator Role Set",
            description=f"Administrator role set to {role.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Set by", value=ctx.author.mention, inline=True)
        embed.add_field(name="Role Members", value=str(len(role.members)), inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @config.command(name="logchannel", description="Set the general log channel")
    @app_commands.describe(channel="The channel to use for general logs")
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Set general log channel"""
        if ctx.guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[ctx.guild.id] = {}
        
        self.bot.guild_configs[ctx.guild.id]['log_channel'] = channel.id
        
        # Send test message
        test_embed = discord.Embed(
            title="📋 Log Channel Configured",
            description="This channel has been set as the general log channel.",
            color=discord.Color.blue()
        )
        test_embed.add_field(name="Configured by", value=ctx.author.mention, inline=True)
        test_embed.timestamp = datetime.utcnow()
        
        try:
            await channel.send(embed=test_embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="⚠️ Warning",
                description=f"Log channel set to {channel.mention}, but I cannot send messages there!",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)
        
        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"General log channel set to {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Set by", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @config.command(name="modlogchannel", description="Set the moderation log channel")
    @app_commands.describe(channel="The channel to use for moderation logs")
    async def set_mod_log_channel(self, ctx, channel: discord.TextChannel):
        """Set moderation log channel"""
        if ctx.guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[ctx.guild.id] = {}
        
        self.bot.guild_configs[ctx.guild.id]['mod_log_channel'] = channel.id
        
        embed = discord.Embed(
            title="✅ Moderation Log Channel Set",
            description=f"Moderation log channel set to {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Set by", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @config.command(name="warnthreshold", description="Set the warning threshold for automatic actions")
    @app_commands.describe(threshold="Number of warnings before automatic action (1-10)")
    async def set_warn_threshold(self, ctx, threshold: int):
        """Set warning threshold"""
        if threshold < 1 or threshold > 10:
            embed = discord.Embed(
                title="❌ Invalid Threshold",
                description="Warning threshold must be between 1 and 10!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if ctx.guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[ctx.guild.id] = {}
        
        self.bot.guild_configs[ctx.guild.id]['warn_threshold'] = threshold
        
        embed = discord.Embed(
            title="✅ Warning Threshold Set",
            description=f"Warning threshold set to **{threshold}** warnings",
            color=discord.Color.green()
        )
        embed.add_field(name="Set by", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="setup", description="Quick server setup wizard")
    @commands.has_permissions(administrator=True)
    async def quick_setup(self, ctx):
        """Quick setup wizard for new servers"""
        embed = discord.Embed(
            title="🛠️ Quick Setup Wizard",
            description="I'll help you set up basic moderation features for your server!",
            color=discord.Color.blue()
        )
        
        setup_msg = await ctx.send(embed=embed)
        
        # Initialize guild config
        if ctx.guild.id not in self.bot.guild_configs:
            self.bot.guild_configs[ctx.guild.id] = {
                'prefix': self.bot.config.get('default_prefix', '!'),
                'warn_threshold': 3,
                'automod_enabled': True
            }
        
        # Create basic moderation channels
        try:
            # Create moderation category
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            mod_category = await ctx.guild.create_category("🛡️ Moderation", overwrites=overwrites)
            
            # Create log channels
            log_channel = await ctx.guild.create_text_channel(
                "mod-logs",
                category=mod_category,
                topic="General moderation and server logs"
            )
            
            member_logs = await ctx.guild.create_text_channel(
                "member-logs", 
                category=mod_category,
                topic="Member join/leave and update logs"
            )
            
            message_logs = await ctx.guild.create_text_channel(
                "message-logs",
                category=mod_category, 
                topic="Message edit and deletion logs"
            )
            
            # Update config
            self.bot.guild_configs[ctx.guild.id].update({
                'log_channel': log_channel.id,
                'mod_log_channel': log_channel.id,
                'member_log_channel': member_logs.id,
                'message_log_channel': message_logs.id
            })
            
            # Create muted role
            muted_role = await ctx.guild.create_role(
                name="Muted",
                color=discord.Color.dark_gray(),
                reason="Quick setup - muted role"
            )
            
            # Set permissions for muted role
            for channel in ctx.guild.channels:
                if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
                    await channel.set_permissions(
                        muted_role,
                        send_messages=False,
                        speak=False,
                        add_reactions=False,
                        reason="Muted role setup"
                    )
            
            self.bot.guild_configs[ctx.guild.id]['mute_role'] = muted_role.id
            
            # Success embed
            success_embed = discord.Embed(
                title="✅ Setup Complete!",
                description="Your server has been configured with basic moderation features.",
                color=discord.Color.green()
            )
            
            success_embed.add_field(
                name="🏷️ Channels Created",
                value=f"• {log_channel.mention} - General logs\n• {member_logs.mention} - Member activity\n• {message_logs.mention} - Message logs",
                inline=False
            )
            
            success_embed.add_field(
                name="🎭 Roles Created",
                value=f"• {muted_role.mention} - Muted role with proper permissions",
                inline=False
            )
            
            success_embed.add_field(
                name="⚙️ Settings Configured",
                value=f"• Prefix: `{self.bot.guild_configs[ctx.guild.id]['prefix']}`\n• Warning threshold: {self.bot.guild_configs[ctx.guild.id]['warn_threshold']}\n• AutoMod: Enabled",
                inline=False
            )
            
            success_embed.add_field(
                name="📝 Next Steps",
                value="• Use `/config modrole <role>` to set moderator role\n• Use `/config adminrole <role>` to set admin role\n• Customize AutoMod with `/automod <setting> <value>`\n• Test moderation commands!",
                inline=False
            )
            
            success_embed.set_footer(text="Setup completed successfully!")
            success_embed.timestamp = datetime.utcnow()
            
            await setup_msg.edit(embed=success_embed)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Setup Failed",
                description="I don't have sufficient permissions to create channels and roles!",
                color=discord.Color.red()
            )
            error_embed.add_field(
                name="Required Permissions",
                value="• Manage Channels\n• Manage Roles\n• Send Messages\n• Embed Links",
                inline=False
            )
            await setup_msg.edit(embed=error_embed)
        
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Setup Error",
                description=f"An error occurred during setup: {str(e)}",
                color=discord.Color.red()
            )
            await setup_msg.edit(embed=error_embed)
    
    @commands.hybrid_command(name="reset", description="Reset server configuration (DANGEROUS)")
    @commands.has_permissions(administrator=True)
    async def reset_config(self, ctx):
        """Reset server configuration"""
        embed = discord.Embed(
            title="⚠️ Reset Configuration",
            description="This will reset ALL server configuration settings!\n\nAre you sure you want to continue?",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="This will reset:", 
            value="• Bot prefix\n• All role assignments\n• All channel assignments\n• Warning thresholds\n• AutoMod settings", 
            inline=False
        )
        embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                # Reset configuration
                if ctx.guild.id in self.bot.guild_configs:
                    del self.bot.guild_configs[ctx.guild.id]
                
                success_embed = discord.Embed(
                    title="✅ Configuration Reset",
                    description="All server configuration has been reset to defaults.",
                    color=discord.Color.green()
                )
                success_embed.add_field(name="Reset by", value=ctx.author.mention, inline=True)
                success_embed.timestamp = datetime.utcnow()
                
                await msg.edit(embed=success_embed)
                await msg.clear_reactions()
                
            else:
                cancel_embed = discord.Embed(
                    title="❌ Reset Cancelled",
                    description="Configuration reset has been cancelled.",
                    color=discord.Color.blue()
                )
                await msg.edit(embed=cancel_embed)
                await msg.clear_reactions()
                
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Timeout",
                description="Configuration reset timed out.",
                color=discord.Color.gray()
            )
            await msg.edit(embed=timeout_embed)
            await msg.clear_reactions()

async def setup(bot):
    await bot.add_cog(Configuration(bot))