import discord
from discord.ext import commands
from discord import app_commands
import platform
from datetime import datetime
import time
import os

class Utility(commands.Cog):
    """Utility commands for server information and diagnostics"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.utcnow()
    
    async def cog_load(self):
        """Ensure unique cog name to avoid clashes."""
        self.__cog_name__ = "Utility"
    
    @commands.hybrid_command(name="ping", description="Check bot latency")
    async def ping(self, ctx):
        start_time = time.time()
        message = await ctx.send("🏓 Pinging...")
        end_time = time.time()
        api_latency = round((end_time - start_time) * 1000, 2)
        websocket_latency = round(self.bot.latency * 1000, 2)
        embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
        embed.add_field(name="API Latency", value=f"{api_latency}ms", inline=True)
        embed.add_field(name="WebSocket Latency", value=f"{websocket_latency}ms", inline=True)
        status = "🟢 Excellent" if websocket_latency < 100 else ("🟡 Good" if websocket_latency < 200 else ("🟠 Fair" if websocket_latency < 500 else "🔴 Poor"))
        embed.add_field(name="Status", value=status, inline=True)
        embed.timestamp = datetime.utcnow()
        await message.edit(content="", embed=embed)
    
    @commands.hybrid_command(name="userinfo", description="Get information about a user")
    @app_commands.describe(member="The member to get information about")
    async def userinfo(self, ctx, member: discord.Member = None):
        if not member:
            member = ctx.author
        embed = discord.Embed(title=f"👤 User Information: {member.display_name}", color=member.color if member.color != discord.Color.default() else discord.Color.blue())
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:F>\n<t:{int(member.created_at.timestamp())}:R>", inline=True)
        if member.joined_at:
            embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:F>\n<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        status_emojis = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟡 Idle",
            discord.Status.dnd: "🔴 Do Not Disturb",
            discord.Status.offline: "⚫ Offline"
        }
        embed.add_field(name="Status", value=status_emojis.get(member.status, "❓ Unknown"), inline=True)
        if len(member.roles) > 1:
            roles = [role.mention for role in reversed(member.roles[1:])][:20]
            roles_text = " ".join(roles)
            if len(member.roles) > 21:
                roles_text += f" (+{len(member.roles) - 21} more)"
            embed.add_field(name=f"Roles ({len(member.roles) - 1})", value=roles_text, inline=False)
        notable_perms = []
        gp = member.guild_permissions
        if gp.administrator: notable_perms.append("Administrator")
        if gp.manage_guild: notable_perms.append("Manage Server")
        if gp.manage_channels: notable_perms.append("Manage Channels")
        if gp.manage_messages: notable_perms.append("Manage Messages")
        if gp.kick_members: notable_perms.append("Kick Members")
        if gp.ban_members: notable_perms.append("Ban Members")
        if notable_perms:
            embed.add_field(name="Key Permissions", value=", ".join(notable_perms), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="serverinfo", description="Get information about the server")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title=f"🏰 Server Information: {guild.name}", color=discord.Color.blue())
        embed.add_field(name="Server ID", value=str(guild.id), inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:F>\n<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])
        embed.add_field(name="👥 Members", value=f"**Total:** {total_members}\n**Humans:** {humans}\n**Bots:** {bots}", inline=True)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        embed.add_field(name="📝 Channels", value=f"**Text:** {text_channels}\n**Voice:** {voice_channels}\n**Categories:** {categories}", inline=True)
        embed.add_field(name="📊 Other", value=f"**Roles:** {len(guild.roles)}\n**Emojis:** {len(guild.emojis)}\n**Boosts:** {guild.premium_subscription_count}", inline=True)
        verification_levels = {
            discord.VerificationLevel.none: "None",
            discord.VerificationLevel.low: "Low",
            discord.VerificationLevel.medium: "Medium",
            discord.VerificationLevel.high: "High",
            discord.VerificationLevel.highest: "Highest"
        }
        embed.add_field(name="🛡️ Security", value=f"**Verification:** {verification_levels.get(guild.verification_level, 'Unknown')}\n**2FA Required:** {'Yes' if guild.mfa_level else 'No'}", inline=True)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="avatar", description="Get a user's avatar")
    @app_commands.describe(member="The member to get avatar for")
    async def avatar(self, ctx, member: discord.Member = None):
        if not member:
            member = ctx.author
        embed = discord.Embed(title=f"🖼️ {member.display_name}'s Avatar", color=member.color if member.color != discord.Color.default() else discord.Color.blue())
        embed.set_image(url=member.display_avatar.url)
        try:
            png = member.display_avatar.replace(format='png').url
            jpg = member.display_avatar.replace(format='jpg').url
            webp = member.display_avatar.replace(format='webp').url
            embed.add_field(name="Links", value=f"[PNG]({png}) | [JPG]({jpg}) | [WEBP]({webp})", inline=False)
        except Exception:
            pass
        if member.avatar != member.display_avatar and member.avatar:
            try:
                png = member.avatar.replace(format='png').url
                jpg = member.avatar.replace(format='jpg').url
                webp = member.avatar.replace(format='webp').url
                embed.add_field(name="Global Avatar", value=f"[PNG]({png}) | [JPG]({jpg}) | [WEBP]({webp})", inline=False)
            except Exception:
                pass
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="botinfo", description="Get information about the bot")
    async def botinfo(self, ctx):
        embed = discord.Embed(title="🤖 Baller Memes Moderation Bot", description="Advanced Discord moderation bot with comprehensive features", color=discord.Color.blue())
        uptime = datetime.utcnow() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        embed.add_field(name="📊 Statistics", value=f"**Guilds:** {len(self.bot.guilds)}\n**Users:** {len(set(self.bot.get_all_members()))}\n**Commands:** {len([cmd for cmd in self.bot.walk_commands()])}", inline=True)
        embed.add_field(name="⏰ Uptime", value=f"{days}d {hours}h {minutes}m {seconds}s", inline=True)
        embed.add_field(name="🏓 Latency", value=f"{round(self.bot.latency * 1000, 2)}ms", inline=True)
        embed.add_field(name="💻 System", value=f"**Python:** {platform.python_version()}\n**discord.py:** {discord.__version__}\n**Platform:** {platform.system()}", inline=True)
        embed.add_field(name="📈 Resources", value=f"**PID:** {os.getpid()}", inline=True)
        embed.add_field(name="⚡ Features", value="• Advanced Moderation\n• Auto-Moderation\n• Comprehensive Logging\n• Hybrid Commands\n• Configurable Settings", inline=False)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Bot ID: {self.bot.user.id}")
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="invite", description="Get bot invite link")
    async def invite(self, ctx):
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
        embed = discord.Embed(title="🔗 Invite Baller Memes Moderation Bot", description=f"[Click here to invite the bot to your server!]({invite_url})", color=discord.Color.blue())
        embed.add_field(name="🛡️ Permissions Included", value="• Ban/Kick Members\n• Manage Messages & Roles\n• Manage Channels\n• View Audit Log\n• Moderate Members (Timeout)", inline=True)
        embed.add_field(name="⚙️ Setup Instructions", value="1. Click the invite link\n2. Select your server\n3. Authorize permissions\n4. Run `/setup` for quick config\n5. Start moderating!", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
