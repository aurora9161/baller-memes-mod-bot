import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque
import aiohttp

class AutoModeration(commands.Cog):
    """Automatic moderation system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = defaultdict(lambda: deque(maxlen=10))  # Track recent messages per user
        self.violation_counts = defaultdict(int)  # Track violations per user
        
        # Regex patterns
        self.invite_pattern = re.compile(r'discord\.gg/[a-zA-Z0-9]+|discordapp\.com/invite/[a-zA-Z0-9]+')
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # Default bad words list (you can expand this)
        self.bad_words = {
            'mild': ['damn', 'hell', 'crap'],
            'moderate': ['shit', 'fuck', 'bitch', 'ass'],
            'severe': ['nigger', 'faggot', 'retard', 'cunt']
        }
        
        # Allowed domains (whitelist)
        self.allowed_domains = {
            'youtube.com', 'youtu.be', 'twitter.com', 'github.com',
            'reddit.com', 'stackoverflow.com', 'discord.com'
        }
    
    def get_automod_config(self, guild_id):
        """Get automod configuration for a guild"""
        return self.bot.config.get('moderation', {
            'auto_dehoist': True,
            'auto_delete_invites': False,
            'spam_detection': True,
            'raid_protection': True,
            'max_mentions': 5,
            'max_emoji': 10,
            'slowmode_threshold': 5,
            'profanity_filter': True,
            'link_filter': False,
            'caps_filter': True,
            'repeated_text_filter': True
        })
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Main automod message handler"""
        if message.author.bot or not message.guild:
            return
        
        # Skip if user has admin permissions
        if message.author.guild_permissions.administrator:
            return
        
        config = self.get_automod_config(message.guild.id)
        
        # Check various automod rules
        if config.get('spam_detection', True):
            if await self.check_spam(message):
                return
        
        if config.get('auto_delete_invites', False):
            if await self.check_invites(message):
                return
        
        if config.get('profanity_filter', True):
            if await self.check_profanity(message):
                return
        
        if config.get('link_filter', False):
            if await self.check_links(message):
                return
        
        if config.get('caps_filter', True):
            if await self.check_caps(message):
                return
        
        if config.get('repeated_text_filter', True):
            if await self.check_repeated_text(message):
                return
        
        await self.check_mentions(message)
        await self.check_emoji_spam(message)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join events for raid protection"""
        config = self.get_automod_config(member.guild.id)
        
        if config.get('raid_protection', True):
            await self.check_raid_protection(member)
        
        if config.get('auto_dehoist', True):
            await self.auto_dehoist(member)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Handle member updates for auto-dehoist"""
        if before.display_name != after.display_name:
            config = self.get_automod_config(after.guild.id)
            if config.get('auto_dehoist', True):
                await self.auto_dehoist(after)
    
    async def check_spam(self, message):
        """Check for spam patterns"""
        user_id = message.author.id
        now = datetime.utcnow()
        
        # Add message to cache
        self.message_cache[user_id].append({
            'content': message.content,
            'timestamp': now,
            'channel': message.channel.id
        })
        
        recent_messages = list(self.message_cache[user_id])
        
        # Check for identical messages
        identical_count = sum(1 for msg in recent_messages if msg['content'] == message.content)
        if identical_count >= 3:
            await self.handle_violation(message, "Spam: Identical messages", "spam")
            return True
        
        # Check for rapid messaging
        recent_in_channel = [msg for msg in recent_messages 
                           if msg['channel'] == message.channel.id 
                           and (now - msg['timestamp']).seconds < 5]
        
        if len(recent_in_channel) >= 5:
            await self.handle_violation(message, "Spam: Rapid messaging", "spam")
            return True
        
        return False
    
    async def check_invites(self, message):
        """Check for Discord invites"""
        if self.invite_pattern.search(message.content):
            # Check if it's an invite to the same server
            try:
                invite_match = self.invite_pattern.search(message.content)
                if invite_match:
                    invite_code = invite_match.group().split('/')[-1]
                    try:
                        invite = await self.bot.fetch_invite(invite_code)
                        if invite.guild.id == message.guild.id:
                            return False  # Allow invites to same server
                    except discord.NotFound:
                        pass  # Invalid invite, delete it
            except Exception:
                pass
            
            await self.handle_violation(message, "Unauthorized Discord invite", "invite")
            return True
        
        return False
    
    async def check_profanity(self, message):
        """Check for profanity"""
        content_lower = message.content.lower()
        
        # Check against bad words
        for severity, words in self.bad_words.items():
            for word in words:
                if word in content_lower:
                    await self.handle_violation(
                        message, 
                        f"Profanity detected: {severity} level", 
                        f"profanity_{severity}"
                    )
                    return True
        
        return False
    
    async def check_links(self, message):
        """Check for unauthorized links"""
        urls = self.url_pattern.findall(message.content)
        
        for url in urls:
            # Extract domain
            try:
                domain = url.split('/')[2].lower()
                # Remove www. prefix
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                if domain not in self.allowed_domains:
                    await self.handle_violation(message, f"Unauthorized link: {domain}", "link")
                    return True
            except IndexError:
                continue
        
        return False
    
    async def check_caps(self, message):
        """Check for excessive caps"""
        if len(message.content) < 10:  # Skip short messages
            return False
        
        caps_ratio = sum(1 for c in message.content if c.isupper()) / len(message.content)
        
        if caps_ratio > 0.7:  # More than 70% caps
            await self.handle_violation(message, "Excessive caps usage", "caps")
            return True
        
        return False
    
    async def check_repeated_text(self, message):
        """Check for repeated text patterns"""
        content = message.content.lower()
        
        # Check for repeated characters (like "aaaaaa")
        if re.search(r'(.)\1{5,}', content):  # 6 or more repeated characters
            await self.handle_violation(message, "Repeated characters", "repeated")
            return True
        
        # Check for repeated words
        words = content.split()
        if len(words) >= 3:
            for i in range(len(words) - 2):
                if words[i] == words[i + 1] == words[i + 2]:  # 3 identical words in a row
                    await self.handle_violation(message, "Repeated words", "repeated")
                    return True
        
        return False
    
    async def check_mentions(self, message):
        """Check for excessive mentions"""
        config = self.get_automod_config(message.guild.id)
        max_mentions = config.get('max_mentions', 5)
        
        total_mentions = len(message.mentions) + len(message.role_mentions)
        
        if total_mentions > max_mentions:
            await self.handle_violation(
                message, 
                f"Excessive mentions: {total_mentions}/{max_mentions}", 
                "mentions"
            )
    
    async def check_emoji_spam(self, message):
        """Check for emoji spam"""
        config = self.get_automod_config(message.guild.id)
        max_emoji = config.get('max_emoji', 10)
        
        # Count custom emojis
        custom_emoji_count = len(re.findall(r'<:[a-zA-Z0-9_]+:[0-9]+>', message.content))
        
        # Count unicode emojis (basic check)
        unicode_emoji_count = len(re.findall(r'[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]', message.content))
        
        total_emoji = custom_emoji_count + unicode_emoji_count
        
        if total_emoji > max_emoji:
            await self.handle_violation(
                message, 
                f"Emoji spam: {total_emoji}/{max_emoji}", 
                "emoji"
            )
    
    async def check_raid_protection(self, member):
        """Check for potential raids"""
        guild = member.guild
        now = datetime.utcnow()
        
        # Count recent joins (last 10 minutes)
        recent_joins = [m for m in guild.members 
                       if m.joined_at and (now - m.joined_at).total_seconds() < 600]
        
        if len(recent_joins) > 10:  # More than 10 joins in 10 minutes
            # Enable slowmode on all text channels
            for channel in guild.text_channels:
                if channel.slowmode_delay < 30:  # Only if not already high
                    try:
                        await channel.edit(slowmode_delay=30, reason="Raid protection")
                    except discord.Forbidden:
                        pass
            
            # Log the potential raid
            embed = discord.Embed(
                title="🚨 Potential Raid Detected",
                description=f"**{len(recent_joins)}** members joined in the last 10 minutes.",
                color=discord.Color.red()
            )
            embed.add_field(name="Latest Member", value=member.mention, inline=True)
            embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
            embed.timestamp = now
            
            # Try to send to log channel
            guild_config = self.bot.guild_configs.get(guild.id, {})
            log_channel_id = guild_config.get('log_channel')
            if log_channel_id:
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(embed=embed)
    
    async def auto_dehoist(self, member):
        """Automatically dehoist members (remove special characters from start of name)"""
        if member.display_name[0] in '!@#$%^&*()_+-=[]{}|;:,.<>?':
            new_name = member.display_name.lstrip('!@#$%^&*()_+-=[]{}|;:,.<>?')
            if not new_name:  # If name becomes empty
                new_name = f"Dehoisted {member.name}"
            
            try:
                await member.edit(nick=new_name, reason="Auto-dehoist")
            except discord.Forbidden:
                pass
    
    async def handle_violation(self, message, reason, violation_type):
        """Handle automod violations"""
        user_id = message.author.id
        guild_id = message.guild.id
        
        # Increment violation count
        self.violation_counts[f"{guild_id}_{user_id}"] += 1
        violation_count = self.violation_counts[f"{guild_id}_{user_id}"]
        
        # Delete the message
        try:
            await message.delete()
        except discord.NotFound:
            pass
        
        # Determine action based on violation count
        action_taken = None
        
        if violation_count >= 5:
            # Mute for 1 hour
            try:
                mute_role = await self.get_or_create_mute_role(message.guild)
                await message.author.add_roles(mute_role, reason=f"Automod: {reason}")
                action_taken = "Muted for 1 hour"
                
                # Schedule unmute
                await asyncio.sleep(3600)  # 1 hour
                try:
                    await message.author.remove_roles(mute_role, reason="Automod mute expired")
                except discord.NotFound:
                    pass
            except discord.Forbidden:
                action_taken = "Could not mute (insufficient permissions)"
        
        elif violation_count >= 3:
            # Warning + timeout
            try:
                await message.author.timeout(timedelta(minutes=5), reason=f"Automod: {reason}")
                action_taken = "Timed out for 5 minutes"
            except discord.Forbidden:
                action_taken = "Could not timeout (insufficient permissions)"
        
        # Create violation embed
        embed = discord.Embed(
            title="⚠️ AutoMod Violation",
            color=discord.Color.orange()
        )
        embed.add_field(name="User", value=f"{message.author} ({message.author.id})", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Violation Count", value=str(violation_count), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if action_taken:
            embed.add_field(name="Action Taken", value=action_taken, inline=False)
        
        embed.add_field(name="Message Content", value=f"```{message.content[:1000]}```", inline=False)
        embed.timestamp = datetime.utcnow()
        
        # Send to log channel
        guild_config = self.bot.guild_configs.get(guild_id, {})
        log_channel_id = guild_config.get('log_channel')
        if log_channel_id:
            log_channel = message.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=embed)
        
        # DM the user (if it's their first few violations)
        if violation_count <= 2:
            try:
                dm_embed = discord.Embed(
                    title="⚠️ Message Removed",
                    description=f"Your message in **{message.guild.name}** was removed by AutoMod.",
                    color=discord.Color.orange()
                )
                dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.add_field(name="Channel", value=f"#{message.channel.name}", inline=True)
                dm_embed.add_field(name="Violation #", value=str(violation_count), inline=True)
                
                if violation_count == 2:
                    dm_embed.add_field(
                        name="⚠️ Warning", 
                        value="Further violations may result in temporary mute or other penalties.", 
                        inline=False
                    )
                
                await message.author.send(embed=dm_embed)
            except discord.Forbidden:
                pass
    
    async def get_or_create_mute_role(self, guild):
        """Get or create mute role (reuse from moderation cog logic)"""
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
            reason="Auto-created mute role for AutoMod"
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
    
    @commands.hybrid_command(name="automod", description="Configure automod settings")
    @app_commands.describe(
        setting="The setting to configure",
        value="The value to set (true/false or number)"
    )
    @commands.has_permissions(administrator=True)
    async def automod_config(self, ctx, setting: str, value: str):
        """Configure automod settings"""
        valid_settings = {
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
        
        if setting not in valid_settings:
            embed = discord.Embed(
                title="❌ Invalid Setting",
                description=f"Valid settings: {', '.join(valid_settings.keys())}",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Parse value
        try:
            if valid_settings[setting] == bool:
                parsed_value = value.lower() in ('true', '1', 'yes', 'on', 'enable')
            elif valid_settings[setting] == int:
                parsed_value = int(value)
                if parsed_value < 0:
                    raise ValueError("Value must be positive")
            else:
                parsed_value = value
        except ValueError as e:
            embed = discord.Embed(
                title="❌ Invalid Value",
                description=f"Could not parse value: {e}",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Update config
        if 'moderation' not in self.bot.config:
            self.bot.config['moderation'] = {}
        
        self.bot.config['moderation'][setting] = parsed_value
        
        # Save config
        try:
            with open('config.json', 'w') as f:
                import json
                json.dump(self.bot.config, f, indent=4)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Save Error",
                description=f"Could not save config: {e}",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        embed = discord.Embed(
            title="✅ AutoMod Setting Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Setting", value=setting, inline=True)
        embed.add_field(name="Value", value=str(parsed_value), inline=True)
        embed.add_field(name="Updated by", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="violations", description="View automod violations for a user")
    @app_commands.describe(
        member="The member to check violations for"
    )
    @commands.has_permissions(manage_messages=True)
    async def violations(self, ctx, member: discord.Member = None):
        """View automod violations for a user"""
        if not member:
            member = ctx.author
        
        violation_key = f"{ctx.guild.id}_{member.id}"
        violation_count = self.violation_counts.get(violation_key, 0)
        
        embed = discord.Embed(
            title=f"📊 AutoMod Violations for {member.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Total Violations", value=str(violation_count), inline=True)
        embed.add_field(name="Member", value=member.mention, inline=True)
        
        if violation_count == 0:
            embed.description = "This member has no automod violations. 🎉"
            embed.color = discord.Color.green()
        elif violation_count < 3:
            embed.description = "This member has minimal violations."
            embed.color = discord.Color.yellow()
        else:
            embed.description = "This member has multiple violations and may need attention."
            embed.color = discord.Color.red()
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="clearviolations", description="Clear automod violations for a user")
    @app_commands.describe(
        member="The member to clear violations for"
    )
    @commands.has_permissions(administrator=True)
    async def clear_violations(self, ctx, member: discord.Member):
        """Clear automod violations for a user"""
        violation_key = f"{ctx.guild.id}_{member.id}"
        old_count = self.violation_counts.get(violation_key, 0)
        self.violation_counts[violation_key] = 0
        
        embed = discord.Embed(
            title="✅ Violations Cleared",
            description=f"Cleared **{old_count}** violations for {member.mention}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoModeration(bot))