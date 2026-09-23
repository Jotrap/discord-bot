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

class AlertasCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alert_channel = None
        self.daily_alert.start()
    
    @tasks.loop(minutes=1)
    async def daily_alert(self):
        """Verifica cada minuto si es la hora de enviar la alerta"""
        global ALERT_SENT_TODAY
        
        if self.alert_channel is None:
            return
        
        # Obtener la hora actual en zona horaria de Perú
        now = datetime.now(peruvian_tz)
        
        # Verificar si es la hora correcta
        if now.hour == ALERT_HOUR and now.minute == ALERT_MINUTE and not ALERT_SENT_TODAY:
            embed = discord.Embed(
                title="🎁 ¡Alerta de Regalo Diario!",
                description="Es hora de reclamar tu regalo diario en el juego.",
                color=discord.Color.gold(),
                timestamp=now
            )
            embed.add_field(
                name="⏰ Hora",
                value=f"{now.strftime('%H:%M')} (Hora Perú)",
                inline=False
            )
            embed.add_field(
                name="📝 Recuerda",
                value="No olvides reclamar tu regalo antes de que se acabe el día.",
                inline=False
            )
            embed.set_footer(text="Bot de Alertas Diarias")
            
            try:
                await self.alert_channel.send("@everyone", embed=embed)
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Alerta enviada correctamente")
                ALERT_SENT_TODAY = True
            except Exception as e:
                print(f"Error al enviar alerta: {e}")
        
        # Resetear bandera cuando sea medianoche
        if now.hour == 0 and now.minute == 0:
            ALERT_SENT_TODAY = False
    
    @daily_alert.before_loop
    async def before_daily_alert(self):
        """Esperar a que el bot esté listo antes de iniciar el loop"""
        await self.bot.wait_until_ready()
    
    @commands.command(name='set_alert_channel')
    @commands.has_permissions(administrator=True)
    async def set_alert_channel(self, ctx):
        """
        Configura el canal donde se enviarán las alertas.
        Uso: !set_alert_channel
        """
        self.alert_channel = ctx.channel
        embed = discord.Embed(
            title="✅ Canal de Alertas Configurado",
            description=f"Las alertas se enviarán a {ctx.channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='test_alert')
    @commands.has_permissions(administrator=True)
    async def test_alert(self, ctx):
        """
        Envía una alerta de prueba.
        Uso: !test_alert
        """
        if self.alert_channel is None:
            await ctx.send("❌ Primero configura el canal con `!set_alert_channel`")
            return
        
        now = datetime.now(peruvian_tz)
        embed = discord.Embed(
            title="🎁 [PRUEBA] ¡Alerta de Regalo Diario!",
            description="Esta es una alerta de prueba.",
            color=discord.Color.blue(),
            timestamp=now
        )
        embed.add_field(
            name="⏰ Hora",
            value=f"{now.strftime('%H:%M')} (Hora Perú)",
            inline=False
        )
        embed.set_footer(text="Bot de Alertas Diarias - MODO PRUEBA")
        
        await self.alert_channel.send(embed=embed)
        await ctx.send(f"✅ Alerta de prueba enviada a {self.alert_channel.mention}")
    
    @commands.command(name='alert_status')
    async def alert_status(self, ctx):
        """
        Muestra el estado actual del sistema de alertas.
        Uso: !alert_status
        """
        now = datetime.now(peruvian_tz)
        
        if self.alert_channel is None:
            status_text = "❌ No configurado"
            channel_text = "Ninguno"
        else:
            status_text = "✅ Activo"
            channel_text = self.alert_channel.mention
        
        # Calcular próxima alerta
        alert_time = now.replace(hour=ALERT_HOUR, minute=ALERT_MINUTE, second=0, microsecond=0)
        if now > alert_time:
            alert_time += timedelta(days=1)
        
        time_remaining = alert_time - now
        hours = time_remaining.seconds // 3600
        minutes = (time_remaining.seconds % 3600) // 60
        
        embed = discord.Embed(
            title="📊 Estado del Sistema de Alertas",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Estado", value=status_text, inline=False)
        embed.add_field(name="Canal", value=channel_text, inline=False)
        embed.add_field(name="Hora de Alerta", value=f"{ALERT_HOUR:02d}:{ALERT_MINUTE:02d} (Hora Perú)", inline=False)
        embed.add_field(
            name="Próxima Alerta",
            value=f"{alert_time.strftime('%d/%m/%Y %H:%M')} (en {hours}h {minutes}m)",
            inline=False
        )
        embed.add_field(
            name="Zona Horaria",
            value="America/Lima (UTC-5)",
            inline=False
        )
        embed.set_footer(text=f"Hora actual: {now.strftime('%d/%m/%Y %H:%M:%S')}")
        
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    print(f"📊 Latencia: {bot.latency * 1000:.2f}ms")
    print(f"🔔 Alerta configurada para las {ALERT_HOUR:02d}:{ALERT_MINUTE:02d} (Hora Perú)")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permisos Insuficientes",
            description="Solo administradores pueden usar este comando.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        embed = discord.Embed(
            title="❌ Error",
            description=f"Ocurrió un error: {str(error)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        print(f"Error: {error}")

async def main():
    """Función principal para ejecutar el bot"""
    async with bot:
        await bot.add_cog(AlertasCog(bot))
        
        # Obtener token de variables de entorno
        TOKEN = os.environ.get('DISCORD_TOKEN')
        
        if not TOKEN:
            print("❌ Error: DISCORD_TOKEN no está configurado")
            return
        
        try:
            await bot.start(TOKEN)
        except Exception as e:
            print(f"Error al conectar el bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())