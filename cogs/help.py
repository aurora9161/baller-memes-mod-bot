import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
from typing import Optional

class HelpView(discord.ui.View):
    """Interactive help system with dropdown menus and buttons"""
    
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the command invoker to interact"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This help menu is not for you!", ephemeral=True)
            return False
        return True
    
    @discord.ui.select(
        placeholder="🔍 Choose a command category...",
        options=[
            discord.SelectOption(
                label="🛡️ Moderation",
                value="moderation",
                description="Moderation commands for managing your server",
                emoji="🛡️"
            ),
            discord.SelectOption(
                label="🤖 Auto-Moderation", 
                value="automod",
                description="Automated moderation and spam protection",
                emoji="🤖"
            ),
            discord.SelectOption(
                label="⚙️ Configuration",
                value="config", 
                description="Server configuration and setup commands",
                emoji="⚙️"
            ),
            discord.SelectOption(
                label="📊 Utility",
                value="utility",
                description="Server information and utility commands", 
                emoji="📊"
            ),
            discord.SelectOption(
                label="📝 Logging",
                value="logging",
                description="Audit logs and moderation tracking",
                emoji="📝"
            ),
            discord.SelectOption(
                label="👑 Owner",
                value="owner",
                description="Bot owner and management commands",
                emoji="👑"
            )
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle category selection"""
        category = select.values[0]
        embed = await self.get_category_embed(category)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.primary)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to main help page"""
        embed = await self.get_main_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🔗 Invite Bot", style=discord.ButtonStyle.link, url="https://discord.com/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=1099511627775&scope=bot%20applications.commands")
    async def invite_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass  # Link buttons don't need handlers
    
    @discord.ui.button(label="📚 Documentation", style=discord.ButtonStyle.secondary)
    async def docs_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show documentation embed"""
        embed = discord.Embed(
            title="📚 Documentation & Support",
            description="Comprehensive guides and support resources",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🚀 Quick Start Guide",
            value="1. Run `/setup` for automatic configuration\n2. Set moderator roles with `/config modrole`\n3. Configure logging with `/config logchannel`\n4. Customize AutoMod with `/automod`\n5. Test moderation commands!",
            inline=False
        )
        
        embed.add_field(
            name="📖 Command Usage",
            value="• **Hybrid Commands:** All commands work as both slash (`/ban`) and prefix (`!ban`)\n• **Permissions:** Commands check both Discord permissions and custom roles\n• **Error Handling:** Comprehensive error messages with solutions",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Advanced Configuration",
            value="• **Per-Channel Settings:** Different rules for different channels\n• **Role Hierarchy:** Automatic permission checking\n• **Custom Prefixes:** Set unique prefixes per server\n• **Backup & Restore:** Save and restore configurations",
            inline=False
        )
        
        embed.add_field(
            name="🆘 Support",
            value="• Use `/support` for help and troubleshooting\n• Check `/botinfo` for system status\n• Review `/logs` for recent activity\n• Contact bot administrators for advanced issues",
            inline=False
        )
        
        embed.set_footer(text="💡 Pro Tip: Use /help <command> for detailed command information")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def get_main_embed(self):
        """Generate the main help embed"""
        embed = discord.Embed(
            title="🛡️ Baller Memes Moderation Bot - Help Center",
            description="**Enterprise-grade Discord moderation with advanced features**\n\n" +
                       f"🏠 **Server Count:** {len(self.bot.guilds)}\n" +
                       f"👥 **User Count:** {len(set(self.bot.get_all_members()))}\n" +
                       f"⚡ **Commands:** {len([cmd for cmd in self.bot.walk_commands()])}\n\n" +
                       "Select a category below to explore commands, or use the buttons for quick actions.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Key Features",
            value="• **Hybrid Commands** - Slash & prefix support\n• **Smart AutoMod** - AI-powered content filtering\n• **Advanced Logging** - Comprehensive audit trails\n• **Role Management** - Sophisticated permission system\n• **Enterprise Security** - Professional-grade protection",
            inline=True
        )
        
        embed.add_field(
            name="🚀 Quick Commands",
            value="`/setup` - Quick server setup\n`/config` - View/edit settings\n`/ban` - Ban a member\n`/automod` - Configure filters\n`/logs` - View audit logs",
            inline=True
        )
        
        embed.add_field(
            name="💡 Getting Started",
            value="1️⃣ Run `/setup` for instant configuration\n2️⃣ Set roles with `/config modrole`\n3️⃣ Enable logging with `/config logchannel`\n4️⃣ Customize AutoMod settings\n5️⃣ You're ready to moderate!",
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="💎 Professional Discord Moderation • Use dropdown menu to explore categories")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    async def get_category_embed(self, category: str):
        """Generate category-specific help embeds"""
        
        if category == "moderation":
            embed = discord.Embed(
                title="🛡️ Moderation Commands",
                description="Comprehensive moderation tools for server management",
                color=discord.Color.red()
            )
            
            commands_data = [
                ("ban", "Ban a member from the server", "`/ban @user [reason] [duration]`", "🔨"),
                ("unban", "Unban a previously banned user", "`/unban <user_id> [reason]`", "🔓"),
                ("kick", "Kick a member from the server", "`/kick @user [reason]`", "👢"),
                ("mute", "Mute a member in all channels", "`/mute @user [duration] [reason]`", "🔇"),
                ("unmute", "Remove mute from a member", "`/unmute @user [reason]`", "🔊"),
                ("warn", "Issue a warning to a member", "`/warn @user <reason>`", "⚠️"),
                ("warnings", "View warnings for a member", "`/warnings @user`", "📋"),
                ("timeout", "Timeout a member", "`/timeout @user <duration> [reason]`", "⏰"),
                ("purge", "Bulk delete messages", "`/purge <amount> [user]`", "🗑️"),
                ("slowmode", "Set channel slowmode", "`/slowmode <seconds>`", "🐌"),
                ("lockdown", "Lock/unlock a channel", "`/lockdown [channel]`", "🔒"),
                ("massban", "Ban multiple users at once", "`/massban <user_ids>`", "🔨")
            ]
            
            for name, desc, usage, emoji in commands_data[:6]:  # First 6
                embed.add_field(
                    name=f"{emoji} **{name}**",
                    value=f"{desc}\n`Usage:` {usage}",
                    inline=True
                )
            
            embed.add_field(
                name="📊 **Advanced Features**",
                value="• **Temporary Actions** - Auto-expiring bans/mutes\n• **Bulk Operations** - Mass moderation tools\n• **Evidence Logging** - Complete audit trails\n• **Appeal System** - Built-in review process\n• **Smart Permissions** - Role hierarchy respect",
                inline=False
            )
        
        elif category == "automod":
            embed = discord.Embed(
                title="🤖 Auto-Moderation Commands",
                description="Advanced automated content filtering and spam protection",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="⚙️ **Configuration**",
                value="`/automod spam_detection true|false`\n`/automod profanity_filter true|false`\n`/automod max_mentions <number>`\n`/automod raid_protection true|false`",
                inline=True
            )
            
            embed.add_field(
                name="📊 **Monitoring**",
                value="`/violations @user` - View user violations\n`/clearviolations @user` - Reset violations\n`/automod_stats` - Server statistics",
                inline=True
            )
            
            embed.add_field(
                name="🛡️ **Protection Features**",
                value="• **Smart Spam Detection** - Pattern recognition\n• **Link Filtering** - Malicious URL protection\n• **Raid Protection** - Automatic server lockdown\n• **Profanity Filter** - Advanced word filtering\n• **Mention Limits** - Anti-ping spam\n• **Emoji Limits** - Prevent emoji spam\n• **Auto-Dehoist** - Remove special characters\n• **Account Age** - New account detection",
                inline=False
            )
        
        elif category == "config":
            embed = discord.Embed(
                title="⚙️ Configuration Commands", 
                description="Server setup and configuration management",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="🚀 **Quick Setup**",
                value="`/setup` - Automated server configuration\n`/reset` - Reset all settings (DANGER)",
                inline=True
            )
            
            embed.add_field(
                name="👥 **Roles**",
                value="`/config modrole @role` - Set moderator role\n`/config adminrole @role` - Set admin role",
                inline=True
            )
            
            embed.add_field(
                name="📝 **Channels**",
                value="`/config logchannel #channel`\n`/config modlogchannel #channel`\n`/config welcomechannel #channel`",
                inline=True
            )
            
            embed.add_field(
                name="🎛️ **Settings**",
                value="`/config prefix <prefix>` - Set bot prefix\n`/config warnthreshold <number>` - Warning limit\n`/config` - View current settings",
                inline=True
            )
            
            embed.add_field(
                name="💾 **Management**",
                value="• **Backup System** - Auto-save configurations\n• **Import/Export** - Transfer settings\n• **Per-Channel Rules** - Granular control\n• **Template System** - Quick deployment",
                inline=False
            )
        
        elif category == "utility":
            embed = discord.Embed(
                title="📊 Utility Commands",
                description="Server information and diagnostic tools", 
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="👤 **User Information**",
                value="`/userinfo [@user]` - Detailed user info\n`/avatar [@user]` - Get user avatar\n`/permissions @user` - Check permissions",
                inline=True
            )
            
            embed.add_field(
                name="🏰 **Server Information**", 
                value="`/serverinfo` - Complete server details\n`/membercount` - Member statistics\n`/roleinfo @role` - Role information",
                inline=True
            )
            
            embed.add_field(
                name="🔧 **Bot Information**",
                value="`/botinfo` - Bot statistics\n`/ping` - Latency check\n`/invite` - Bot invite link\n`/support` - Help resources",
                inline=True
            )
        
        elif category == "logging":
            embed = discord.Embed(
                title="📝 Logging Commands",
                description="Comprehensive audit logging and tracking",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="📋 **View Logs**",
                value="`/logs [type] [amount]` - Recent server logs\n`/modlogs @user` - User mod history\n`/search <query>` - Search log entries",
                inline=True
            )
            
            embed.add_field(
                name="📊 **Analytics**",
                value="`/stats` - Server activity stats\n`/violations @user` - AutoMod violations\n`/trends` - Moderation trends",
                inline=True
            )
            
            embed.add_field(
                name="🔍 **Log Types**",
                value="• **Moderation** - Bans, kicks, warnings\n• **Messages** - Edits, deletions\n• **Members** - Joins, leaves, updates\n• **Channels** - Creates, deletes, edits\n• **Roles** - Assignments, changes\n• **Voice** - Channel activity",
                inline=False
            )
        
        elif category == "owner":
            embed = discord.Embed(
                title="👑 Owner Commands",
                description="Bot administration and management (Owner Only)",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🔧 **Bot Management**",
                value="`/reload <cog>` - Reload bot modules\n`/sync` - Sync slash commands\n`/shutdown` - Shutdown bot\n`/restart` - Restart bot",
                inline=True
            )
            
            embed.add_field(
                name="🚫 **User Management**",
                value="`/blacklist <user_id>` - Blacklist user\n`/unblacklist <user_id>` - Remove blacklist\n`/globalban <user_id>` - Ban across servers",
                inline=True
            )
            
            embed.add_field(
                name="📊 **Analytics**",
                value="`/guilds` - List all servers\n`/leave <guild_id>` - Leave server\n`/eval <code>` - Execute code\n`/logs system` - System logs",
                inline=True
            )
        
        else:
            return await self.get_main_embed()
        
        embed.set_footer(text=f"💡 Use /help <command> for detailed usage • Category: {category.title()}")
        embed.timestamp = datetime.utcnow()
        
        return embed


class Help(commands.Cog):
    """Advanced help system with interactive menus and comprehensive documentation"""
    
    def __init__(self, bot):
        self.bot = bot
        # Remove default help command
        self.bot.remove_command('help')
    
    @commands.hybrid_command(name="help", description="Show comprehensive help information")
    @app_commands.describe(
        command="Get detailed help for a specific command",
        category="Show commands from a specific category"
    )
    async def help_command(
        self, 
        ctx, 
        command: Optional[str] = None,
        category: Optional[str] = None
    ):
        """Enhanced help command with interactive menus"""
        
        # If specific command requested
        if command:
            await self.show_command_help(ctx, command)
            return
        
        # If category requested
        if category:
            await self.show_category_help(ctx, category)
            return
        
        # Show main interactive help
        view = HelpView(self.bot, ctx.author.id)
        embed = await view.get_main_embed()
        
        try:
            await ctx.send(embed=embed, view=view)
        except discord.HTTPException:
            # Fallback to simple embed if view fails
            await ctx.send(embed=embed)
    
    async def show_command_help(self, ctx, command_name: str):
        """Show detailed help for a specific command"""
        cmd = self.bot.get_command(command_name)
        
        if not cmd:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"No command named `{command_name}` found.\nUse `/help` to see all available commands.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        embed = discord.Embed(
            title=f"📖 Command: `{cmd.name}`",
            description=cmd.description or "No description available.",
            color=discord.Color.blue()
        )
        
        # Usage
        usage = f"/{cmd.name}"
        if cmd.signature:
            usage += f" {cmd.signature}"
        embed.add_field(name="📝 Usage", value=f"`{usage}`", inline=False)
        
        # Aliases
        if cmd.aliases:
            embed.add_field(
                name="🔗 Aliases",
                value=", ".join([f"`{alias}`" for alias in cmd.aliases]),
                inline=True
            )
        
        # Permissions
        if hasattr(cmd, 'callback'):
            checks = getattr(cmd.callback, '__commands_checks__', [])
            if checks:
                perms = []
                for check in checks:
                    if hasattr(check, '__name__'):
                        if 'permissions' in check.__name__:
                            perms.append("Manage Messages")
                        elif 'admin' in check.__name__:
                            perms.append("Administrator")
                        elif 'owner' in check.__name__:
                            perms.append("Bot Owner")
                
                if perms:
                    embed.add_field(
                        name="🔒 Required Permissions",
                        value=", ".join(perms),
                        inline=True
                    )
        
        # Examples
        examples = {
            'ban': ["/ban @spammer Spam advertising", "/ban @user 7d Temporary ban"],
            'mute': ["/mute @user 1h Being disruptive", "/mute @user Permanent mute"],
            'purge': ["/purge 10", "/purge 50 @spammer"],
            'config': ["/config prefix !", "/config modrole @Moderator"],
            'automod': ["/automod spam_detection true", "/automod max_mentions 5"]
        }
        
        if cmd.name in examples:
            embed.add_field(
                name="💡 Examples",
                value="\n".join([f"`{ex}`" for ex in examples[cmd.name]]),
                inline=False
            )
        
        # Category info
        if hasattr(cmd, 'cog') and cmd.cog:
            embed.add_field(
                name="📂 Category",
                value=cmd.cog.qualified_name,
                inline=True
            )
        
        embed.set_footer(text="💎 Enterprise-grade Discord moderation")
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    async def show_category_help(self, ctx, category: str):
        """Show help for a specific category"""
        view = HelpView(self.bot, ctx.author.id)
        embed = await view.get_category_embed(category.lower())
        
        try:
            await ctx.send(embed=embed, view=view)
        except discord.HTTPException:
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="commands", description="List all available commands")
    @app_commands.describe(cog="Filter commands by cog/category")
    async def list_commands(self, ctx, cog: Optional[str] = None):
        """List all commands, optionally filtered by cog"""
        
        if cog:
            target_cog = self.bot.get_cog(cog.title())
            if not target_cog:
                embed = discord.Embed(
                    title="❌ Category Not Found",
                    description=f"No category named `{cog}` found.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
            
            commands = target_cog.get_commands()
            embed = discord.Embed(
                title=f"📋 Commands in {target_cog.qualified_name}",
                color=discord.Color.blue()
            )
        else:
            commands = self.bot.commands
            embed = discord.Embed(
                title="📋 All Available Commands",
                description=f"Total: {len(list(commands))} commands",
                color=discord.Color.blue()
            )
        
        # Group commands by cog
        cog_commands = {}
        for cmd in commands:
            if cmd.hidden:
                continue
                
            cog_name = cmd.cog.qualified_name if cmd.cog else "No Category"
            if cog_name not in cog_commands:
                cog_commands[cog_name] = []
            cog_commands[cog_name].append(cmd)
        
        # Add fields for each cog
        for cog_name, cmd_list in cog_commands.items():
            if len(cmd_list) == 0:
                continue
                
            cmd_names = [f"`{cmd.name}`" for cmd in cmd_list[:10]]  # Limit to 10 per cog
            if len(cmd_list) > 10:
                cmd_names.append(f"... and {len(cmd_list) - 10} more")
            
            embed.add_field(
                name=f"📂 {cog_name}",
                value=" • ".join(cmd_names),
                inline=False
            )
        
        embed.set_footer(text="Use /help <command> for detailed information about a command")
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="support", description="Get support and troubleshooting help")
    async def support(self, ctx):
        """Support and troubleshooting information"""
        embed = discord.Embed(
            title="🆘 Support & Troubleshooting",
            description="Get help with the Baller Memes Moderation Bot",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🚀 Quick Fixes",
            value="• **Bot not responding?** Check permissions and role hierarchy\n• **Commands not working?** Try both `/command` and `!command`\n• **Missing logs?** Set up log channels with `/config logchannel`\n• **AutoMod issues?** Review settings with `/automod`",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Common Issues",
            value="• **Permission errors:** Bot needs appropriate permissions\n• **Role hierarchy:** Bot role must be above target roles\n• **Channel access:** Bot needs read/send message permissions\n• **Slash commands:** May take time to sync globally",
            inline=False
        )
        
        embed.add_field(
            name="📊 Diagnostic Commands",
            value="`/botinfo` - Check bot status and stats\n`/ping` - Test bot responsiveness\n`/config` - Review server configuration\n`/logs` - Check recent activity",
            inline=True
        )
        
        embed.add_field(
            name="📖 Resources",
            value="• Use `/help` for command documentation\n• Check `/config` for current settings\n• Review `/logs` for troubleshooting\n• Contact server administrators for issues",
            inline=True
        )
        
        embed.add_field(
            name="🏥 Emergency Commands",
            value="`/reset` - Reset all configuration (Admin only)\n`/setup` - Re-run initial setup\n`/sync` - Resync slash commands (Owner only)",
            inline=False
        )
        
        embed.set_footer(text="💡 Most issues can be resolved by checking permissions and configuration")
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))