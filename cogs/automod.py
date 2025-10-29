import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque
import aiohttp
from utils.database import DB

class AutoModeration(commands.Cog):
    """Automatic moderation system (DB-backed settings)"""
    
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = defaultdict(lambda: deque(maxlen=10))
        self.violation_counts = defaultdict(int)
        self.invite_pattern = re.compile(r'discord\.gg/[a-zA-Z0-9]+|discordapp\.com/invite/[a-zA-Z0-9]+')
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.bad_words = {
            'mild': ['damn', 'hell', 'crap'],
            'moderate': ['shit', 'fuck', 'bitch', 'ass'],
            'severe': ['nigger', 'faggot', 'retard', 'cunt']
        }
        self.allowed_domains = {'youtube.com','youtu.be','twitter.com','github.com','reddit.com','stackoverflow.com','discord.com'}
    
    async def get_automod_config(self, guild_id):
        settings = await DB.get_automod_settings(guild_id)
        def b(x, default):
            if x is None:
                return default
            return bool(int(x)) if isinstance(x, (int, str)) else bool(x)
        cfg = {
            'auto_dehoist': b(settings.get('auto_dehoist'), True),
            'auto_delete_invites': b(settings.get('auto_delete_invites'), False),
            'spam_detection': b(settings.get('spam_detection'), True),
            'raid_protection': b(settings.get('raid_protection'), True),
            'max_mentions': int(settings.get('max_mentions') or 5),
            'max_emoji': int(settings.get('max_emoji') or 10),
            'profanity_filter': b(settings.get('profanity_filter'), True),
            'link_filter': b(settings.get('link_filter'), False),
            'caps_filter': b(settings.get('caps_filter'), True),
            'repeated_text_filter': b(settings.get('repeated_text_filter'), True)
        }
        return cfg
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.author.guild_permissions.administrator:
            return
        config = await self.get_automod_config(message.guild.id)
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
        await self.check_mentions(message, config)
        await self.check_emoji_spam(message, config)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = await self.get_automod_config(member.guild.id)
        if config.get('raid_protection', True):
            await self.check_raid_protection(member)
        if config.get('auto_dehoist', True):
            await self.auto_dehoist(member)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.display_name != after.display_name:
            config = await self.get_automod_config(after.guild.id)
            if config.get('auto_dehoist', True):
                await self.auto_dehoist(after)
    
    async def check_spam(self, message):
        user_id = message.author.id
        now = datetime.utcnow()
        self.message_cache[user_id].append({'content': message.content,'timestamp': now,'channel': message.channel.id})
        recent_messages = list(self.message_cache[user_id])
        identical_count = sum(1 for msg in recent_messages if msg['content'] == message.content)
        if identical_count >= 3:
            await self.handle_violation(message, "Spam: Identical messages", "spam")
            return True
        recent_in_channel = [msg for msg in recent_messages if msg['channel'] == message.channel.id and (now - msg['timestamp']).seconds < 5]
        if len(recent_in_channel) >= 5:
            await self.handle_violation(message, "Spam: Rapid messaging", "spam")
            return True
        return False
    
    async def check_invites(self, message):
        if self.invite_pattern.search(message.content):
            try:
                invite_match = self.invite_pattern.search(message.content)
                if invite_match:
                    invite_code = invite_match.group().split('/')[-1]
                    try:
                        invite = await self.bot.fetch_invite(invite_code)
                        if invite.guild and invite.guild.id == message.guild.id:
                            return False
                    except discord.NotFound:
                        pass
            except Exception:
                pass
            await self.handle_violation(message, "Unauthorized Discord invite", "invite")
            return True
        return False
    
    async def check_profanity(self, message):
        content_lower = message.content.lower()
        for severity, words in self.bad_words.items():
            for word in words:
                if word in content_lower:
                    await self.handle_violation(message, f"Profanity detected: {severity} level", f"profanity_{severity}")
                    return True
        return False
    
    async def check_links(self, message):
        urls = self.url_pattern.findall(message.content)
        for url in urls:
            try:
                domain = url.split('/')[2].lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                if domain not in self.allowed_domains:
                    await self.handle_violation(message, f"Unauthorized link: {domain}", "link")
                    return True
            except IndexError:
                continue
        return False
    
    async def check_caps(self, message):
        if len(message.content) < 10:
            return False
        caps = sum(1 for c in message.content if c.isupper())
        ratio = caps / max(1, len(message.content))
        if ratio > 0.7:
            await self.handle_violation(message, "Excessive caps usage", "caps")
            return True
        return False
    
    async def check_repeated_text(self, message):
        content = message.content.lower()
        if re.search(r'(.)\1{5,}', content):
            await self.handle_violation(message, "Repeated characters", "repeated")
            return True
        words = content.split()
        if len(words) >= 3:
            for i in range(len(words) - 2):
                if words[i] == words[i+1] == words[i+2]:
                    await self.handle_violation(message, "Repeated words", "repeated")
                    return True
        return False
    
    async def check_mentions(self, message, config):
        max_mentions = config.get('max_mentions', 5)
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if total_mentions > max_mentions:
            await self.handle_violation(message, f"Excessive mentions: {total_mentions}/{max_mentions}", "mentions")
    
    async def check_emoji_spam(self, message, config):
        max_emoji = config.get('max_emoji', 10)
        custom_emoji_count = len(re.findall(r'<:[a-zA-Z0-9_]+:[0-9]+>', message.content))
        unicode_emoji_count = len(re.findall(r'[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]', message.content))
        total_emoji = custom_emoji_count + unicode_emoji_count
        if total_emoji > max_emoji:
            await self.handle_violation(message, f"Emoji spam: {total_emoji}/{max_emoji}", "emoji")
    
    async def check_raid_protection(self, member):
        guild = member.guild
        now = datetime.utcnow()
        recent_joins = [m for m in guild.members if m.joined_at and (now - m.joined_at).total_seconds() < 600]
        if len(recent_joins) > 10:
            for channel in guild.text_channels:
                if channel.slowmode_delay < 30:
                    try:
                        await channel.edit(slowmode_delay=30, reason="Raid protection")
                    except discord.Forbidden:
                        pass
            embed = discord.Embed(title="🚨 Potential Raid Detected", description=f"**{len(recent_joins)}** members joined in the last 10 minutes.", color=discord.Color.red())
            embed.add_field(name="Latest Member", value=member.mention, inline=True)
            embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
            embed.timestamp = now
            guild_config = self.bot.guild_configs.get(guild.id, {})
            log_channel_id = guild_config.get('log_channel')
            if log_channel_id:
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(embed=embed)
    
    async def auto_dehoist(self, member):
        if member.display_name and member.display_name[0] in '!@#$%^&*()_+-=[]{}|;:,.<>?':
            new_name = member.display_name.lstrip('!@#$%^&*()_+-=[]{}|;:,.<>?') or f"Dehoisted {member.name}"
            try:
                await member.edit(nick=new_name, reason="Auto-dehoist")
            except discord.Forbidden:
                pass
    
    async def handle_violation(self, message, reason, violation_type):
        user_id = message.author.id
        guild_id = message.guild.id
        self.violation_counts[f"{guild_id}_{user_id}"] += 1
        violation_count = self.violation_counts[f"{guild_id}_{user_id}"]
        try:
            await message.delete()
        except discord.NotFound:
            pass
        action_taken = None
        if violation_count >= 5:
            try:
                mute_role = await self.get_or_create_mute_role(message.guild)
                await message.author.add_roles(mute_role, reason=f"Automod: {reason}")
                action_taken = "Muted for 1 hour"
                await asyncio.sleep(3600)
                try:
                    await message.author.remove_roles(mute_role, reason="Automod mute expired")
                except discord.NotFound:
                    pass
            except discord.Forbidden:
                action_taken = "Could not mute (insufficient permissions)"
        elif violation_count >= 3:
            try:
                await message.author.timeout(timedelta(minutes=5), reason=f"Automod: {reason}")
                action_taken = "Timed out for 5 minutes"
            except discord.Forbidden:
                action_taken = "Could not timeout (insufficient permissions)"
        embed = discord.Embed(title="⚠️ AutoMod Violation", color=discord.Color.orange())
        embed.add_field(name="User", value=f"{message.author} ({message.author.id})", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Violation Count", value=str(violation_count), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        if action_taken:
            embed.add_field(name="Action Taken", value=action_taken, inline=False)
        embed.add_field(name="Message Content", value=f"```{message.content[:1000]}```", inline=False)
        embed.timestamp = datetime.utcnow()
        guild_config = self.bot.guild_configs.get(guild_id, {})
        log_channel_id = guild_config.get('log_channel')
        if log_channel_id:
            log_channel = message.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=embed)
    
    @commands.hybrid_command(name="automod", description="Configure automod settings (DB)")
    @app_commands.describe(setting="Setting key", value="Value (true/false or number)")
    @commands.has_permissions(administrator=True)
    async def automod_config(self, ctx, setting: str, value: str):
        valid = {'spam_detection': bool,'auto_delete_invites': bool,'profanity_filter': bool,'link_filter': bool,'caps_filter': bool,'repeated_text_filter': bool,'auto_dehoist': bool,'raid_protection': bool,'max_mentions': int,'max_emoji': int}
        if setting not in valid:
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Setting", description=f"Valid settings: {', '.join(valid.keys())}", color=discord.Color.red()))
        try:
            if valid[setting] == bool:
                parsed_value = 1 if value.lower() in ('true','1','yes','on','enable') else 0
            else:
                parsed_value = int(value)
                if parsed_value < 0:
                    raise ValueError("Value must be positive")
        except ValueError as e:
            return await ctx.send(embed=discord.Embed(title="❌ Invalid Value", description=str(e), color=discord.Color.red()))
        await DB.update_automod_settings(ctx.guild.id, **{setting: parsed_value})
        embed = discord.Embed(title="✅ AutoMod Setting Updated", color=discord.Color.green())
        embed.add_field(name="Setting", value=setting, inline=True)
        embed.add_field(name="Value", value=str(value), inline=True)
        embed.add_field(name="Updated by", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="violations", description="View automod violations for a user")
    @app_commands.describe(member="The member to check violations for")
    @commands.has_permissions(manage_messages=True)
    async def violations(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        violation_key = f"{ctx.guild.id}_{member.id}"
        violation_count = self.violation_counts.get(violation_key, 0)
        embed = discord.Embed(title=f"📊 AutoMod Violations for {member.display_name}", color=discord.Color.blue())
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
    @app_commands.describe(member="The member to clear violations for")
    @commands.has_permissions(administrator=True)
    async def clear_violations(self, ctx, member: discord.Member):
        violation_key = f"{ctx.guild.id}_{member.id}"
        old_count = self.violation_counts.get(violation_key, 0)
        self.violation_counts[violation_key] = 0
        embed = discord.Embed(title="✅ Violations Cleared", description=f"Cleared **{old_count}** violations for {member.mention}.", color=discord.Color.green())
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoModeration(bot))
