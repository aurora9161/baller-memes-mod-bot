import discord
from discord.ext import commands
from discord import app_commands
import platform
import psutil
from datetime import datetime
import time

class Utility(commands.Cog):
    """Utility commands for server information and diagnostics"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.utcnow()
    
    @commands.hybrid_command(name="ping", description="Check bot latency")
    async def ping(self, ctx):
        """Check bot latency"""
        start_time = time.time()
        message = await ctx.send("🏓 Pinging...")
        end_time = time.time()
        
        api_latency = round((end_time - start_time) * 1000, 2)
        websocket_latency = round(self.bot.latency * 1000, 2)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green()
        )
        embed.add_field(name="API Latency", value=f"{api_latency}ms", inline=True)
        embed.add_field(name="WebSocket Latency", value=f"{websocket_latency}ms", inline=True)
        
        # Status based on latency
        if websocket_latency < 100:
            status = "🟢 Excellent"
        elif websocket_latency < 200:
            status = "🟡 Good"
        elif websocket_latency < 500:
            status = "🟠 Fair"
        else:
            status = "🔴 Poor"
        
        embed.add_field(name="Status", value=status, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await message.edit(content="", embed=embed)
    
    @commands.hybrid_command(name="userinfo", description="Get information about a user")
    @app_commands.describe(member="The member to get information about")
    async def userinfo(self, ctx, member: discord.Member = None):
        """Get user information"""
        if not member:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"👤 User Information: {member.display_name}",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue()
        )
        
        # Basic info
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        
        # Dates
        embed.add_field(
            name="Account Created", 
            value=f"<t:{int(member.created_at.timestamp())}:F>\n<t:{int(member.created_at.timestamp())}:R>", 
            inline=True
        )
        
        if member.joined_at:
            embed.add_field(
                name="Joined Server", 
                value=f"<t:{int(member.joined_at.timestamp())}:F>\n<t:{int(member.joined_at.timestamp())}:R>", 
                inline=True
            )
        
        # Status and activity
        status_emojis = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟡 Idle",
            discord.Status.dnd: "🔴 Do Not Disturb",
            discord.Status.offline: "⚫ Offline"
        }
        
        embed.add_field(
            name="Status", 
            value=status_emojis.get(member.status, "❓ Unknown"), 
            inline=True
        )
        
        # Roles (limit to prevent embed from being too long)
        if len(member.roles) > 1:
            roles = [role.mention for role in reversed(member.roles[1:])][:20]  # Skip @everyone, limit to 20
            roles_text = " ".join(roles)
            if len(member.roles) > 21:
                roles_text += f" (+{len(member.roles) - 21} more)"
            embed.add_field(name=f"Roles ({len(member.roles) - 1})", value=roles_text, inline=False)
        
        # Permissions (if user has notable permissions)
        notable_perms = []
        if member.guild_permissions.administrator:
            notable_perms.append("Administrator")
        elif member.guild_permissions.manage_guild:
            notable_perms.append("Manage Server")
        elif member.guild_permissions.manage_channels:
            notable_perms.append("Manage Channels")
        elif member.guild_permissions.manage_messages:
            notable_perms.append("Manage Messages")
        elif member.guild_permissions.kick_members:
            notable_perms.append("Kick Members")
        elif member.guild_permissions.ban_members:
            notable_perms.append("Ban Members")
        
        if notable_perms:
            embed.add_field(name="Key Permissions", value=", ".join(notable_perms), inline=False)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="serverinfo", description="Get information about the server")
    async def serverinfo(self, ctx):
        """Get server information"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"🏰 Server Information: {guild.name}",
            color=discord.Color.blue()
        )
        
        # Basic info
        embed.add_field(name="Server ID", value=str(guild.id), inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(
            name="Created", 
            value=f"<t:{int(guild.created_at.timestamp())}:F>\n<t:{int(guild.created_at.timestamp())}:R>", 
            inline=True
        )
        
        # Member stats
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])
        
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {total_members}\n**Humans:** {humans}\n**Bots:** {bots}",
            inline=True
        )
        
        # Channel stats
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed.add_field(
            name="📝 Channels",
            value=f"**Text:** {text_channels}\n**Voice:** {voice_channels}\n**Categories:** {categories}",
            inline=True
        )
        
        # Other stats
        embed.add_field(
            name="📊 Other",
            value=f"**Roles:** {len(guild.roles)}\n**Emojis:** {len(guild.emojis)}\n**Boosts:** {guild.premium_subscription_count}",
            inline=True
        )
        
        # Features
        if guild.features:
            features = []
            feature_names = {
                'COMMUNITY': 'Community Server',
                'VERIFIED': 'Verified',
                'PARTNERED': 'Partnered',
                'BANNER': 'Banner',
                'VANITY_URL': 'Vanity URL',
                'ANIMATED_ICON': 'Animated Icon',
                'INVITE_SPLASH': 'Invite Splash',
                'VIP_REGIONS': 'VIP Voice Regions',
                'COMMERCE': 'Commerce',
                'NEWS': 'News Channels',
                'DISCOVERABLE': 'Server Discovery'
            }
            
            for feature in guild.features:
                if feature in feature_names:
                    features.append(feature_names[feature])
            
            if features:
                embed.add_field(name="✨ Features", value="\n".join(features[:10]), inline=False)
        
        # Verification level
        verification_levels = {
            discord.VerificationLevel.none: "None",
            discord.VerificationLevel.low: "Low",
            discord.VerificationLevel.medium: "Medium",
            discord.VerificationLevel.high: "High",
            discord.VerificationLevel.highest: "Highest"
        }
        
        embed.add_field(
            name="🛡️ Security",
            value=f"**Verification:** {verification_levels.get(guild.verification_level, 'Unknown')}\n**2FA Required:** {'Yes' if guild.mfa_level else 'No'}",
            inline=True
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="avatar", description="Get a user's avatar")
    @app_commands.describe(member="The member to get avatar for")
    async def avatar(self, ctx, member: discord.Member = None):
        """Get user avatar"""
        if not member:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"🖼️ {member.display_name}'s Avatar",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue()
        )
        
        embed.set_image(url=member.display_avatar.url)
        embed.add_field(
            name="Links",
            value=f"[PNG]({member.display_avatar.with_format('png').url}) | [JPG]({member.display_avatar.with_format('jpg').url}) | [WEBP]({member.display_avatar.with_format('webp').url})",
            inline=False
        )
        
        # If they have a server-specific avatar, show global too
        if member.avatar != member.display_avatar and member.avatar:
            embed.add_field(
                name="Global Avatar",
                value=f"[PNG]({member.avatar.with_format('png').url}) | [JPG]({member.avatar.with_format('jpg').url}) | [WEBP]({member.avatar.with_format('webp').url})",
                inline=False
            )
        
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="botinfo", description="Get information about the bot")
    async def botinfo(self, ctx):
        """Get bot information"""
        embed = discord.Embed(
            title="🤖 Baller Memes Moderation Bot",
            description="Advanced Discord moderation bot with comprehensive features",
            color=discord.Color.blue()
        )
        
        # Bot stats
        uptime = datetime.utcnow() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed.add_field(
            name="📊 Statistics",
            value=f"**Guilds:** {len(self.bot.guilds)}\n**Users:** {len(set(self.bot.get_all_members()))}\n**Commands:** {len([cmd for cmd in self.bot.walk_commands()])}",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Uptime",
            value=f"{days}d {hours}h {minutes}m {seconds}s",
            inline=True
        )
        
        embed.add_field(
            name="🏓 Latency",
            value=f"{round(self.bot.latency * 1000, 2)}ms",
            inline=True
        )
        
        # System info
        try:
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            cpu_usage = process.cpu_percent()
            
            embed.add_field(
                name="💻 System",
                value=f"**Python:** {platform.python_version()}\n**Discord.py:** {discord.__version__}\n**Platform:** {platform.system()}",
                inline=True
            )
            
            embed.add_field(
                name="📈 Resources",
                value=f"**Memory:** {memory_usage:.1f} MB\n**CPU:** {cpu_usage}%",
                inline=True
            )
        except Exception:
            embed.add_field(
                name="💻 System",
                value=f"**Python:** {platform.python_version()}\n**Discord.py:** {discord.__version__}\n**Platform:** {platform.system()}",
                inline=True
            )
        
        # Features
        embed.add_field(
            name="⚡ Features",
            value="• Advanced Moderation\n• Auto-Moderation\n• Comprehensive Logging\n• Hybrid Commands\n• Configurable Settings",
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Bot ID: {self.bot.user.id}")
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="invite", description="Get bot invite link")
    async def invite(self, ctx):
        """Get bot invite link"""
        permissions = discord.Permissions(
            ban_members=True,
            kick_members=True,
            manage_messages=True,
            manage_roles=True,
            manage_channels=True,
            view_audit_log=True,
            read_messages=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            add_reactions=True,
            use_slash_commands=True,
            moderate_members=True
        )
        
        invite_url = discord.utils.oauth_url(self.bot.user.id, permissions=permissions)
        
        embed = discord.Embed(
            title="🔗 Invite Baller Memes Moderation Bot",
            description=f"[Click here to invite the bot to your server!]({invite_url})",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🛡️ Permissions Included",
            value="• Ban/Kick Members\n• Manage Messages & Roles\n• Manage Channels\n• View Audit Log\n• Moderate Members (Timeout)",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Setup Instructions",
            value="1. Click the invite link\n2. Select your server\n3. Authorize permissions\n4. Run `/setup` for quick config\n5. Start moderating!",
            inline=True
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="help", description="Show help information")
    async def help_command(self, ctx):
        """Show help information"""
        embed = discord.Embed(
            title="🆘 Baller Memes Moderation Bot - Help",
            description="Advanced Discord moderation bot with hybrid commands",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🛡️ Moderation Commands",
            value="`/ban` - Ban a member\n`/kick` - Kick a member\n`/mute` - Mute a member\n`/warn` - Warn a member\n`/purge` - Delete messages\n`/slowmode` - Set channel slowmode",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Configuration Commands",
            value="`/config` - View/change settings\n`/setup` - Quick server setup\n`/automod` - Configure auto-moderation",
            inline=True
        )
        
        embed.add_field(
            name="📊 Utility Commands",
            value="`/userinfo` - User information\n`/serverinfo` - Server information\n`/ping` - Check bot latency\n`/botinfo` - Bot information",
            inline=True
        )
        
        embed.add_field(
            name="📝 Logging Commands",
            value="`/logs` - View recent logs\n`/violations` - View automod violations",
            inline=True
        )
        
        embed.add_field(
            name="🔧 Owner Commands",
            value="`/reload` - Reload cog\n`/sync` - Sync slash commands\n`/blacklist` - Blacklist user",
            inline=True
        )
        
        embed.add_field(
            name="⚡ Hybrid Commands",
            value="All commands work as both slash commands (`/ban`) and prefix commands (`!ban`)",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Links",
            value="Use `/invite` to get the bot invite link\nUse `/support` for help and support",
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))