import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# โหลด Token จากไฟล์ .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PORT = int(os.getenv('PORT', 10000))

# ==========================================
# Simple HTTP Server สำหรับ Render Health Check
# ==========================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Discord Bot is running!')
    
    def log_message(self, format, *args):
        pass  # ปิด log เพื่อไม่ให้รกคอนโซล

def run_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    print(f"🌐 Health check server running on port {PORT}")
    server.serve_forever()

THAI_TZ = ZoneInfo("Asia/Bangkok")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # เห็นสมาชิกในเซิฟเวอร์
        intents.presences = True # เห็นสถานะ Online/Offline
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
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
        return f"{secs} วินาที"

@bot.tree.command(name="help-queue", description="ดูวิธีใช้งานบอทจองเวร")
async def help_queue(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 คู่มือการใช้งานบอทจองเวร",
        description="วิธีสั่งงานบอทให้จองเวรอัตโนมัติ",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="1. สั่งจองวันนี้/พรุ่งนี้",
        value="`/queue 08:30`\n(บอทจะเริ่มรันเวลา 08:30 ของวันนี้ หรือพรุ่งนี้ถ้าเลยเวลาแล้ว)",
        inline=False
    )
    
    embed.add_field(
        name="2. สั่งจองล่วงหน้า (ระบุวันที่, หน้าที่, ชื่อ)",
        value="`/queue 08:30` (สามารถเลือก option เสริมได้)\n- `date_str`: ระบุวันที่ (เช่น 21/01/69)\n- `duty_select`: เลือกหน้าที่ (มีให้เลือกในลิสต์)\n- `name_input`: ระบุชื่อคนจอง",
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ หมายเหตุ",
        value="- ถ้าไม่ระบุ `duty` หรือ `name` จะใช้ค่าเริ่มต้นจาก `.env`\n- เมื่อจองเสร็จจะมีรูป Screenshot ส่งมาให้ดู",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="queue", description="สั่งจองเวรล่วงหน้า")
