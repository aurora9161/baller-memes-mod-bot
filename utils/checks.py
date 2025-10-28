import discord
from discord.ext import commands
from typing import Union

def is_mod_or_admin():
    """Check if user has moderation permissions"""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        
        if ctx.author.guild_permissions.manage_messages:
            return True
        
        # Check for configured mod/admin roles
        guild_config = ctx.bot.guild_configs.get(ctx.guild.id, {})
        
        mod_role_id = guild_config.get('mod_role')
        admin_role_id = guild_config.get('admin_role')
        
        user_role_ids = [role.id for role in ctx.author.roles]
        
        if mod_role_id and mod_role_id in user_role_ids:
            return True
        
        if admin_role_id and admin_role_id in user_role_ids:
            return True
        
        raise commands.MissingPermissions(['manage_messages'])
    
    return commands.check(predicate)

def is_admin():
    """Check if user has admin permissions"""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        
        # Check for configured admin role
        guild_config = ctx.bot.guild_configs.get(ctx.guild.id, {})
        admin_role_id = guild_config.get('admin_role')
        
        if admin_role_id:
            user_role_ids = [role.id for role in ctx.author.roles]
            if admin_role_id in user_role_ids:
                return True
        
        raise commands.MissingPermissions(['administrator'])
    
    return commands.check(predicate)

def is_owner():
    """Check if user is bot owner"""
    async def predicate(ctx):
        owner_ids = ctx.bot.config.get('owner_ids', [])
        if ctx.author.id in owner_ids:
            return True
        
        return await ctx.bot.is_owner(ctx.author)
    
    return commands.check(predicate)

def can_moderate_member(moderator: discord.Member, target: discord.Member) -> bool:
    """Check if moderator can moderate target member"""
    # Can't moderate yourself
    if moderator == target:
        return False
    
    # Bot owner can moderate anyone
    if moderator.guild.owner == moderator:
        return True
    
    # Can't moderate bot owner
    if target.guild.owner == target:
        return False
    
    # Can't moderate someone with higher role
    if target.top_role >= moderator.top_role:
        return False
    
    return True

def has_higher_role(member1: discord.Member, member2: discord.Member) -> bool:
    """Check if member1 has higher role than member2"""
    return member1.top_role > member2.top_role

def is_blacklisted():
    """Check if user is blacklisted from using the bot"""
    async def predicate(ctx):
        blacklisted_users = ctx.bot.config.get('blacklisted_users', {})
        if str(ctx.author.id) in blacklisted_users:
            raise commands.CheckFailure("You are blacklisted from using this bot.")
        return True
    
    return commands.check(predicate)

def guild_only():
    """Ensure command is only used in guilds"""
    async def predicate(ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage("This command cannot be used in private messages.")
        return True
    
    return commands.check(predicate)