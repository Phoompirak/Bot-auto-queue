from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ==========================================
# Initial Variables (ดึงค่าจาก .env)
# ==========================================
TARGET_URL = os.getenv("TARGET_URL", "https://test-qeue.onrender.com/")
TARGET_DATE = os.getenv("TARGET_DATE", "2026-01-16")
TARGET_DUTY = os.getenv("TARGET_DUTY", "ลบกระดานปิดหน้าต่าง")
TARGET_NAME = os.getenv("TARGET_NAME", "ต่อ")
DELAY_SECONDS = int(os.getenv("DELAY_SECONDS", 1))

def run_bot(url=None, date=None, duty=None, name=None, callback=None):
    # Helper to log to both console and callback
    def log(msg):
        print(msg)
        if callback:
            try:
                callback(msg)
            except Exception as e:
                print(f"⚠️ Callback failed: {e}")

    # ใช้ค่าจาก .env ถ้าไม่ได้ระบุ parameter
    url = url or TARGET_URL
    date = date or TARGET_DATE
    duty = duty or TARGET_DUTY
    name = name or TARGET_NAME
    
    log("=" * 50)
    log("🤖 BOT SCRIPT STARTED")
    log("=" * 50)
    log(f"📋 CONFIG FROM .env:")
    log(f"   🌐 TARGET_URL  = {url}")
    log(f"   📆 TARGET_DATE = {date}")
    log(f"   🧹 TARGET_DUTY = {duty}")
    log(f"   ✍️  TARGET_NAME = {name}")
    log(f"   ⏱️  DELAY       = {DELAY_SECONDS}s")
    log("=" * 50)
    
    log("[STEP 1/6] Setting up Chrome Driver...")
    
    # Setup Chrome Driver
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    options.add_argument("--headless") # Render ต้องใช้ Headless Mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=options)
        log("[STEP 1/6] ✅ Chrome Driver ready (local)")
    except Exception as e:
        log(f"[STEP 1/6] ⚠️ Local driver failed: {e}")
        log("[STEP 1/6] 🔧 Downloading ChromeDriver via webdriver-manager...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("[STEP 1/6] ✅ Chrome Driver ready (downloaded)")
    
    try:
        # 1. เข้าสู่หน้าเว็บ
        print(f"[STEP 2/6] Opening URL: {url}")
        driver.get(url)
        driver.execute_script("document.body.style.zoom='70%'")
        time.sleep(DELAY_SECONDS)
        print("[STEP 2/6] ✅ Page loaded")
        
        # ส่วน iframe (สำหรับ Google Apps Script)
        try:
            WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "sandboxFrame")))
            print("[STEP 2/6] Switched to sandboxFrame")
            WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "userHtmlFrame")))
            print("[STEP 2/6] Switched to userHtmlFrame")
        except:
            print("[STEP 2/6] No iframe detected (running on standalone HTML)")

        # 2. ป้อนวันที่
        print(f"[STEP 3/6] Setting date: {date}")
        date_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="date"]'))
        )
        driver.execute_script(f"arguments[0].value = '{date}';", date_input)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", date_input)
        time.sleep(DELAY_SECONDS)
        print("[STEP 3/6] ✅ Date set")
        
        # 3. เลือกหน้าที่
        print(f"[STEP 4/6] Selecting duty: {duty}")
        duty_select_elem = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="duty"]'))
        )
        
        WebDriverWait(driver, 10).until(
            lambda d: duty_select_elem.get_attribute("disabled") is None
        )
        
        select = Select(duty_select_elem)
        try:
            select.select_by_visible_text(duty)
            print(f"[STEP 4/6] ✅ Selected: {duty}")
        except Exception:
            print(f"[STEP 4/6] ❌ Duty '{duty}' not found!")
            available_options = [o.text for o in select.options]
            print(f"[STEP 4/6] Available options: {available_options}")
            
            # Fallback
            fallback_duty = "ลบกระดานปิดหน้าต่าง"
            if duty != fallback_duty:
                try:
                    print(f"[STEP 4/6] Trying fallback: {fallback_duty}")
                    select.select_by_visible_text(fallback_duty)
                    print(f"[STEP 4/6] ✅ Fallback selected: {fallback_duty}")
                except Exception:
                    print(f"[STEP 4/6] ❌ Fallback also failed")
                    return "FAILED: No available duty"
            else:
                return "FAILED: Duty not available"

        time.sleep(DELAY_SECONDS)
        
        # 4. กรอกชื่อ
        print(f"[STEP 5/6] Entering name: {name}")
        name_input = driver.find_element(By.XPATH, '//*[@id="name"]')
        name_input.clear()
        name_input.send_keys(name)
        time.sleep(DELAY_SECONDS)
        print("[STEP 5/6] ✅ Name entered")
        
        # 5. กดปุ่มบันทึก
        print("[STEP 6/6] Clicking submit button...")
        submit_btn = driver.find_element(By.XPATH, '//*[@id="submitBtn"]')
        submit_btn.click()
        
        # 6. ตรวจสอบผลลัพธ์
        try:
            success_msg = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "success"))
            )
            print(f"[STEP 6/6] 🎉 SUCCESS: {success_msg.text}")
            return f"SUCCESS: {success_msg.text}"
        except:
            print("[STEP 6/6] ⚠️ No success message detected")
            return "UNKNOWN: No success message"

    except Exception as e:
        print(f"[ERROR] ❌ Bot crashed: {e}")
        return f"ERROR: {e}"
    finally:
        print("=" * 50)
        print("🏁 BOT SCRIPT FINISHED")
        print("=" * 50)
        time.sleep(3)
        driver.quit()

if __name__ == "__main__":
    result = run_bot()
    print(f"\n📊 FINAL RESULT: {result}")
