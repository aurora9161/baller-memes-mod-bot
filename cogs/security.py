import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import asyncio
import hashlib
import re
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set
import json

class SecuritySystem(commands.Cog):
    """Enterprise-level security and threat detection system"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Security monitoring data
        self.threat_indicators = defaultdict(lambda: {
            'suspicious_activity': deque(maxlen=50),
            'failed_attempts': defaultdict(int),
            'reputation_score': 100,  # 0-100 scale
            'trust_level': 'unknown',  # unknown, trusted, suspicious, blacklisted
            'last_violation': None,
            'violation_count': 0,
            'ip_hash': None
        })
        
        # Guild security settings
        self.security_config = defaultdict(lambda: {
            'lockdown_mode': False,
            'raid_protection_level': 'medium',  # low, medium, high, maximum
            'account_age_requirement': 7,  # days
            'verification_level': 'medium',
            'suspicious_activity_threshold': 5,
            'auto_quarantine': True,
            'security_alerts': True,
            'whitelist_enabled': False,
            'whitelist_users': set(),
            'trusted_domains': set(),
            'blocked_domains': set()
        })
        
        # Known threat patterns
        self.threat_patterns = {
            'discord_token': re.compile(r'[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27}'),
            'webhook_url': re.compile(r'https://discord(?:app)?\.com/api/webhooks/\d+/[\w-]+'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'suspicious_links': re.compile(r'(?:bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly)/\w+'),
            'crypto_scam': re.compile(r'(?:free|claim).*(?:bitcoin|eth|crypto|nft)', re.IGNORECASE),
            'phishing': re.compile(r'(?:discord|nitro|steam).*(?:free|gift|giveaway)', re.IGNORECASE)
        }
        
        # Security monitoring task
        self.security_task = None
        self.lockdown_tasks = {}
    
    async def cog_load(self):
        """Start security monitoring when cog loads"""
        self.security_task = asyncio.create_task(self.security_monitor())
    
    async def cog_unload(self):
        """Stop security monitoring when cog unloads"""
        if self.security_task:
            self.security_task.cancel()
        
        # Cancel any active lockdown tasks
        for task in self.lockdown_tasks.values():
            if not task.done():
                task.cancel()
    
    async def security_monitor(self):
        """Background security monitoring task"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Analyze threat indicators
                await self.analyze_threats()
                
                # Update reputation scores
                await self.update_reputation_scores()
                
                # Check for automated responses
                await self.check_automated_responses()
                
            except Exception as e:
                print(f"Security monitor error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Advanced member join security checks"""
        guild_config = self.security_config[member.guild.id]
        
        # Account age check
        account_age = (datetime.utcnow() - member.created_at).days
        if account_age < guild_config['account_age_requirement']:
            await self.flag_suspicious_activity(
                member, 
                f"New account (created {account_age} days ago)",
                severity="medium"
            )
        
        # Check against known patterns
        await self.check_member_patterns(member)
        
        # Raid protection
        if guild_config['raid_protection_level'] != 'low':
            await self.check_raid_activity(member)
        
        # Auto-quarantine if needed
        if guild_config['auto_quarantine'] and self.is_suspicious_member(member):
            await self.quarantine_member(member, "Automatic security quarantine")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Advanced message security analysis"""
        if message.author.bot or not message.guild:
            return
        
        # Check threat patterns
        await self.analyze_message_threats(message)
        
        # Monitor for suspicious behavior
        await self.monitor_user_behavior(message)
        
        # Check links and attachments
        await self.scan_message_content(message)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Monitor message edits for threat indicators"""
        if after.author.bot or not after.guild:
            return
        
        # Check if edit introduces threats
        if before.content != after.content:
            await self.analyze_message_threats(after, is_edit=True)
    
    async def flag_suspicious_activity(self, user, reason: str, severity: str = "low"):
        """Flag suspicious activity for a user"""
        user_data = self.threat_indicators[user.id]
        
        activity_record = {
            'timestamp': datetime.utcnow(),
            'reason': reason,
            'severity': severity,
            'guild_id': user.guild.id if hasattr(user, 'guild') else None
        }
        
        user_data['suspicious_activity'].append(activity_record)
        user_data['violation_count'] += 1
        user_data['last_violation'] = datetime.utcnow()
        
        # Adjust reputation score
        score_reduction = {'low': 5, 'medium': 15, 'high': 30, 'critical': 50}
        user_data['reputation_score'] = max(0, user_data['reputation_score'] - score_reduction.get(severity, 10))
        
        # Update trust level
        self.update_trust_level(user.id)
        
        # Send security alert if enabled
        if hasattr(user, 'guild'):
            await self.send_security_alert(user.guild, user, reason, severity)
    
    def update_trust_level(self, user_id: int):
        """Update user trust level based on reputation score"""
        user_data = self.threat_indicators[user_id]
        score = user_data['reputation_score']
        
        if score >= 80:
            user_data['trust_level'] = 'trusted'
        elif score >= 50:
            user_data['trust_level'] = 'neutral'
        elif score >= 20:
            user_data['trust_level'] = 'suspicious'
        else:
            user_data['trust_level'] = 'high_risk'
    
    async def check_member_patterns(self, member):
        """Check new member against known threat patterns"""
        # Username analysis
        suspicious_patterns = [
            r'[a-zA-Z]+\d{4,}$',  # Username ending with many numbers
            r'^[a-zA-Z]{1,3}\d{10,}$',  # Very short name with many numbers
            r'discord|admin|mod|owner',  # Impersonation attempts
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, member.name.lower()):
                await self.flag_suspicious_activity(
                    member,
                    f"Suspicious username pattern: {member.name}",
                    "medium"
                )
                break
        
        # Profile picture analysis
        if member.avatar is None:
            await self.flag_suspicious_activity(
                member,
                "No profile picture (default avatar)",
                "low"
            )
    
    async def check_raid_activity(self, member):
        """Check for potential raid activity"""
        guild = member.guild
        now = datetime.utcnow()
        
        # Count recent joins
        recent_joins = [m for m in guild.members 
                       if m.joined_at and (now - m.joined_at).total_seconds() < 300]  # 5 minutes
        
        guild_config = self.security_config[guild.id]
        
        # Determine thresholds based on protection level
        thresholds = {
            'low': 15,
            'medium': 10,
            'high': 7,
            'maximum': 5
        }
        
        threshold = thresholds.get(guild_config['raid_protection_level'], 10)
        
        if len(recent_joins) > threshold:
            # Potential raid detected
            await self.initiate_lockdown(guild, "Potential raid detected", duration=1800)  # 30 minutes
            
            # Flag all recent joiners
            for recent_member in recent_joins[-threshold:]:  # Last N members
                await self.flag_suspicious_activity(
                    recent_member,
                    "Joined during suspected raid",
                    "high"
                )
    
    async def analyze_message_threats(self, message, is_edit: bool = False):
        """Analyze message for security threats"""
        content = message.content.lower()
        threats_found = []
        
        # Check against threat patterns
        for threat_type, pattern in self.threat_patterns.items():
            if pattern.search(content):
                threats_found.append(threat_type)
        
        if threats_found:
            severity = "critical" if any(t in ['discord_token', 'webhook_url'] for t in threats_found) else "high"
            
            await self.flag_suspicious_activity(
                message.author,
                f"Message contains threats: {', '.join(threats_found)}",
                severity
            )
            
            # Auto-delete critical threats
            if severity == "critical":
                try:
                    await message.delete()
                    await self.quarantine_member(message.author, "Critical security threat detected")
                except discord.Forbidden:
                    pass
    
    async def monitor_user_behavior(self, message):
        """Monitor user behavior patterns"""
        user_data = self.threat_indicators[message.author.id]
        
        # Track message frequency
        now = datetime.utcnow()
        recent_messages = [activity for activity in user_data['suspicious_activity'] 
                          if (now - activity['timestamp']).total_seconds() < 300]  # 5 minutes
        
        # Check for spam-like behavior
        if len(recent_messages) > 10:
            await self.flag_suspicious_activity(
                message.author,
                "High message frequency detected",
                "medium"
            )
    
    async def scan_message_content(self, message):
        """Scan message content for threats"""
        # Check URLs
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
        
        guild_config = self.security_config[message.guild.id]
        
        for url in urls:
            domain = self.extract_domain(url)
            
            # Check against blocked domains
            if domain in guild_config['blocked_domains']:
                await self.flag_suspicious_activity(
                    message.author,
                    f"Posted blocked domain: {domain}",
                    "high"
                )
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
        
        # Check attachments
        for attachment in message.attachments:
            if await self.is_suspicious_file(attachment):
                await self.flag_suspicious_activity(
                    message.author,
                    f"Suspicious file attachment: {attachment.filename}",
                    "medium"
                )
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.lower()
        except:
            return url
    
    async def is_suspicious_file(self, attachment) -> bool:
        """Check if file attachment is suspicious"""
        suspicious_extensions = ['.exe', '.scr', '.bat', '.cmd', '.com', '.pif', '.vbs', '.js']
        return any(attachment.filename.lower().endswith(ext) for ext in suspicious_extensions)
    
    def is_suspicious_member(self, member) -> bool:
        """Check if member should be considered suspicious"""
        user_data = self.threat_indicators[member.id]
        return (
            user_data['reputation_score'] < 30 or
            user_data['trust_level'] in ['suspicious', 'high_risk'] or
            user_data['violation_count'] >= 3
        )
    
    async def quarantine_member(self, member, reason: str):
        """Quarantine a suspicious member"""
        try:
            # Create or get quarantine role
            quarantine_role = discord.utils.get(member.guild.roles, name="Quarantined")
            
            if not quarantine_role:
                quarantine_role = await member.guild.create_role(
                    name="Quarantined",
                    color=discord.Color.dark_red(),
                    permissions=discord.Permissions(read_messages=True),
                    reason="Security quarantine role"
                )
                
                # Set permissions for all channels
                for channel in member.guild.channels:
                    if isinstance(channel, discord.TextChannel):
                        await channel.set_permissions(
                            quarantine_role,
                            send_messages=False,
                            add_reactions=False,
                            speak=False
                        )
            
            await member.add_roles(quarantine_role, reason=reason)
            
            # Log quarantine action
            await self.log_security_action(member.guild, "quarantine", member, reason)
            
        except discord.Forbidden:
            pass
    
    async def initiate_lockdown(self, guild, reason: str, duration: int = 3600):
        """Initiate server lockdown"""
        guild_config = self.security_config[guild.id]
        
        if guild_config['lockdown_mode']:
            return  # Already in lockdown
        
        guild_config['lockdown_mode'] = True
        
        # Restrict permissions
        everyone_role = guild.default_role
        try:
            await everyone_role.edit(
                permissions=everyone_role.permissions.update(send_messages=False),
                reason=f"Security lockdown: {reason}"
            )
        except discord.Forbidden:
            pass
        
        # Log lockdown
        await self.log_security_action(guild, "lockdown_initiated", None, reason)
        
        # Schedule lockdown end
        self.lockdown_tasks[guild.id] = asyncio.create_task(
            self.schedule_lockdown_end(guild, duration)
        )
    
    async def schedule_lockdown_end(self, guild, duration: int):
        """Schedule the end of lockdown"""
        await asyncio.sleep(duration)
        await self.end_lockdown(guild, "Automatic lockdown expiry")
    
    async def end_lockdown(self, guild, reason: str):
        """End server lockdown"""
        guild_config = self.security_config[guild.id]
        guild_config['lockdown_mode'] = False
        
        # Restore permissions
        everyone_role = guild.default_role
        try:
            await everyone_role.edit(
                permissions=everyone_role.permissions.update(send_messages=True),
                reason=f"Lockdown ended: {reason}"
            )
        except discord.Forbidden:
            pass
        
        # Log lockdown end
        await self.log_security_action(guild, "lockdown_ended", None, reason)
        
        # Clean up task
        if guild.id in self.lockdown_tasks:
            del self.lockdown_tasks[guild.id]
    
    async def send_security_alert(self, guild, user, reason: str, severity: str):
        """Send security alert to designated channel"""
        guild_config = self.bot.guild_configs.get(guild.id, {})
        
        if not self.security_config[guild.id]['security_alerts']:
            return
        
        log_channel_id = guild_config.get('log_channel') or guild_config.get('mod_log_channel')
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        color_map = {
            'low': discord.Color.yellow(),
            'medium': discord.Color.orange(),
            'high': discord.Color.red(),
            'critical': discord.Color.dark_red()
        }
        
        embed = discord.Embed(
            title=f"🚨 Security Alert - {severity.title()}",
            color=color_map.get(severity, discord.Color.red())
        )
        
        embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Severity", value=severity.title(), inline=True)
        
        user_data = self.threat_indicators[user.id]
        embed.add_field(name="Reputation Score", value=f"{user_data['reputation_score']}/100", inline=True)
        embed.add_field(name="Trust Level", value=user_data['trust_level'].title(), inline=True)
        embed.add_field(name="Total Violations", value=str(user_data['violation_count']), inline=True)
        
        embed.timestamp = datetime.utcnow()
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    async def log_security_action(self, guild, action: str, target_user, reason: str):
        """Log security actions"""
        guild_config = self.bot.guild_configs.get(guild.id, {})
        log_channel_id = guild_config.get('log_channel') or guild_config.get('mod_log_channel')
        
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title=f"🔒 Security Action - {action.replace('_', ' ').title()}",
            color=discord.Color.blue()
        )
        
        if target_user:
            embed.add_field(name="Target", value=f"{target_user} ({target_user.id})", inline=True)
        
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.timestamp = datetime.utcnow()
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass
    
    async def analyze_threats(self):
        """Analyze accumulated threat data"""
        for user_id, data in self.threat_indicators.items():
            # Decay reputation over time (gradual recovery)
            if data['last_violation']:
                days_since_violation = (datetime.utcnow() - data['last_violation']).days
                if days_since_violation > 7:  # Recovery after a week
                    recovery_rate = min(5, days_since_violation - 7)
                    data['reputation_score'] = min(100, data['reputation_score'] + recovery_rate)
                    self.update_trust_level(user_id)
    
    async def update_reputation_scores(self):
        """Update reputation scores based on recent activity"""
        # This is handled in analyze_threats for now
        pass
    
    async def check_automated_responses(self):
        """Check if automated security responses are needed"""
        # This could include automatic bans, alerts to admins, etc.
        pass
    
    @commands.hybrid_command(name="security", description="View security dashboard")
    @commands.has_permissions(administrator=True)
    async def security_dashboard(self, ctx, user: discord.Member = None):
        """Show security dashboard"""
        if user:
            await self._show_user_security(ctx, user)
        else:
            await self._show_guild_security(ctx)
    
    async def _show_guild_security(self, ctx):
        """Show guild security overview"""
        guild_config = self.security_config[ctx.guild.id]
        
        embed = discord.Embed(
            title=f"🔒 Security Dashboard - {ctx.guild.name}",
            description="Server security status and configuration",
            color=discord.Color.blue()
        )
        
        # Security status
        status = "🔴 LOCKDOWN" if guild_config['lockdown_mode'] else "🟢 OPERATIONAL"
        embed.add_field(name="Status", value=status, inline=True)
        
        # Protection level
        embed.add_field(name="Protection Level", value=guild_config['raid_protection_level'].title(), inline=True)
        
        # Account age requirement
        embed.add_field(name="Min Account Age", value=f"{guild_config['account_age_requirement']} days", inline=True)
        
        # Threat statistics
        total_threats = sum(len(data['suspicious_activity']) for data in self.threat_indicators.values())
        high_risk_users = sum(1 for data in self.threat_indicators.values() if data['trust_level'] == 'high_risk')
        
        embed.add_field(name="Total Threats Detected", value=str(total_threats), inline=True)
        embed.add_field(name="High Risk Users", value=str(high_risk_users), inline=True)
        embed.add_field(name="Auto-Quarantine", value="✅ Enabled" if guild_config['auto_quarantine'] else "❌ Disabled", inline=True)
        
        # Recent activity
        recent_threats = []
        for user_id, data in self.threat_indicators.items():
            if data['suspicious_activity']:
                recent = data['suspicious_activity'][-1]
                if (datetime.utcnow() - recent['timestamp']).days < 7:
                    user = ctx.guild.get_member(user_id)
                    if user:
                        recent_threats.append(f"{user.display_name}: {recent['reason']}")
        
        if recent_threats:
            embed.add_field(
                name="Recent Threats (7 days)",
                value="\n".join(recent_threats[:5]) + ("\n..." if len(recent_threats) > 5 else ""),
                inline=False
            )
        
        embed.set_footer(text="Use /security @user for individual user analysis")
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    async def _show_user_security(self, ctx, user: discord.Member):
        """Show individual user security analysis"""
        user_data = self.threat_indicators[user.id]
        
        embed = discord.Embed(
            title=f"🔍 Security Analysis - {user.display_name}",
            color=self._get_threat_color(user_data['trust_level'])
        )
        
        embed.add_field(name="Reputation Score", value=f"{user_data['reputation_score']}/100", inline=True)
        embed.add_field(name="Trust Level", value=user_data['trust_level'].title(), inline=True)
        embed.add_field(name="Total Violations", value=str(user_data['violation_count']), inline=True)
        
        # Account information
        account_age = (datetime.utcnow() - user.created_at).days
        join_age = (datetime.utcnow() - user.joined_at).days if user.joined_at else "Unknown"
        
        embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
        embed.add_field(name="Time in Server", value=f"{join_age} days" if isinstance(join_age, int) else join_age, inline=True)
        
        # Recent activity
        if user_data['suspicious_activity']:
            recent_activity = list(user_data['suspicious_activity'])[-5:]
            activity_text = "\n".join([
                f"• {activity['reason']} ({activity['severity']})"
                for activity in recent_activity
            ])
            embed.add_field(name="Recent Violations", value=activity_text, inline=False)
        
        # Risk assessment
        risk_factors = []
        if account_age < 7:
            risk_factors.append("New account")
        if user_data['reputation_score'] < 50:
            risk_factors.append("Low reputation")
        if user_data['violation_count'] > 3:
            risk_factors.append("Multiple violations")
        
        if risk_factors:
            embed.add_field(name="Risk Factors", value="\n".join([f"⚠️ {factor}" for factor in risk_factors]), inline=False)
        else:
            embed.add_field(name="Risk Assessment", value="✅ Low risk profile", inline=False)
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    def _get_threat_color(self, trust_level: str) -> discord.Color:
        """Get color based on threat level"""
        colors = {
            'trusted': discord.Color.green(),
            'neutral': discord.Color.blue(),
            'unknown': discord.Color.greyple(),
            'suspicious': discord.Color.orange(),
            'high_risk': discord.Color.red()
        }
        return colors.get(trust_level, discord.Color.greyple())
    
    @commands.hybrid_command(name="lockdown", description="Initiate or end server lockdown")
    @app_commands.describe(
        action="Action to perform (start/end)",
        duration="Lockdown duration in minutes",
        reason="Reason for lockdown"
    )
    @commands.has_permissions(administrator=True)
    async def lockdown_command(self, ctx, action: str, duration: int = 60, *, reason: str = "Manual lockdown"):
        """Manual lockdown control"""
        if action.lower() == "start":
            await self.initiate_lockdown(ctx.guild, reason, duration * 60)
            embed = discord.Embed(
                title="🔒 Lockdown Initiated",
                description=f"Server locked down for {duration} minutes\nReason: {reason}",
                color=discord.Color.red()
            )
        elif action.lower() == "end":
            await self.end_lockdown(ctx.guild, reason)
            embed = discord.Embed(
                title="🔓 Lockdown Ended",
                description=f"Server lockdown lifted\nReason: {reason}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Invalid Action",
                description="Use 'start' or 'end'",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="quarantine", description="Quarantine or unquarantine a member")
    @app_commands.describe(
        member="Member to quarantine/unquarantine",
        action="Action to perform (add/remove)",
        reason="Reason for action"
    )
    @commands.has_permissions(manage_roles=True)
    async def quarantine_command(self, ctx, member: discord.Member, action: str, *, reason: str = "Manual quarantine"):
        """Manual quarantine control"""
        if action.lower() == "add":
            await self.quarantine_member(member, reason)
            embed = discord.Embed(
                title="🚨 Member Quarantined",
                description=f"{member.mention} has been quarantined\nReason: {reason}",
                color=discord.Color.red()
            )
        elif action.lower() == "remove":
            quarantine_role = discord.utils.get(ctx.guild.roles, name="Quarantined")
            if quarantine_role and quarantine_role in member.roles:
                await member.remove_roles(quarantine_role, reason=reason)
                embed = discord.Embed(
                    title="✅ Quarantine Removed",
                    description=f"{member.mention} has been unquarantined\nReason: {reason}",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Not Quarantined",
                    description=f"{member.mention} is not currently quarantined",
                    color=discord.Color.red()
                )
        else:
            embed = discord.Embed(
                title="❌ Invalid Action",
                description="Use 'add' or 'remove'",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="trustlevel", description="Set trust level for a user")
    @app_commands.describe(
        member="Member to modify",
        level="Trust level (trusted/neutral/suspicious/high_risk)",
        reason="Reason for change"
    )
    @commands.has_permissions(administrator=True)
    async def trust_level_command(self, ctx, member: discord.Member, level: str, *, reason: str = "Manual override"):
        """Manually set trust level"""
        valid_levels = ['trusted', 'neutral', 'suspicious', 'high_risk']
        
        if level.lower() not in valid_levels:
            embed = discord.Embed(
                title="❌ Invalid Trust Level",
                description=f"Valid levels: {', '.join(valid_levels)}",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        user_data = self.threat_indicators[member.id]
        old_level = user_data['trust_level']
        user_data['trust_level'] = level.lower()
        
        # Adjust reputation score based on trust level
        score_map = {'trusted': 90, 'neutral': 60, 'suspicious': 30, 'high_risk': 10}
        user_data['reputation_score'] = score_map[level.lower()]
        
        embed = discord.Embed(
            title="✅ Trust Level Updated",
            description=f"{member.mention} trust level changed\n**From:** {old_level} → **To:** {level.lower()}\n**Reason:** {reason}",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        await self.log_security_action(ctx.guild, "trust_level_changed", member, f"{old_level} → {level}: {reason}")

async def setup(bot):
    await bot.add_cog(SecuritySystem(bot))