import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import asyncio
import os
import threading
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# โหลด Config จากไฟล์ .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PORT = int(os.getenv('PORT', 10000))
APPS_SCRIPT_URL = os.getenv('APPS_SCRIPT_URL', '')  # URL ของ Google Apps Script

# ==========================================
# Timezone
# ==========================================
THAI_TZ = ZoneInfo("Asia/Bangkok")

# ==========================================
# Google Apps Script API Helpers
# ==========================================
def call_apps_script(action, params=None):
    """เรียก Google Apps Script API"""
    if not APPS_SCRIPT_URL:
        print("⚠️ APPS_SCRIPT_URL not set in .env")
        return {"error": "APPS_SCRIPT_URL not configured"}
    
    print(f"\n🚀 [API CALL] Action: {action}")
    try:
        url = f"{APPS_SCRIPT_URL}?action={action}"
        if params:
            for key, value in params.items():
                url += f"&{urllib.parse.quote(key)}={urllib.parse.quote(str(value))}"
        
        print(f"🔗 URL: {url}")
        if params:
            print(f"📦 Params: {params}")
        
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            raw_data = response.read().decode('utf-8')
            print(f"📥 Response Status: {response.status}")
            print(f"📄 Raw Body: {raw_data[:500]}...") # Print first 500 chars
            
            try:
                json_data = json.loads(raw_data)
                print(f"✅ Parsed JSON: {json_data}")
                return json_data
            except json.JSONDecodeError as e:
                print(f"❌ JSON Decode Error: {e}")
                print(f"☢️  Content causing error: {raw_data}")
                return {"error": "Invalid JSON response", "raw_content": raw_data}
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        print(f"⚠️ Apps Script call failed: {e}")
        return {"error": str(e)}

# ==========================================
# Bot Instance
# ==========================================
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Synced slash commands for {self.user}")

bot = MyBot()

# ==========================================
# HTTP Server with /check-jobs endpoint
# ==========================================
class SchedulerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/check-jobs':
            # เช็คและรัน jobs ที่ถึงเวลา
            result = asyncio.run_coroutine_threadsafe(
                execute_pending_jobs(), 
                bot.loop
            ).result(timeout=300)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            # Health check
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Discord Bot is running!')
    
    def log_message(self, format, *args):
        print(f"🌐 HTTP: {args[0]}")

def run_http_server():
    server = HTTPServer(('0.0.0.0', PORT), SchedulerHandler)
    print(f"🌐 HTTP server running on port {PORT}")
    print(f"📡 Endpoints: / (health), /check-jobs (scheduler)")
    server.serve_forever()

# ==========================================
# Job Execution Logic
# ==========================================
async def execute_pending_jobs():
    """เช็คและรัน jobs ที่ถึงเวลาแล้ว"""
    print("🔍 Checking for pending jobs...")
    
    # ดึง jobs ที่ถึงเวลาจาก Google Sheets
    result = call_apps_script('getPendingJobs')
    jobs = result.get('jobs', [])
    
    # Print Debug Logs from Apps Script
    debug_logs = result.get('debug_logs', [])
    if debug_logs:
        print(f"🐛 [Apps Script Debug] {' | '.join(debug_logs)}")
    
    if not jobs:
        print("✅ No pending jobs")
        return {"status": "ok", "jobs_executed": 0}
    
    print(f"📋 Found {len(jobs)} pending job(s)")
    executed = 0
    
    for job in jobs:
        try:
            print(f"🚀 Executing job: {job['job_id']}")
            
            # รัน bot_script
            from bot_script import run_bot
            import functools
            
            loop = asyncio.get_event_loop()
            run_bot_func = functools.partial(
                run_bot,
                date=job['booking_date'],
                duty=job['duty'],
                name=job['name']
            )
            
            bot_result = await loop.run_in_executor(None, run_bot_func)
            
            # อัปเดตสถานะ job
            status = bot_result.get('status', 'UNKNOWN')
            call_apps_script('markJobDone', {
                'job_id': job['job_id'],
                'result_status': status
            })
            
            # ส่งผลลัพธ์ไป Discord (ถ้ามี channel_id)
            if job.get('channel_id'):
                try:
                    channel = bot.get_channel(int(job['channel_id']))
                    if channel:
                        message_text = bot_result.get('message', 'No message')
                        screenshot_path = bot_result.get('screenshot')
                        
                        if status == "SUCCESS":
                            summary = f"✅ **จองสำเร็จ!**\n📝 {message_text}"
                        elif status == "FAILED":
                            summary = f"❌ **จองไม่สำเร็จ!**\n📝 {message_text}"
                        else:
                            summary = f"⚠️ **สถานะ: {status}**\n📝 {message_text}"
                        
                        content = f"🏁 **บอทรันเสร็จแล้ว!**\n📋 Job: `{job['job_id']}`\n🧹 หน้าที่: `{job['duty']}`\n✍️ ชื่อ: `{job['name']}`\n\n{summary}"
                        
                        if screenshot_path and os.path.exists(screenshot_path):
                            file = discord.File(screenshot_path, filename="booking_result.png")
                            await channel.send(content=content, file=file)
                        else:
                            await channel.send(content)
                except Exception as e:
                    print(f"⚠️ Failed to send Discord message: {e}")
            
            executed += 1
            print(f"✅ Job {job['job_id']} completed with status: {status}")
            
        except Exception as e:
            print(f"❌ Job {job['job_id']} failed: {e}")
            call_apps_script('markJobDone', {
                'job_id': job['job_id'],
                'result_status': 'ERROR'
            })
    
    return {"status": "ok", "jobs_executed": executed}

