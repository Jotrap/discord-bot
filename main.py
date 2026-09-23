import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timezone, timedelta
import pytz
import asyncio
import os

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Zona horaria de Perú
peruvian_tz = pytz.timezone('America/Lima')

# Configuración de la alerta
ALERT_HOUR = 19  # 7pm (19:00)
ALERT_MINUTE = 0
ALERT_SENT_TODAY = False

# Zonas horarias para mostrar en el mensaje
TIMEZONES = {
    'America/New_York': 'Eastern Time (EST/EDT)',
    'America/Chicago': 'Central Time (CST/CDT)',
    'America/Denver': 'Mountain Time (MST/MDT)',
    'America/Los_Angeles': 'Pacific Time (PST/PDT)',
    'Europe/London': 'Greenwich Mean Time (GMT)',
    'Europe/Paris': 'Central European Time (CET/CEST)',
    'Europe/Berlin': 'Central European Time (CET/CEST)',
    'Asia/Tokyo': 'Japan Standard Time (JST)',
    'Asia/Shanghai': 'China Standard Time (CST)',
    'Asia/Singapore': 'Singapore Standard Time (SGT)',
    'Asia/Dubai': 'Gulf Standard Time (GST)',
    'Australia/Sydney': 'Australian Eastern Time (AEST/AEDT)',
    'America/Lima': 'Peru Time (PET)',
}

class AlertasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alert_channel = None
        self.daily_alert.start()
    
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
            # Create timezone information string
            timezone_info = "**Time in different zones:**\n"
            for tz_name, tz_display in TIMEZONES.items():
                try:
                    tz = pytz.timezone(tz_name)
                    time_in_tz = now.astimezone(tz)
                    timezone_info += f"🕐 {tz_display}: {time_in_tz.strftime('%H:%M')}\n"
                except:
                    pass
            
            embed = discord.Embed(
                title="🎁 Daily Reward Alert!",
                description="It's time to claim your daily reward in the game!",
                color=discord.Color.gold(),
                timestamp=now
            )
            embed.add_field(
                name="⏰ Current Time",
                value=f"{now.strftime('%H:%M')} (Peru Time)",
                inline=False
            )
            embed.add_field(
                name="🌍 Other Time Zones",
                value=timezone_info,
                inline=False
            )
            embed.add_field(
                name="📝 Remember",
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
    
    @commands.command(name='set_alert_channel')
    @commands.has_permissions(administrator=True)
    async def set_alert_channel(self, ctx):
        """
        Configure the channel where alerts will be sent.
        Usage: !set_alert_channel
        """
        self.alert_channel = ctx.channel
        embed = discord.Embed(
            title="✅ Alert Channel Configured",
            description=f"Alerts will be sent to {ctx.channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='test_alert')
    @commands.has_permissions(administrator=True)
    async def test_alert(self, ctx):
        """
        Send a test alert.
        Usage: !test_alert
        """
        if self.alert_channel is None:
            await ctx.send("❌ First configure the channel with `!set_alert_channel`")
            return
        
        now = datetime.now(peruvian_tz)
        
        # Create timezone information string
        timezone_info = "**Time in different zones:**\n"
        for tz_name, tz_display in TIMEZONES.items():
            try:
                tz = pytz.timezone(tz_name)
                time_in_tz = now.astimezone(tz)
                timezone_info += f"🕐 {tz_display}: {time_in_tz.strftime('%H:%M')}\n"
            except:
                pass
        
        embed = discord.Embed(
            title="🎁 [TEST] Daily Reward Alert!",
            description="This is a test alert.",
            color=discord.Color.blue(),
            timestamp=now
        )
        embed.add_field(
            name="⏰ Current Time",
            value=f"{now.strftime('%H:%M')} (Peru Time)",
            inline=False
        )
        embed.add_field(
            name="🌍 Other Time Zones",
            value=timezone_info,
            inline=False
        )
        embed.set_footer(text="Daily Alert Bot - TEST MODE")
        
        await self.alert_channel.send("@everyone", embed=embed)
        await ctx.send(f"✅ Test alert sent to {self.alert_channel.mention}")
    
    @commands.command(name='alert_status')
    async def alert_status(self, ctx):
        """
        Show the current status of the alert system.
        Usage: !alert_status
        """
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
        
        embed = discord.Embed(
            title="📊 Alert System Status",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Status", value=status_text, inline=False)
        embed.add_field(name="Channel", value=channel_text, inline=False)
        embed.add_field(name="Alert Time", value=f"{ALERT_HOUR:02d}:{ALERT_MINUTE:02d} (Peru Time)", inline=False)
        embed.add_field(
            name="Next Alert",
            value=f"{alert_time.strftime('%m/%d/%Y %H:%M')} (in {hours}h {minutes}m)",
            inline=False
        )
        embed.add_field(
            name="Time Zone",
            value="America/Lima (UTC-5)",
            inline=False
        )
        embed.set_footer(text=f"Current time: {now.strftime('%m/%d/%Y %H:%M:%S')}")
        
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    print(f"📊 Latency: {bot.latency * 1000:.2f}ms")
    print(f"🔔 Alert configured for {ALERT_HOUR:02d}:{ALERT_MINUTE:02d} (Peru Time)")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Insufficient Permissions",
            description="Only administrators can use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
