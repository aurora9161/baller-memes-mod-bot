import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import sys
import traceback
from datetime import datetime
import subprocess
import os

class Owner(commands.Cog):
    """Owner-only commands for bot management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        """Check if user is bot owner"""
        owner_ids = self.bot.config.get('owner_ids', [])
        return ctx.author.id in owner_ids or await self.bot.is_owner(ctx.author)
    
    @commands.hybrid_command(name="reload", description="Reload a cog")
    @app_commands.describe(cog="Name of the cog to reload")
    async def reload_cog(self, ctx, cog: str):
        """Reload a specific cog"""
        try:
            await self.bot.reload_extension(f'cogs.{cog}')
            embed = discord.Embed(
                title="✅ Cog Reloaded",
                description=f"Successfully reloaded `{cog}` cog.",
                color=discord.Color.green()
            )
        except commands.ExtensionNotLoaded:
            embed = discord.Embed(
                title="❌ Cog Not Loaded",
                description=f"Cog `{cog}` is not currently loaded.",
                color=discord.Color.red()
            )
        except commands.ExtensionNotFound:
            embed = discord.Embed(
                title="❌ Cog Not Found",
                description=f"Cog `{cog}` does not exist.",
                color=discord.Color.red()
            )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reload Failed",
                description=f"Failed to reload `{cog}`: {str(e)}",
                color=discord.Color.red()
            )
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="load", description="Load a cog")
    @app_commands.describe(cog="Name of the cog to load")
    async def load_cog(self, ctx, cog: str):
        """Load a specific cog"""
        try:
            await self.bot.load_extension(f'cogs.{cog}')
            embed = discord.Embed(
                title="✅ Cog Loaded",
                description=f"Successfully loaded `{cog}` cog.",
                color=discord.Color.green()
            )
        except commands.ExtensionAlreadyLoaded:
            embed = discord.Embed(
                title="❌ Cog Already Loaded",
                description=f"Cog `{cog}` is already loaded.",
                color=discord.Color.red()
            )
        except commands.ExtensionNotFound:
            embed = discord.Embed(
                title="❌ Cog Not Found",
                description=f"Cog `{cog}` does not exist.",
                color=discord.Color.red()
            )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Load Failed",
                description=f"Failed to load `{cog}`: {str(e)}",
                color=discord.Color.red()
            )
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unload", description="Unload a cog")
    @app_commands.describe(cog="Name of the cog to unload")
    async def unload_cog(self, ctx, cog: str):
        """Unload a specific cog"""
        if cog.lower() == 'owner':
            embed = discord.Embed(
                title="❌ Cannot Unload",
                description="Cannot unload the owner cog!",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        try:
            await self.bot.unload_extension(f'cogs.{cog}')
            embed = discord.Embed(
                title="✅ Cog Unloaded",
                description=f"Successfully unloaded `{cog}` cog.",
                color=discord.Color.green()
            )
        except commands.ExtensionNotLoaded:
            embed = discord.Embed(
                title="❌ Cog Not Loaded",
                description=f"Cog `{cog}` is not currently loaded.",
                color=discord.Color.red()
            )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Unload Failed",
                description=f"Failed to unload `{cog}`: {str(e)}",
                color=discord.Color.red()
            )
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="sync", description="Sync slash commands")
    async def sync_commands(self, ctx):
        """Sync slash commands globally or to current guild"""
        try:
            # Sync globally
            synced = await self.bot.tree.sync()
            
            embed = discord.Embed(
                title="✅ Commands Synced",
                description=f"Successfully synced {len(synced)} commands globally.",
                color=discord.Color.green()
            )
            
            # Also sync to current guild for faster testing
            if ctx.guild:
                guild_synced = await self.bot.tree.sync(guild=ctx.guild)
                embed.add_field(
                    name="Guild Sync",
                    value=f"Synced {len(guild_synced)} commands to this guild for testing.",
                    inline=False
                )
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Sync Failed",
                description=f"Failed to sync commands: {str(e)}",
                color=discord.Color.red()
            )
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="shutdown", description="Shutdown the bot")
    async def shutdown(self, ctx):
        """Shutdown the bot"""
        embed = discord.Embed(
            title="🔌 Shutting Down",
            description="Bot is shutting down...",
            color=discord.Color.red()
        )
        embed.add_field(name="Shutdown by", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
        await self.bot.close()
    
    @commands.hybrid_command(name="eval", description="Evaluate Python code")
    @app_commands.describe(code="Python code to evaluate")
    async def eval_code(self, ctx, *, code: str):
        """Evaluate Python code (DANGEROUS)"""
        # Remove code blocks if present
        if code.startswith('```python'):
            code = code[9:-3]
        elif code.startswith('```'):
            code = code[3:-3]
        
        # Create environment
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'discord': discord,
            'commands': commands,
            'asyncio': asyncio
        }
        
        try:
            # Execute code
            result = eval(code, env)
            if asyncio.iscoroutine(result):
                result = await result
            
            # Format result
            if result is None:
                result_text = "None"
            else:
                result_text = str(result)
            
            # Truncate if too long
            if len(result_text) > 1900:
                result_text = result_text[:1900] + "..."
            
            embed = discord.Embed(
                title="✅ Code Executed",
                color=discord.Color.green()
            )
            embed.add_field(name="Input", value=f"```python\n{code[:1000]}```", inline=False)
            embed.add_field(name="Output", value=f"```python\n{result_text}```", inline=False)
            
        except Exception as e:
            error_text = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            if len(error_text) > 1900:
                error_text = error_text[:1900] + "..."
            
            embed = discord.Embed(
                title="❌ Code Failed",
                color=discord.Color.red()
            )
            embed.add_field(name="Input", value=f"```python\n{code[:1000]}```", inline=False)
            embed.add_field(name="Error", value=f"```python\n{error_text}```", inline=False)
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="guilds", description="List all guilds the bot is in")
    async def list_guilds(self, ctx):
        """List all guilds"""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        
        embed = discord.Embed(
            title="🏰 Bot Guilds",
            description=f"Bot is in {len(guilds)} guilds",
            color=discord.Color.blue()
        )
        
        guild_list = []
        for i, guild in enumerate(guilds[:20], 1):  # Show top 20
            guild_list.append(
                f"{i}. **{guild.name}** ({guild.id})\n"
                f"   Members: {guild.member_count} | Owner: {guild.owner}"
            )
        
        if guild_list:
            embed.add_field(
                name="Top Guilds by Member Count",
                value="\n".join(guild_list[:10]),
                inline=False
            )
            
            if len(guild_list) > 10:
                embed.add_field(
                    name="More Guilds",
                    value="\n".join(guild_list[10:]),
                    inline=False
                )
        
        if len(guilds) > 20:
            embed.set_footer(text=f"Showing 20 of {len(guilds)} guilds")
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="leave", description="Leave a guild")
    @app_commands.describe(guild_id="ID of the guild to leave")
    async def leave_guild(self, ctx, guild_id: str):
        """Leave a specific guild"""
        try:
            guild_id = int(guild_id)
            guild = self.bot.get_guild(guild_id)
            
            if not guild:
                embed = discord.Embed(
                    title="❌ Guild Not Found",
                    description=f"Could not find guild with ID {guild_id}",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
            
            guild_name = guild.name
            await guild.leave()
            
            embed = discord.Embed(
                title="✅ Left Guild",
                description=f"Successfully left **{guild_name}** ({guild_id})",
                color=discord.Color.green()
            )
            embed.timestamp = datetime.utcnow()
            
            await ctx.send(embed=embed)
            
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid ID",
                description="Please provide a valid guild ID (numbers only)",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to leave guild: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="blacklist", description="Blacklist a user from using the bot")
    @app_commands.describe(
        user_id="User ID to blacklist",
        reason="Reason for blacklisting"
    )
    async def blacklist_user(self, ctx, user_id: str, *, reason: str = "No reason provided"):
        """Blacklist a user from using the bot"""
        try:
            user_id = int(user_id)
            user = await self.bot.fetch_user(user_id)
            
            # Add to blacklist (you would store this in a database)
            if 'blacklisted_users' not in self.bot.config:
                self.bot.config['blacklisted_users'] = {}
            
            self.bot.config['blacklisted_users'][str(user_id)] = {
                'reason': reason,
                'blacklisted_by': ctx.author.id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Save config
            with open('config.json', 'w') as f:
                json.dump(self.bot.config, f, indent=4)
            
            embed = discord.Embed(
                title="✅ User Blacklisted",
                description=f"**{user}** ({user_id}) has been blacklisted.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Blacklisted by", value=ctx.author.mention, inline=True)
            embed.timestamp = datetime.utcnow()
            
            await ctx.send(embed=embed)
            
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid ID",
                description="Please provide a valid user ID (numbers only)",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.NotFound:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"Could not find user with ID {user_id}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to blacklist user: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="unblacklist", description="Remove a user from blacklist")
    @app_commands.describe(user_id="User ID to unblacklist")
    async def unblacklist_user(self, ctx, user_id: str):
        """Remove a user from blacklist"""
        try:
            user_id = int(user_id)
            
            if 'blacklisted_users' not in self.bot.config or str(user_id) not in self.bot.config['blacklisted_users']:
                embed = discord.Embed(
                    title="❌ User Not Blacklisted",
                    description=f"User {user_id} is not blacklisted.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
            
            user = await self.bot.fetch_user(user_id)
            del self.bot.config['blacklisted_users'][str(user_id)]
            
            # Save config
            with open('config.json', 'w') as f:
                json.dump(self.bot.config, f, indent=4)
            
            embed = discord.Embed(
                title="✅ User Unblacklisted",
                description=f"**{user}** ({user_id}) has been removed from blacklist.",
                color=discord.Color.green()
            )
            embed.add_field(name="Unblacklisted by", value=ctx.author.mention, inline=True)
            embed.timestamp = datetime.utcnow()
            
            await ctx.send(embed=embed)
            
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid ID",
                description="Please provide a valid user ID (numbers only)",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to unblacklist user: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="status", description="Change bot status")
    @app_commands.describe(
        status_type="Type of status (playing, watching, listening, streaming)",
        text="Status text"
    )
    async def change_status(self, ctx, status_type: str, *, text: str):
        """Change bot status"""
        status_types = {
            'playing': discord.ActivityType.playing,
            'watching': discord.ActivityType.watching,
            'listening': discord.ActivityType.listening,
            'streaming': discord.ActivityType.streaming
        }
        
        if status_type.lower() not in status_types:
            embed = discord.Embed(
                title="❌ Invalid Status Type",
                description=f"Valid types: {', '.join(status_types.keys())}",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        activity_type = status_types[status_type.lower()]
        activity = discord.Activity(type=activity_type, name=text)
        
        await self.bot.change_presence(activity=activity)
        
        embed = discord.Embed(
            title="✅ Status Changed",
            description=f"Bot status changed to **{status_type}** {text}",
            color=discord.Color.green()
        )
        embed.add_field(name="Changed by", value=ctx.author.mention, inline=True)
        embed.timestamp = datetime.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="cogs", description="List all loaded cogs")
    async def list_cogs(self, ctx):
        """List all loaded cogs"""
        loaded_cogs = [name.split('.')[-1] for name in self.bot.extensions.keys()]
        
        embed = discord.Embed(
            title="🔧 Loaded Cogs",
            description=f"Currently loaded: {len(loaded_cogs)} cogs",
            color=discord.Color.blue()
        )
        
        if loaded_cogs:
            embed.add_field(
                name="Cogs",
                value="\n".join([f"• {cog}" for cog in sorted(loaded_cogs)]),
                inline=False
            )
        
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Owner(bot))