import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import pytz
import asyncio
import os

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Zona horaria de Perú
peruvian_tz = pytz.timezone('America/Lima')

# Configuración de la alerta
ALERT_HOUR = 19  # 7pm (19:00)
ALERT_MINUTE = 0
ALERT_SENT_TODAY = False

class AlertasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alert_channel = None
        self.daily_alert.start()
    
    def get_unix_timestamp_for_alert():
        """Get Unix timestamp for the next alert at 7pm Peru time"""
        now = datetime.now(peruvian_tz)
        alert_time = now.replace(hour=ALERT_HOUR, minute=ALERT_MINUTE, second=0, microsecond=0)
        
        # If alert time has passed today, use tomorrow's
        if now > alert_time:
            alert_time += timedelta(days=1)
        
        # Convert to UTC for Unix timestamp
        alert_utc = alert_time.astimezone(pytz.UTC)
        unix_timestamp = int(alert_utc.timestamp())
        return unix_timestamp
    
    @tasks.loop(minutes=1)
    async def daily_alert(self):
        """Checks every minute if it's time to send the alert"""
        global ALERT_SENT_TODAY
        
        if self.alert_channel is None:
            return
        
        # Get current time in Peru timezone
        now = datetime.now(peruvian_tz)
        
        # Check if it's the correct time
        if now.hour == ALERT_HOUR and now.minute == ALERT_MINUTE and not ALERT_SENT_TODAY:
            # Get Unix timestamp for 7pm Peru time today
            alert_time = now.replace(hour=ALERT_HOUR, minute=ALERT_MINUTE, second=0, microsecond=0)
            alert_utc = alert_time.astimezone(pytz.UTC)
            unix_timestamp = int(alert_utc.timestamp())
            
            embed = discord.Embed(
                title="🎁 Daily Reward Alert!",
                description="It's time to claim your daily reward in the game!",
                color=discord.Color.gold(),
                timestamp=now
            )
            embed.add_field(
                name="⏰ Claim Now!",
                value=f"Alert sent at <t:{unix_timestamp}:t> (Peru Time)\n\nEach user sees this in their local timezone!",
                inline=False
            )
            embed.add_field(
                name="📝 Reminder",
                value="Don't forget to claim your daily reward before the day ends!",
                inline=False
            )
            embed.set_footer(text="Daily Alert Bot")
            
            try:
                # Send message with @everyone mention
                await self.alert_channel.send("@everyone", embed=embed)
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Alert sent successfully")
                ALERT_SENT_TODAY = True
            except Exception as e:
                print(f"Error sending alert: {e}")
        
        # Reset flag at midnight
        if now.hour == 0 and now.minute == 0:
            ALERT_SENT_TODAY = False
    
    @daily_alert.before_loop
    async def before_daily_alert(self):
        """Wait for bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="set_alert_channel", description="Configure the channel where alerts will be sent")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_alert_channel(self, interaction: discord.Interaction):
        """Configure the channel where alerts will be sent"""
        self.alert_channel = interaction.channel
        embed = discord.Embed(
            title="✅ Alert Channel Configured",
            description=f"Alerts will be sent to {interaction.channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="test_alert", description="Send a test alert")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_alert(self, interaction: discord.Interaction):
        """Send a test alert"""
        if self.alert_channel is None:
            embed = discord.Embed(
                title="❌ Error",
                description="First configure the channel with `/set_alert_channel`",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        now = datetime.now(peruvian_tz)
        
        # Get Unix timestamp for 7pm Peru time
        alert_time = now.replace(hour=ALERT_HOUR, minute=ALERT_MINUTE, second=0, microsecond=0)
        alert_utc = alert_time.astimezone(pytz.UTC)
        unix_timestamp = int(alert_utc.timestamp())
        
        embed = discord.Embed(
            title="🎁 [TEST] Daily Reward Alert!",
            description="This is a test alert.",
            color=discord.Color.blue(),
            timestamp=now
        )
        embed.add_field(
            name="⏰ Claim Now!",
            value=f"Alert would be sent at <t:{unix_timestamp}:t> (Peru Time)\n\nEach user sees this in their local timezone!",
            inline=False
        )
        embed.add_field(
            name="📝 Reminder",
            value="Don't forget to claim your daily reward before the day ends!",
            inline=False
        )
        embed.set_footer(text="Daily Alert Bot - TEST MODE")
        
        await self.alert_channel.send("@everyone", embed=embed)
        
        embed_response = discord.Embed(
            title="✅ Test Alert Sent",
            description=f"Test alert sent to {self.alert_channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed_response, ephemeral=True)
    
    @app_commands.command(name="alert_status", description="Show the current status of the alert system")
    async def alert_status(self, interaction: discord.Interaction):
        """Show the current status of the alert system"""
        now = datetime.now(peruvian_tz)
        
        if self.alert_channel is None:
            status_text = "❌ Not configured"
            channel_text = "None"
        else:
            status_text = "✅ Active"
            channel_text = self.alert_channel.mention
        
        # Calculate next alert
        alert_time = now.replace(hour=ALERT_HOUR, minute=ALERT_MINUTE, second=0, microsecond=0)
        if now > alert_time:
            alert_time += timedelta(days=1)
        
        time_remaining = alert_time - now
        hours = time_remaining.seconds // 3600
        minutes = (time_remaining.seconds % 3600) // 60
        
        # Get Unix timestamp for next alert
        alert_utc = alert_time.astimezone(pytz.UTC)
        unix_timestamp = int(alert_utc.timestamp())
        
        embed = discord.Embed(
            title="📊 Alert System Status",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Status", value=status_text, inline=False)
        embed.add_field(name="Channel", value=channel_text, inline=False)
        embed.add_field(
            name="Next Alert",
            value=f"<t:{unix_timestamp}:f> (in {hours}h {minutes}m)\n\nEach user will see this in their local timezone!",
            inline=False
        )
        embed.add_field(
            name="Alert Reference",
            value="7:00 PM Peru Time (UTC-5)",
            inline=False
        )
        embed.set_footer(text=f"Current Peru time: {now.strftime('%m/%d/%Y %H:%M:%S')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    print(f"📊 Latency: {bot.latency * 1000:.2f}ms")
    print(f"🔔 Alert configured for {ALERT_HOUR:02d}:{ALERT_MINUTE:02d} (Peru Time)")
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
