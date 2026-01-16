import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import asyncio
import os
from dotenv import load_dotenv

# โหลด Token จากไฟล์ .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Sync slash commands เมื่อเปิดบอท
        await self.tree.sync()
        print(f"✅ Synced slash commands for {self.user}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"🤖 Discord Bot is ready as {bot.user}")

def format_countdown(seconds):
    """แปลงวินาทีเป็นรูปแบบ ชม:นาที:วินาที"""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours} ชั่วโมง {minutes} นาที {secs} วินาที"
    elif minutes > 0:
        return f"{minutes} นาที {secs} วินาที"
    else:
        return f"{secs} วินาที"

@bot.tree.command(name="queue", description="สั่งจองเวรล่วงหน้าตามเวลาที่กำหนด")
@app_commands.describe(time_str="เวลาที่จะให้บอทเริ่มรัน (HH:MM เช่น 08:30)")
async def queue(interaction: discord.Interaction, time_str: str):
    try:
        # ตรวจสอบรูปแบบเวลา HH:MM
        target_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        now = datetime.datetime.now()
        target_datetime = datetime.datetime.combine(now.date(), target_time)

        # ถ้าเวลาที่ระบุผ่านมาแล้ว ให้ตั้งเป็นวันพรุ่งนี้
        if target_datetime <= now:
            target_datetime += datetime.timedelta(days=1)
            day_text = "พรุ่งนี้"
        else:
            day_text = "วันนี้"

        wait_seconds = (target_datetime - now).total_seconds()
        countdown_text = format_countdown(wait_seconds)
        
        # ดึงค่าจาก .env (ผ่าน bot_script)
        from bot_script import TARGET_URL, TARGET_DATE, TARGET_DUTY, TARGET_NAME
        
        msg_content = (
            f"✅ **ตั้งเวลาสำเร็จ!**\n"
            f"📅 บอทจะเริ่มทำงาน{day_text}เวลา **{time_str}**\n"
            f"⏳ นับถอยหลัง: **{countdown_text}**\n\n"
            f"📋 **ข้อมูลจาก .env:**\n"
            f"🌐 URL: `{TARGET_URL}`\n"
            f"📆 วันที่: `{TARGET_DATE}`\n"
            f"🧹 หน้าที่: `{TARGET_DUTY}`\n"
            f"✍️ ชื่อ: `{TARGET_NAME}`"
        )
        
        await interaction.response.send_message(msg_content)
        
        # ดึงข้อความที่ส่งไว้เพื่ออัปเดต
        message = await interaction.original_response()

        # อัปเดตนับถอยหลังทุกๆ 5 วินาที (หรือทุก 1 นาทีถ้าเหลือเยอะ)
        update_interval = 60 if wait_seconds > 300 else 5
        
        while wait_seconds > 0:
            await asyncio.sleep(min(update_interval, wait_seconds))
            now = datetime.datetime.now()
            wait_seconds = (target_datetime - now).total_seconds()
            
            if wait_seconds <= 0:
                break
                
            countdown_text = format_countdown(wait_seconds)
            msg_content = (
                f"✅ **ตั้งเวลาสำเร็จ!**\n"
                f"📅 บอทจะเริ่มทำงาน{day_text}เวลา **{time_str}**\n"
                f"⏳ นับถอยหลัง: **{countdown_text}**\n\n"
                f"📋 **ข้อมูลจาก .env:**\n"
                f"🌐 URL: `{TARGET_URL}`\n"
                f"📆 วันที่: `{TARGET_DATE}`\n"
                f"🧹 หน้าที่: `{TARGET_DUTY}`\n"
                f"✍️ ชื่อ: `{TARGET_NAME}`"
            )
            try:
                await message.edit(content=msg_content)
            except:
                pass  # ถ้า edit ไม่ได้ก็ข้ามไป

        # ถึงเวลาแล้ว! อัปเดตข้อความ
        await message.edit(content=f"🚀 **ถึงเวลาแล้ว!** กำลังเริ่มรันบอท...")
        
        print("🚀 Starting bot execution...")
        
        # Import และรันบอทโดยใช้ค่าจาก .env (ผ่าน default ของ run_bot)
        from bot_script import run_bot
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_bot)

        # แจ้งผลทาง Discord
        channel = interaction.channel
        await channel.send(f"🏁 **บอทรันเสร็จเรียบร้อยแล้ว!**\nตั้งเวลาไว้ที่ {time_str}")

    except ValueError:
        await interaction.response.send_message("❌ รูปแบบเวลาไม่ถูกต้อง! กรุณาใช้ HH:MM (เช่น 08:00)", ephemeral=True)
    except Exception as e:
        try:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)
        except:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: ไม่พบ DISCORD_TOKEN ในไฟล์ .env!")
        print("กรุณาสร้างไฟล์ .env แล้วใส่ DISCORD_TOKEN=your_token_here")
    else:
        bot.run(TOKEN)
