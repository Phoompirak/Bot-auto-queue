import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio
import os
from dotenv import load_dotenv
from bot_script import run_bot

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

@bot.tree.command(name="queue", description="สั่งจองเวรล่วงหน้าตามเวลาที่กำหนด")
@app_commands.describe(time_str="เวลาที่จะให้บอทเริ่มรัน (HH:MM เช่น 08:30)", 
                       duty="ชื่อหน้าที่ (เว้นว่างไว้ถ้าจะใช้ค่าเริ่มต้น)",
                       name="ชื่อผู้จอง (เว้นว่างไว้ถ้าจะใช้ค่าจากสคริปต์)")
async def queue(interaction: discord.Interaction, time_str: str, duty: str = None, name: str = None):
    try:
        # ตรวจสอบรูปแบบเวลา HH:MM
        target_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        now = datetime.datetime.now()
        target_datetime = datetime.datetime.combine(now.date(), target_time)

        # ถ้าเวลาที่ระบุผ่านมาแล้ว ให้ไปรันวันพรุ่งนี้แทน (หรือแจ้งเตือน)
        if target_datetime < now:
            await interaction.response.send_message(f"⚠️ เวลา {time_str} ผ่านมาแล้วนะ! กรุณาระบุเวลาในอนาคต", ephemeral=True)
            return

        wait_seconds = (target_datetime - now).total_seconds()
        
        msg = f"✅ ตั้งเวลาสำเร็จ! บอทจะเริ่มทำงานตอน **{time_str}**"
        if duty: msg += f"\n🧹 หน้าที่: {duty}"
        if name: msg += f"\n✍️ ชื่อ: {name}"
        
        await interaction.response.send_message(msg)

        # รอจนกว่าจะถึงเวลา
        print(f"⏳ Waiting {wait_seconds:.0f} seconds until {time_str}...")
        await asyncio.sleep(wait_seconds)

        # เริ่มรันบอท
        print("🚀 Starting bot execution...")
        # เราดึงค่าเริ่มต้นจากใน bot_script มาใช้ถ้าผู้ใช้ไม่ได้ระบุเพิ่ม
        from bot_script import TARGET_DUTY, TARGET_NAME
        final_duty = duty if duty else TARGET_DUTY
        final_name = name if name else TARGET_NAME
        
        # รัน Selenium (หมายเหตุ: บอทดิสคอร์ดจะค้างจนกว่าบอทเซเลเนียมจะจบ ถ้าไม่รันแบบ Thread/Subprocess)
        # แต่เนื่องจากเราต้องการความง่าย เราจะรันท่านี้ก่อน
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_bot, "http://localhost:3000", now.strftime("%Y-%m-%d"), final_duty, final_name)

        # แจ้งผลทาง Discord (ตัวอย่าง)
        channel = interaction.channel
        await channel.send(f"🏁 บอทรันเสร็จเรียบร้อยแล้วสำหรับเวลา {time_str}!")

    except ValueError:
        await interaction.response.send_message("❌ รูปแบบเวลาไม่ถูกต้อง! กรุณาใช้ HH:MM (เช่น 08:00)", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: ไม่พบ DISCORD_TOKEN ในไฟล์ .env!")
        print("กรุณาสร้างไฟล์ .env แล้วใส่ DISCORD_TOKEN=your_token_here")
    else:
        bot.run(TOKEN)
