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
    return {}

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
        """Checks every minute if it's time to send Infinity Raids alerts"""
        if self.raids_channel is None or not raids_config:
            return
        
        # Get current time in Peru timezone
        now = datetime.now(peruvian_tz)
        current_hour = now.hour
        
        # Check each configured raid time
        for raid_time_str, raid_data in raids_config.items():
            try:
                raid_hour = int(raid_time_str)
                role_id = raid_data.get('role_id')
                last_sent = raid_data.get('last_sent', '')
                
                # Check if it's the correct hour and we haven't sent it yet
                if now.minute == 0 and current_hour == raid_hour and last_sent != now.strftime('%Y-%m-%d %H'):
                    # Get Unix timestamp for raid time
                    raid_alarm_time = now.replace(minute=0, second=0, microsecond=0)
                    raid_utc = raid_alarm_time.astimezone(pytz.UTC)
                    unix_timestamp = int(raid_utc.timestamp())
                    
                    embed = discord.Embed(
                        title="🔥 Infinity Raids are Open!",
                        description="The Infinity Raids have opened! Get ready to raid!",
                        color=discord.Color.red(),
                        timestamp=now
                    )
                    embed.add_field(
                        name="⏰ Open at",
                        value=f"<t:{unix_timestamp}:t>\n\nEach user sees this in their local timezone!",
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
                        
                        # Update last sent time
                        raids_config[raid_time_str]['last_sent'] = now.strftime('%Y-%m-%d %H')
                        save_raids_config(raids_config)
                        
                        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Infinity Raids alert sent for {raid_hour}:00")
                    except Exception as e:
                        print(f"Error sending Infinity Raids alert: {e}")
            except Exception as e:
                print(f"Error processing raid time {raid_time_str}: {e}")
    
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
    
    @app_commands.command(name="add_raid_alert", description="Add an Infinity Raids alert for a specific hour")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_raid_alert(self, interaction: discord.Interaction, hour: int, role: discord.Role):
        """Add an Infinity Raids alert for a specific hour"""
        if hour < 0 or hour > 23:
            embed = discord.Embed(
                title="❌ Error",
                description="Hour must be between 0 and 23",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        raids_config[str(hour)] = {
            'role_id': role.id,
            'role_name': role.name,
            'last_sent': ''
        }
        save_raids_config(raids_config)
        
        embed = discord.Embed(
            title="✅ Raid Alert Added",
            description=f"Infinity Raids alert added for **{hour:02d}:00**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Role",
            value=role.mention,
            inline=False
        )
        embed.add_field(
            name="Notification",
            value=f"Members of {role.mention} will be notified at {hour:02d}:00 (Peru Time)",
            inline=False
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove_raid_alert", description="Remove an Infinity Raids alert for a specific hour")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_raid_alert(self, interaction: discord.Interaction, hour: int):
        """Remove an Infinity Raids alert for a specific hour"""
        if str(hour) not in raids_config:
            embed = discord.Embed(
                title="❌ Error",
                description=f"No raid alert configured for {hour:02d}:00",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role_name = raids_config[str(hour)].get('role_name', 'Unknown')
        del raids_config[str(hour)]
        save_raids_config(raids_config)
        
        embed = discord.Embed(
            title="✅ Raid Alert Removed",
            description=f"Infinity Raids alert removed for **{hour:02d}:00** ({role_name})",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="list_raid_alerts", description="List all configured Infinity Raids alerts")
    async def list_raid_alerts(self, interaction: discord.Interaction):
        """List all configured Infinity Raids alerts"""
        if not raids_config:
            embed = discord.Embed(
                title="📊 Infinity Raids Alerts",
                description="No raid alerts configured yet. Use `/add_raid_alert` to add one.",
                color=discord.Color.blurple()
            )
        else:
            raid_list = "**Configured Raid Times:**\n\n"
            for hour_str in sorted(raids_config.keys(), key=lambda x: int(x)):
                hour = int(hour_str)
                role_name = raids_config[hour_str].get('role_name', 'Unknown')
                raid_list += f"🕐 **{hour:02d}:00** → {role_name}\n"
            
            embed = discord.Embed(
                title="📊 Infinity Raids Alerts",
                description=raid_list,
                color=discord.Color.blurple()
            )
            embed.add_field(
                name="Timezone",
                value="All times are in Peru Time (UTC-5)",
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
    async def test_raid_alert(self, interaction: discord.Interaction, hour: int, role: discord.Role):
        """Send a test Infinity Raids alert"""
        if self.raids_channel is None:
            embed = discord.Embed(
                title="❌ Error",
                description="First configure the channel with `/set_raids_channel`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        now = datetime.now(peruvian_tz)
        
        # Get Unix timestamp
        raid_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        raid_utc = raid_time.astimezone(pytz.UTC)
        unix_timestamp = int(raid_utc.timestamp())
        
        embed = discord.Embed(
            title="🔥 Infinity Raids are Open!",
            description="The Infinity Raids have opened! Get ready to raid!",
            color=discord.Color.red(),
            timestamp=now
        )
        embed.add_field(
            name="⏰ Open at",
            value=f"<t:{unix_timestamp}:t>\n\nEach user sees this in their local timezone!",
            inline=False
        )
        embed.add_field(
            name="💪 Reminder",
            value="Join and claim your rewards!",
            inline=False
        )
        embed.set_footer(text="Infinity Raids Alert Bot - TEST MODE")
        
        await self.raids_channel.send(f"{role.mention}", embed=embed)
        
        embed_response = discord.Embed(
            title="✅ Test Alert Sent",
            description=f"Test Infinity Raids alert sent to {self.raids_channel.mention} for {role.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed_response, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    print(f"📊 Latency: {bot.latency * 1000:.2f}ms")
    print(f"🔔 Day Reset configured for {DAY_RESET_HOUR:02d}:{DAY_RESET_MINUTE:02d} (Peru Time)")
    if raids_config:
        print(f"🔥 Infinity Raids alerts configured: {', '.join([f'{h}:00' for h in sorted(raids_config.keys(), key=lambda x: int(x))])}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Insufficient Permissions",
            description="Only administrators can use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"Error: {error}")

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