# ==========================================
# Discord Events
# ==========================================
@bot.event
async def on_ready():
    print(f"🤖 Discord Bot is ready as {bot.user}")

# ==========================================
# Slash Commands
# ==========================================
@bot.tree.command(name="help-queue", description="ดูวิธีใช้งานบอทจองเวร")
async def help_queue(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 คู่มือการใช้งานบอทจองเวร",
        description="วิธีสั่งงานบอทให้จองเวรอัตโนมัติ",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="📌 คำสั่งหลัก",
        value="`/queue 08:30`\n(ตั้งเวลาจองเวลา 08:30)",
        inline=False
    )
    
    embed.add_field(
        name="📅 ระบุวันที่",
        value="`date_str`: ระบุวันที่ (เช่น 21/01/69)\nถ้าไม่ใส่ = วันนี้หรือพรุ่งนี้",
        inline=False
    )
    
    embed.add_field(
        name="🧹 เลือกหน้าที่/ชื่อ",
        value="`duty_select`: เลือกจากลิสต์\n`name_input`: พิมพ์ชื่อเอง",
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ หมายเหตุ",
        value="- คิวจะถูกบันทึกไว้ใน Google Sheets\n- บอทจะทำงานตามเวลาที่ตั้งไว้ (±1 นาที)\n- แม้บอท restart ก็ไม่หาย!",
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
    # Defer interaction เพื่อป้องกัน timeout (3 วินาที)
    await interaction.response.defer()
    
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

        scheduled_date = target_datetime.strftime("%Y-%m-%d")
        scheduled_time = time_str
        
        # 2. คำนวณวันที่ที่จะจอง (Booking Date)
        if date_str:
            try:
                parts = date_str.split('/')
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                
                # แปลง พ.ศ. 2 หลัก -> ค.ศ. 4 หลัก
                if y < 100:
                    y_ad = 1957 + y
                elif y > 2400:
                    y_ad = y - 543
                else:
                    y_ad = y
                
                booking_date_obj = datetime.date(y_ad, m, d)
                booking_date = booking_date_obj.strftime("%Y-%m-%d")
                date_note = "(ระบุเอง)"
            except:
                await interaction.followup.send("❌ รูปแบบวันที่ไม่ถูกต้อง! กรุณาใช้ dd/mm/yy (เช่น 21/01/69)", ephemeral=True)
                return
        else:
            booking_date = scheduled_date
            date_note = f"({day_text})"
        
        # 3. ดึงค่า Config และกำหนดค่า
        from bot_script import TARGET_DUTY as ENV_DUTY, TARGET_NAME as ENV_NAME
        
        final_duty = duty_select.value if duty_select else ENV_DUTY
        final_name = name_input if name_input else ENV_NAME
        channel_id = str(interaction.channel_id)
        
        # 4. บันทึกลง Google Sheets
        result = call_apps_script('addScheduledJob', {
            'scheduled_date': scheduled_date,
            'scheduled_time': scheduled_time,
            'booking_date': booking_date,
            'duty': final_duty,
            'name': final_name,
            'channel_id': channel_id
        })
        
        if not result.get('success'):
            await interaction.followup.send(f"❌ บันทึกคิวไม่สำเร็จ: {result.get('message', 'Unknown error')}", ephemeral=True)
            return
        
        job_id = result.get('job_id', 'N/A')
        
        # 5. ส่งข้อความยืนยัน
        embed = discord.Embed(
            title="✅ บันทึกคิวสำเร็จ!",
            description=f"บอทจะทำงาน**{day_text}** เวลา **{time_str}** น.",
            color=discord.Color.green()
        )
        embed.add_field(name="🆔 Job ID", value=f"`{job_id}`", inline=True)
        embed.add_field(name="📅 วันที่จอง", value=f"`{booking_date}` {date_note}", inline=True)
        embed.add_field(name="🧹 หน้าที่", value=final_duty, inline=True)
        embed.add_field(name="✍️ ชื่อ", value=final_name, inline=True)
        embed.set_footer(text="💡 คิวนี้จะไม่หายแม้บอท restart!")
        
        await interaction.followup.send(embed=embed)
        
        # Calculate wait time and schedule job execution
        now = datetime.datetime.now(THAI_TZ)
        wait_seconds = (target_datetime - now).total_seconds()
        
        if wait_seconds > 0:
            print(f"⏰ Job scheduled. Will execute in {wait_seconds:.0f} seconds...")
            async def delayed_job_check():
                await asyncio.sleep(wait_seconds + 5)  # Add 5s buffer
                print("⚡ Time reached! Triggering job check...")
                await execute_pending_jobs()
            bot.loop.create_task(delayed_job_check())
        else:
            # Already past time, execute immediately
            print("⚡ Triggering immediate job check...")
            bot.loop.create_task(execute_pending_jobs())

    except ValueError:
        await interaction.followup.send("❌ รูปแบบเวลาไม่ถูกต้อง! กรุณาใช้ HH:MM (เช่น 08:00)", ephemeral=True)
    except Exception as e:
        try:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {str(e)}", ephemeral=True)
        except:
            print(f"❌ Error: {e}")

@bot.tree.command(name="list-jobs", description="ดูรายการคิวที่รอทำ")
async def list_jobs(interaction: discord.Interaction):
    await interaction.response.defer()
    
    result = call_apps_script('getPendingJobs')
    jobs = result.get('jobs', [])
    
    if not jobs:
        await interaction.followup.send("📭 ไม่มีคิวที่รอทำ", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📋 รายการคิวที่รอทำ",
        color=discord.Color.blue()
    )
    
    for job in jobs[:10]:  # แสดงแค่ 10 อันแรก
        embed.add_field(
            name=f"🔹 {job['scheduled_date']} {job['scheduled_time']}",
            value=f"หน้าที่: {job['duty']} | ชื่อ: {job['name']}\nID: `{job['job_id']}`",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="cancel-job", description="ยกเลิกคิว")
@app_commands.describe(job_id="Job ID ที่ต้องการยกเลิก")
async def cancel_job(interaction: discord.Interaction, job_id: str):
    await interaction.response.defer()
    
    result = call_apps_script('cancelJob', {'job_id': job_id})
    
    if result.get('success'):
        await interaction.followup.send(f"✅ ยกเลิกคิว `{job_id}` สำเร็จ!")
    else:
        await interaction.followup.send(f"❌ ยกเลิกไม่สำเร็จ: {result.get('message')}", ephemeral=True)

# ==========================================
# Main
# ==========================================
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: ไม่พบ DISCORD_TOKEN ในไฟล์ .env!")
        print("กรุณาสร้างไฟล์ .env แล้วใส่ DISCORD_TOKEN=your_token_here")
    elif not APPS_SCRIPT_URL:
        print("⚠️ Warning: ไม่พบ APPS_SCRIPT_URL ในไฟล์ .env!")
        print("กรุณาใส่ URL ของ Google Apps Script")
    else:
        # เริ่ม HTTP server ใน background thread
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        
        # รัน Discord bot
        bot.run(TOKEN)
