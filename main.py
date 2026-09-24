import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import pytz
import asyncio
import os
import json

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Zona horaria de Perú
peruvian_tz = pytz.timezone('America/Lima')

# Configuración de alertas
DAY_RESET_HOUR = 19  # 7pm (19:00)
DAY_RESET_MINUTE = 0
DAY_RESET_SENT_TODAY = False

# Archivo para guardar configuración de Infinity Raids
RAIDS_CONFIG_FILE = 'raids_config.json'

def load_raids_config():
    """Load Infinity Raids configuration from file"""
    try:
        if os.path.exists(RAIDS_CONFIG_FILE):
            with open(RAIDS_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {'role_id': None, 'role_name': None}

def save_raids_config(data):
    """Save Infinity Raids configuration to file"""
    try:
        with open(RAIDS_CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving raids config: {e}")

raids_config = load_raids_config()

class AlertasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.day_reset_channel = None
        self.raids_channel = None
        self.daily_alert.start()
        self.raids_alert.start()
    
    @tasks.loop(minutes=1)
    async def daily_alert(self):
        """Checks every minute if it's time to send the Day Reset alert"""
        global DAY_RESET_SENT_TODAY
        
        if self.day_reset_channel is None:
            return
        
        # Get current time in Peru timezone
        now = datetime.now(peruvian_tz)
        
        # Check if it's the correct time
        if now.hour == DAY_RESET_HOUR and now.minute == DAY_RESET_MINUTE and not DAY_RESET_SENT_TODAY:
            # Get Unix timestamp for alert time
            alert_time = now.replace(hour=DAY_RESET_HOUR, minute=DAY_RESET_MINUTE, second=0, microsecond=0)
            alert_utc = alert_time.astimezone(pytz.UTC)
            unix_timestamp = int(alert_utc.timestamp())
            
            embed = discord.Embed(
                title="Day Reset",
                description="Don't forget to do the Jujutsu Trials, your 2x cc raids and daily tasks.",
                color=discord.Color.gold(),
                timestamp=now
            )
            embed.add_field(
                name="⏰ Reset at",
                value=f"<t:{unix_timestamp}:t>\n\nEach user sees this in their local timezone!",
                inline=False
            )
            embed.set_footer(text="Daily Alert Bot")
            
            try:
                # Send message with @everyone mention
                await self.day_reset_channel.send("@everyone", embed=embed)
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Day Reset alert sent successfully")
                DAY_RESET_SENT_TODAY = True
            except Exception as e:
                print(f"Error sending Day Reset alert: {e}")
        
        # Reset flag at midnight
        if now.hour == 0 and now.minute == 0:
            DAY_RESET_SENT_TODAY = False
    
    @daily_alert.before_loop
    async def before_daily_alert(self):
        """Wait for bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()
    
    @tasks.loop(minutes=1)
    async def raids_alert(self):
        """Checks every minute if it's time to send Infinity Raids alerts at each hour"""
        if self.raids_channel is None or not raids_config.get('role_id'):
            return
        
        # Get current time in Peru timezone
        now = datetime.now(peruvian_tz)
        
        # Check if it's at the top of any hour (minute 0)
        if now.minute == 0:
            # Alert for every hour if role is configured
            role_id = raids_config.get('role_id')
            
            # Get Unix timestamps for start and end time (15 minutes)
            start_time = now.replace(minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(minutes=15)
            
            start_utc = start_time.astimezone(pytz.UTC)
            end_utc = end_time.astimezone(pytz.UTC)
            
            start_timestamp = int(start_utc.timestamp())
            end_timestamp = int(end_utc.timestamp())
            
            embed = discord.Embed(
                title="🔥 Infinity Raids are Open!",
                description="The Infinity Raids have opened! Get ready to raid!",
                color=discord.Color.red(),
                timestamp=now
            )
            embed.add_field(
                name="⏰ Open Window",
                value=f"<t:{start_timestamp}:t> to <t:{end_timestamp}:t>\n\nEach user sees this in their local timezone!",
                inline=False
            )
            embed.add_field(
                name="💪 Reminder",
                value="Join and claim your rewards!",
                inline=False
            )
            embed.set_footer(text="Infinity Raids Alert Bot")
            
            try:
                role = self.bot.get_guild(self.raids_channel.guild.id).get_role(role_id)
                if role:
                    mention = role.mention
                else:
                    mention = "@here"
                
                await self.raids_channel.send(f"{mention}", embed=embed)
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Infinity Raids alert sent for {now.hour:02d}:00")
            except Exception as e:
                print(f"Error sending Infinity Raids alert: {e}")
    
    @raids_alert.before_loop
    async def before_raids_alert(self):
        """Wait for bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="set_day_reset_channel", description="Configure the channel for Day Reset alerts")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_day_reset_channel(self, interaction: discord.Interaction):
        """Configure the channel for Day Reset alerts"""
        self.day_reset_channel = interaction.channel
        embed = discord.Embed(
            title="✅ Day Reset Channel Configured",
            description=f"Day Reset alerts will be sent to {interaction.channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="set_raids_channel", description="Configure the channel for Infinity Raids alerts")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_raids_channel(self, interaction: discord.Interaction):
        """Configure the channel for Infinity Raids alerts"""
        self.raids_channel = interaction.channel
        embed = discord.Embed(
            title="✅ Infinity Raids Channel Configured",
            description=f"Infinity Raids alerts will be sent to {interaction.channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="set_raid_role", description="Set the role for Infinity Raids alerts (alerts every hour)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_raid_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the role for Infinity Raids alerts"""
        raids_config['role_id'] = role.id
        raids_config['role_name'] = role.name
        save_raids_config(raids_config)
        
        embed = discord.Embed(
            title="✅ Raid Role Configured",
            description=f"Infinity Raids alerts will be sent to {role.mention}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="⏰ Alert Frequency",
            value="Alerts will be sent **every hour at XX:00** (all 24 hours)",
            inline=False
        )
        embed.add_field(
            name="⏱️ Duration",
            value="Each alert covers XX:00 to XX:15",
            inline=False
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove_raid_role", description="Remove the Infinity Raids role alert")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_raid_role(self, interaction: discord.Interaction):
        """Remove the Infinity Raids role alert"""
        if not raids_config.get('role_id'):
            embed = discord.Embed(
                title="❌ Error",
                description="No raid role configured",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role_name = raids_config.get('role_name', 'Unknown')
        raids_config['role_id'] = None
        raids_config['role_name'] = None
        save_raids_config(raids_config)
        
        embed = discord.Embed(
            title="✅ Raid Role Removed",
            description=f"Infinity Raids alerts removed for **{role_name}**",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="raid_status", description="Check the current Infinity Raids configuration")
    async def raid_status(self, interaction: discord.Interaction):
        """Check the current Infinity Raids configuration"""
        if not raids_config.get('role_id'):
            embed = discord.Embed(
                title="📊 Infinity Raids Status",
                description="❌ No raid role configured",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="ℹ️ Setup",
                value="Use `/set_raid_role` to configure alerts for all hourly raids",
                inline=False
            )
        else:
            role_name = raids_config.get('role_name', 'Unknown')
            embed = discord.Embed(
                title="📊 Infinity Raids Status",
                description=f"✅ Raids configured for role: **{role_name}**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="⏰ Alert Times",
                value="**Every hour at XX:00** (00:00, 01:00, 02:00... 23:00)",
                inline=False
            )
            embed.add_field(
                name="⏱️ Duration",
                value="Each alert covers XX:00 to XX:15",
                inline=False
            )
            embed.add_field(
                name="📢 Mentions",
                value=f"Will mention {role_name}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="test_day_reset", description="Send a test Day Reset alert")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_day_reset(self, interaction: discord.Interaction):
        """Send a test Day Reset alert"""
        if self.day_reset_channel is None:
            embed = discord.Embed(
                title="❌ Error",
                description="First configure the channel with `/set_day_reset_channel`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        now = datetime.now(peruvian_tz)
        
        # Get Unix timestamp
        alert_time = now.replace(hour=DAY_RESET_HOUR, minute=DAY_RESET_MINUTE, second=0, microsecond=0)
        alert_utc = alert_time.astimezone(pytz.UTC)
        unix_timestamp = int(alert_utc.timestamp())
        
        embed = discord.Embed(
            title="Day Reset",
            description="Don't forget to do the Jujutsu Trials, your 2x cc raids and daily tasks.",
            color=discord.Color.blue(),
            timestamp=now
        )
        embed.add_field(
            name="⏰ Reset at",
            value=f"<t:{unix_timestamp}:t>\n\nEach user sees this in their local timezone!",
            inline=False
        )
        embed.set_footer(text="Daily Alert Bot - TEST MODE")
        
        await self.day_reset_channel.send("@everyone", embed=embed)
        
        embed_response = discord.Embed(
            title="✅ Test Alert Sent",
            description=f"Test Day Reset alert sent to {self.day_reset_channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed_response, ephemeral=True)
    
    @app_commands.command(name="test_raid_alert", description="Send a test Infinity Raids alert")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_raid_alert(self, interaction: discord.Interaction):
        """Send a test Infinity Raids alert"""
        if self.raids_channel is None:
            embed = discord.Embed(
                title="❌ Error",
                description="First configure the channel with `/set_raids_channel`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not raids_config.get('role_id'):
            embed = discord.Embed(
                title="❌ Error",
                description="First set a raid role with `/set_raid_role`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        now = datetime.now(peruvian_tz)
        
        # Get Unix timestamps for start and end time
        start_time = now.replace(minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=15)
        
        start_utc = start_time.astimezone(pytz.UTC)
        end_utc = end_time.astimezone(pytz.UTC)
        
        start_timestamp = int(start_utc.timestamp())
        end_timestamp = int(end_utc.timestamp())
        
        embed = discord.Embed(
            title="🔥 Infinity Raids are Open!",
            description="The Infinity Raids have opened! Get ready to raid!",
            color=discord.Color.red(),
            timestamp=now
        )
        embed.add_field(
            name="⏰ Open Window",
            value=f"<t:{start_timestamp}:t> to <t:{end_timestamp}:t>\n\nEach user sees this in their local timezone!",
            inline=False
        )
        embed.add_field(
            name="💪 Reminder",
            value="Join and claim your rewards!",
            inline=False
        )
        embed.set_footer(text="Infinity Raids Alert Bot - TEST MODE")
        
        role = self.bot.get_guild(self.raids_channel.guild.id).get_role(raids_config.get('role_id'))
        mention = role.mention if role else "@here"
        
        await self.raids_channel.send(f"{mention}", embed=embed)
        
        embed_response = discord.Embed(
            title="✅ Test Alert Sent",
            description=f"Test Infinity Raids alert sent to {self.raids_channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed_response, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    print(f"📊 Latency: {bot.latency * 1000:.2f}ms")
    print(f"🔔 Day Reset configured for {DAY_RESET_HOUR:02d}:{DAY_RESET_MINUTE:02d}")
    if raids_config.get('role_id'):
        role_name = raids_config.get('role_name', 'Unknown')
        print(f"🔥 Infinity Raids alerts configured for role: {role_name} (every hour)")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    try:
        if isinstance(error, app_commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Insufficient Permissions",
                description="Only administrators can use this command.",
                color=discord.Color.red()
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(error)}",
                color=discord.Color.red()
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            print(f"Error: {error}")
    except Exception as e:
        print(f"Error handler error: {e}")

async def main():
    """Main function to run the bot"""
    async with bot:
        await bot.add_cog(AlertasCog(bot))
        
        # Get token from environment variables
        TOKEN = os.environ.get('DISCORD_TOKEN')
        
        if not TOKEN:
            print("❌ Error: DISCORD_TOKEN is not configured")
            return
        
        try:
            await bot.start(TOKEN)
        except Exception as e:
            print(f"Error connecting bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
