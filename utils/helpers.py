import discord
from datetime import datetime, timedelta
import re
from typing import Optional, Union

def format_duration(seconds: int) -> str:
    """Format seconds into human readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"

def parse_time(time_str: str) -> Optional[timedelta]:
    """Parse time string like '1h30m' into timedelta"""
    if not time_str:
        return None
    
    # Pattern to match time components
    pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
    match = re.match(pattern, time_str.lower().replace(' ', ''))
    
    if not match:
        return None
    
    days, hours, minutes, seconds = match.groups()
    
    total_seconds = 0
    if days:
        total_seconds += int(days) * 86400
    if hours:
        total_seconds += int(hours) * 3600
    if minutes:
        total_seconds += int(minutes) * 60
    if seconds:
        total_seconds += int(seconds)
    
    if total_seconds == 0:
        return None
    
    return timedelta(seconds=total_seconds)

def create_embed(title: str, description: str = None, color: discord.Color = None) -> discord.Embed:
    """Create a standardized embed"""
    if color is None:
        color = discord.Color.blue()
    
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.utcnow()
    return embed

def success_embed(title: str, description: str = None) -> discord.Embed:
    """Create a success embed"""
    return create_embed(title, description, discord.Color.green())

def error_embed(title: str, description: str = None) -> discord.Embed:
    """Create an error embed"""
    return create_embed(title, description, discord.Color.red())

def warning_embed(title: str, description: str = None) -> discord.Embed:
    """Create a warning embed"""
    return create_embed(title, description, discord.Color.orange())

def info_embed(title: str, description: str = None) -> discord.Embed:
    """Create an info embed"""
    return create_embed(title, description, discord.Color.blue())

def get_member_color(member: discord.Member) -> discord.Color:
    """Get member's display color or default blue"""
    if member.color == discord.Color.default():
        return discord.Color.blue()
    return member.color

def truncate_text(text: str, max_length: int = 1024, suffix: str = "...") -> str:
    """Truncate text to fit in embed fields"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def format_permissions(permissions: discord.Permissions) -> str:
    """Format permissions into a readable string"""
    perms = []
    
    if permissions.administrator:
        perms.append("Administrator")
    else:
        perm_list = [
            ('manage_guild', 'Manage Server'),
            ('manage_channels', 'Manage Channels'),
            ('manage_messages', 'Manage Messages'),
            ('manage_roles', 'Manage Roles'),
            ('kick_members', 'Kick Members'),
            ('ban_members', 'Ban Members'),
            ('moderate_members', 'Timeout Members'),
            ('view_audit_log', 'View Audit Log')
        ]
        
        for perm_name, display_name in perm_list:
            if getattr(permissions, perm_name):
                perms.append(display_name)
    
    return ', '.join(perms) if perms else 'No special permissions'

def format_user_id(user: Union[discord.User, discord.Member, int]) -> str:
    """Format user mention with ID"""
    if isinstance(user, (discord.User, discord.Member)):
        return f"{user} ({user.id})"
    else:
        return f"<@{user}> ({user})"

def clean_content(content: str) -> str:
    """Clean message content for logging"""
    # Remove markdown formatting for cleaner logs
    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold
    content = re.sub(r'\*(.*?)\*', r'\1', content)      # Italic
    content = re.sub(r'~~(.*?)~~', r'\1', content)     # Strikethrough
    content = re.sub(r'`(.*?)`', r'\1', content)       # Inline code
    content = re.sub(r'```.*?```', '[Code Block]', content, flags=re.DOTALL)  # Code blocks
    
    # Truncate if too long
    return truncate_text(content, 1000)

def get_relative_time(timestamp: datetime) -> str:
    """Get relative time string"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

def format_list(items: list, max_items: int = 10, item_format: str = "• {}") -> str:
    """Format a list of items for embed display"""
    if not items:
        return "None"
    
    formatted_items = []
    for item in items[:max_items]:
        formatted_items.append(item_format.format(item))
    
    result = "\n".join(formatted_items)
    
    if len(items) > max_items:
        result += f"\n... and {len(items) - max_items} more"
    
    return result

def safe_mention(user_id: int, guild: discord.Guild = None) -> str:
    """Safely mention a user, fallback to ID if user not found"""
    if guild:
        member = guild.get_member(user_id)
        if member:
            return member.mention
    
    return f"<@{user_id}>"

def validate_hex_color(color_str: str) -> Optional[int]:
    """Validate and convert hex color string to integer"""
    if not color_str:
        return None
    
    # Remove # if present
    if color_str.startswith('#'):
        color_str = color_str[1:]
    
    # Validate hex format
    if not re.match(r'^[0-9a-fA-F]{6}$', color_str):
        return None
    
    return int(color_str, 16)

def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"