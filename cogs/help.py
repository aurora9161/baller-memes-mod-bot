import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional

# Build permissions without deprecated/invalid flags
INVITE_PERMS = (
    discord.Permissions(
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
        moderate_members=True
    )
)

class HelpView(discord.ui.View):
    """Interactive help system with dropdown and clean buttons (discord.py v2 safe)."""
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        invite_url = discord.utils.oauth_url(self.bot.user.id, permissions=INVITE_PERMS)
        self.add_item(discord.ui.Button(label="🔗 Invite Bot", style=discord.ButtonStyle.link, url=invite_url))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This help menu is not for you!", ephemeral=True)
            return False
        return True

    @discord.ui.select(
        placeholder="🔍 Choose a command category...",
        options=[
            discord.SelectOption(label="🛡️ Moderation", value="moderation", description="Moderation commands"),
            discord.SelectOption(label="⚙️ Configuration", value="config", description="Setup & settings"),
            discord.SelectOption(label="📊 Utility", value="utility", description="Info & tools"),
            discord.SelectOption(label="📝 Logging", value="logging", description="Audit logs"),
            discord.SelectOption(label="👑 Owner", value="owner", description="Owner-only")
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        category = select.values[0]
        embed = await self.get_category_embed(category)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.primary)
    async def home_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        embed = await self.get_main_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def get_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🛡️ Help Center",
            description=(
                "Enterprise-grade Discord moderation with advanced features.\n\n"
                f"🏠 **Servers:** {len(self.bot.guilds)}\n"
                f"👥 **Users:** {len(set(self.bot.get_all_members()))}\n"
                f"⚡ **Commands:** {len([cmd for cmd in self.bot.walk_commands()])}\n\n"
                "Use the menu below to browse categories."
            ),
            color=discord.Color.blue()
        )
        embed.add_field(name="Quick Commands", value="`/setup`, `/config`, `/ban`, `/logs`", inline=False)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Use /help <command> for detailed usage")
        embed.timestamp = datetime.utcnow()
        return embed

    async def get_category_embed(self, category: str) -> discord.Embed:
        category = category.lower()
        if category == "moderation":
            title = "🛡️ Moderation"
            lines = [
                "`/ban @user [duration] [reason]` - Ban a member",
                "`/unban <user_id> [reason]` - Unban a user",
                "`/kick @user [reason]` - Kick a member",
                "`/mute @user [duration] [reason]` - Mute a member",
                "`/timeout @user <duration> [reason]` - Timeout a member",
                "`/purge <amount> [user]` - Bulk delete",
                "`/slowmode <seconds>` - Channel slowmode",
                "`/warnings [@user]` - View warnings",
                "`/clearwarnings @user` - Clear warnings"
            ]
            color = discord.Color.red()
        elif category == "config":
            title = "⚙️ Configuration"
            lines = [
                "`/setup` - Quick setup",
                "`/config` - View settings",
                "`/config prefix <prefix>`",
                "`/config modrole @role` | `/config adminrole @role`",
                "`/config logchannel #channel` | `/config modlogchannel #channel`",
                "`/warnthreshold <1-10>` - Set warning threshold"
            ]
            color = discord.Color.green()
        elif category == "utility":
            title = "📊 Utility"
            lines = [
                "`/userinfo [@user]` | `/avatar [@user]`",
                "`/serverinfo` | `/botinfo` | `/ping`",
                "`/invite` | `/support`"
            ]
            color = discord.Color.blurple()
        elif category == "logging":
            title = "📝 Logging"
            lines = [
                "`/logs [type] [amount]` - View logs"
            ]
            color = discord.Color.purple()
        elif category == "owner":
            title = "👑 Owner"
            lines = [
                "`/reload <cog>` | `/load <cog>` | `/unload <cog>`",
                "`/sync` | `/shutdown` | `/guilds`",
                "`/blacklist <user_id>` | `/unblacklist <user_id>`"
            ]
            color = discord.Color.gold()
        else:
            return await self.get_main_embed()
        embed = discord.Embed(title=title, description="\n".join(lines), color=color)
        embed.set_footer(text=f"Category: {category.title()}")
        embed.timestamp = datetime.utcnow()
        return embed

class Help(commands.Cog):
    """Clean, professional help system"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.remove_command('help')

    @commands.hybrid_command(name="help", description="Interactive help with categories and examples")
    @app_commands.describe(command="Specific command to explain", category="Category to open")
    async def help_command(self, ctx: commands.Context, command: Optional[str] = None, category: Optional[str] = None):
        if command:
            return await self.show_command_help(ctx, command)
        if category:
            view = HelpView(self.bot, ctx.author.id)
            embed = await view.get_category_embed(category)
            return await ctx.send(embed=embed, view=view)
        view = HelpView(self.bot, ctx.author.id)
        embed = await view.get_main_embed()
        try:
            await ctx.send(embed=embed, view=view)
        except discord.HTTPException:
            await ctx.send(embed=embed)

    async def show_command_help(self, ctx: commands.Context, name: str):
        cmd = self.bot.get_command(name)
        if not cmd:
            return await ctx.send(embed=discord.Embed(title="❌ Command Not Found", description=f"No command named `{name}`.", color=discord.Color.red()))
        usage = f"/{cmd.name}"
        if cmd.signature:
            usage += f" {cmd.signature}"
        embed = discord.Embed(title=f"📖 {cmd.name}", description=cmd.description or "No description.", color=discord.Color.blue())
        embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
        if getattr(cmd, 'aliases', None):
            embed.add_field(name="Aliases", value=", ".join(f"`{a}`" for a in cmd.aliases), inline=False)
        embed.add_field(name="Category", value=cmd.cog.qualified_name if cmd.cog else "General", inline=True)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