@app_commands.describe(
    time_str="เวลาที่จะให้บอทเริ่มรัน (HH:MM เช่น 08:30)",
    date_str="วันที่ที่จะจอง (dd/mm/yy พ.ศ. เช่น 21/01/69) *ไม่บังคับ",
    duty_select="เลือกหน้าที่ (ถ้าไม่เลือกจะใช้จาก .env)",
    name_input="ชื่อคนจอง (ถ้าไม่ใส่จะใช้จาก .env)"
)
@app_commands.choices(duty_select=[
    app_commands.Choice(name="เทขยะ1", value="เทขยะ1"),
    app_commands.Choice(name="เทขยะ2", value="เทขยะ2"),
    app_commands.Choice(name="กวาดห้อง1", value="กวาดห้อง1"),
    app_commands.Choice(name="กวาดห้อง2", value="กวาดห้อง2"),
    app_commands.Choice(name="กวาดห้อง3", value="กวาดห้อง3"),
    app_commands.Choice(name="จัดโต๊ะปิดไฟปิดพัดลม", value="จัดโต๊ะปิดไฟปิดพัดลม"),
    app_commands.Choice(name="ลบกระดานปิดหน้าต่าง", value="ลบกระดานปิดหน้าต่าง")
])
async def queue(interaction: discord.Interaction, time_str: str, date_str: str = None, duty_select: app_commands.Choice[str] = None, name_input: str = None):
    try:
        # ใช้เวลาไทย (UTC+7)
        now = datetime.datetime.now(THAI_TZ)
        
        # 1. คำนวณเวลาที่จะรันบอท (Scheduled Time)
        target_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        target_datetime = datetime.datetime.combine(now.date(), target_time, tzinfo=THAI_TZ)

        # ถ้าเวลาที่ระบุผ่านมาแล้ว ให้ตั้งเป็นวันพรุ่งนี้
        if target_datetime <= now:
            target_datetime += datetime.timedelta(days=1)
            day_text = "พรุ่งนี้"
        else:
            day_text = "วันนี้"

        wait_seconds = (target_datetime - now).total_seconds()
        countdown_text = format_countdown(wait_seconds)
        
        # 2. คำนวณวันที่ที่จะจอง (Booking Date)
        booking_date = ""
        date_note = ""
        
        if date_str:
            # กรณีระบุวันที่เอง (คาดว่าเป็น พ.ศ. dd/mm/yy)
            try:
                parts = date_str.split('/')
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                
                # แปลง พ.ศ. 2 หลัก -> ค.ศ. 4 หลัก
                if y < 100:
                    y_ad = 1957 + y
                elif y > 2400:
                    y_ad = y - 543
                else:
                    y_ad = y # กรณีใส่ 2026 มาตรงๆ
                
                # Format เป็น YYYY-MM-DD
                booking_date_obj = datetime.date(y_ad, m, d)
                booking_date = booking_date_obj.strftime("%Y-%m-%d")
                date_note = "(ระบุเอง)"
            except:
                await interaction.response.send_message("❌ รูปแบบวันที่ไม่ถูกต้อง! กรุณาใช้ dd/mm/yy (เช่น 21/01/69)", ephemeral=True)
                return
        else:
            # กรณีไม่ระบุ -> ใช้วันเดียวกับที่บอทจะรัน
            booking_date = target_datetime.strftime("%Y-%m-%d")
            date_note = f"({day_text})"
        
        # ดึงค่า Config อื่นๆ (จาก .env)
        from bot_script import TARGET_URL, TARGET_DUTY as ENV_DUTY, TARGET_NAME as ENV_NAME, get_today_date, run_bot
        
        # ใช้ค่าที่ user เลือก หรือใช้จาก .env ถ้าไม่ได้เลือก
        final_duty = duty_select.value if duty_select else ENV_DUTY
        final_name = name_input if name_input else ENV_NAME
        
        msg_content = (
            f"✅ **ตั้งเวลาสำเร็จ!**\n"
            f"📅 บอทจะเริ่มทำงาน{day_text}เวลา **{time_str}** (เวลาไทย)\n"
            f"⏳ นับถอยหลัง: **{countdown_text}**\n\n"
            f"📋 **ข้อมูลที่จะใช้จอง:**\n"
            f"🌐 URL: `{TARGET_URL}`\n"
            f"📆 วันที่ที่จะจอง: `{booking_date}` {date_note}\n"
            f"🧹 หน้าที่: `{final_duty}`\n"
            f"✍️ ชื่อ: `{final_name}`"
        )
        
        await interaction.response.send_message(msg_content)
        
        message = await interaction.original_response()

        # อัปเดตนับถอยหลังทุกๆ 5 วินาที (หรือทุก 1 นาทีถ้าเหลือเยอะ)
        update_interval = 60 if wait_seconds > 300 else 5
        
        while wait_seconds > 0:
            await asyncio.sleep(min(update_interval, wait_seconds))
            now = datetime.datetime.now(THAI_TZ)
            wait_seconds = (target_datetime - now).total_seconds()
            
            if wait_seconds <= 0:
                break
                
            countdown_text = format_countdown(wait_seconds)
            msg_content = (
                f"✅ **ตั้งเวลาสำเร็จ!**\n"
                f"📅 บอทจะเริ่มทำงาน{day_text}เวลา **{time_str}** (เวลาไทย)\n"
                f"⏳ นับถอยหลัง: **{countdown_text}**\n\n"
                f"📋 **ข้อมูลที่จะใช้จอง:**\n"
                f"🌐 URL: `{TARGET_URL}`\n"
                f"📆 วันที่ที่จะจอง: `{booking_date}` {date_note}\n"
                f"🧹 หน้าที่: `{final_duty}`\n"
                f"✍️ ชื่อ: `{final_name}`"
            )
            try:
                await message.edit(content=msg_content)
            except:
                pass

        # ถึงเวลาแล้ว!
        await message.edit(content=f"🚀 **ถึงเวลาแล้ว!** กำลังเริ่มรันบอท...")
        
        print("🚀 Starting bot execution...")
        
        # Callback function เพื่อส่ง Log กลับมาที่ Discord
        # (ต้องใช้ run_coroutine_threadsafe เพราะ callback ถูกเรียกจาก Thread อื่น)
        def progress_callback(text):
            # กรองเฉพาะข้อความที่สำคัญ หรือตกแต่งข้อความ
            content = f"🚀 **กำลังรันบอท...**\n```{text}```"
            asyncio.run_coroutine_threadsafe(message.edit(content=content), bot.loop)

        from bot_script import run_bot
        import functools
        
        # ใช้ partial เพื่อส่ง callback และ parameters ต่างๆ เข้าไป
        loop = asyncio.get_event_loop()
        run_bot_with_callback = functools.partial(
            run_bot, 
            date=booking_date, 
            duty=final_duty, 
            name=final_name, 
            callback=progress_callback
        )
        
        # รันใน Executor เพื่อไม่ให้ Main Loop ค้าง
        result = await loop.run_in_executor(None, run_bot_with_callback)

        # Parse ผลลัพธ์ (result เป็น dict ที่มี status, message, screenshot)
        status = result.get("status", "UNKNOWN")
        message_text = result.get("message", "No message")
        screenshot_path = result.get("screenshot")
        
        # สร้างข้อความสรุป
        if status == "SUCCESS":
            summary = f"✅ **จองสำเร็จ!**\n📝 {message_text}"
        elif status == "FAILED":
            summary = f"❌ **จองไม่สำเร็จ!**\n📝 เหตุผล: {message_text}"
        elif status == "ERROR":
            summary = f"⚠️ **เกิดข้อผิดพลาด!**\n📝 {message_text}"
        else:
            summary = f"❓ **สถานะไม่แน่ชัด**\n📝 {message_text}"
        
        channel = interaction.channel
        
        # Debug: แสดง screenshot path
        print(f"📸 Screenshot path: {screenshot_path}")
        if screenshot_path:
            print(f"📸 File exists: {os.path.exists(screenshot_path)}")
        
        # พยายามส่งหลายวิธี
        sent = False
        
        # วิธี 1: ใช้ interaction.followup.send (แนะนำ)
        if not sent:
            try:
                if screenshot_path and os.path.exists(screenshot_path):
                    print(f"📸 Trying followup.send with screenshot...")
                    file = discord.File(screenshot_path, filename="booking_result.png")
                    await interaction.followup.send(content=f"🏁 **บอทรันเสร็จแล้ว** (เวลาไทย {time_str})\n\n{summary}", file=file)
                else:
                    await interaction.followup.send(f"🏁 **บอทรันเสร็จแล้ว** (เวลาไทย {time_str})\n\n{summary}\n\n(ไม่สามารถถ่าย Screenshot ได้)")
                sent = True
                print(f"📸 Sent via followup!")
            except Exception as e:
                print(f"⚠️ followup.send failed: {e}")
        
        # วิธี 2: ใช้ channel.send
        if not sent:
            try:
                if screenshot_path and os.path.exists(screenshot_path):
                    print(f"📸 Trying channel.send with screenshot...")
                    file = discord.File(screenshot_path, filename="booking_result.png")
                    await channel.send(content=f"🏁 **บอทรันเสร็จแล้ว** (เวลาไทย {time_str})\n\n{summary}", file=file)
                else:
                    await channel.send(f"🏁 **บอทรันเสร็จแล้ว** (เวลาไทย {time_str})\n\n{summary}")
                sent = True
                print(f"📸 Sent via channel!")
            except Exception as e:
                print(f"⚠️ channel.send failed: {e}")
        
        # วิธี 3: แก้ไขข้อความเดิม (fallback สุดท้าย - ไม่มีรูป)
        if not sent:
            try:
                print(f"📸 Trying message.edit as last resort...")
                await message.edit(content=f"🏁 **บอทรันเสร็จแล้ว!**\n\n{summary}\n\n📸 Screenshot: {screenshot_path}")
                print(f"📸 Updated via message.edit!")
            except Exception as e:
                print(f"⚠️ All send methods failed: {e}")

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
        # เริ่ม HTTP server ใน background thread (สำหรับ Render health check)
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        
        # รัน Discord bot
        bot.run(TOKEN)

