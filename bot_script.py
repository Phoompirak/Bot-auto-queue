from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ==========================================
# Initial Variables (ดึงค่าจาก .env)
# ==========================================
TARGET_URL = os.getenv("TARGET_URL", "https://test-qeue.onrender.com/")
TARGET_DUTY = os.getenv("TARGET_DUTY", "ลบกระดานปิดหน้าต่าง")
TARGET_NAME = os.getenv("TARGET_NAME", "ต่อ")
DELAY_SECONDS = int(os.getenv("DELAY_SECONDS", 1))

def get_today_date():
    """คืนค่าวันที่ปัจจุบันในรูปแบบ YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")

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
    # ถ้าไม่ได้ระบุวันที่ (None) ให้ใช้วันที่ปัจจุบัน
    date = date or get_today_date()
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

    options = webdriver.ChromeOptions()

    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
        log("☁️ Running on Linux mode (CHROME_BIN set)")
    else:
        log("💻 Running on Local mode")

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--mute-audio")

    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--no-first-run")
    options.add_argument("--safebrowsing-disable-auto-update")

    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--js-flags=--max-old-space-size=128")

    options.add_argument("--window-size=1280,720")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    })

    options.page_load_strategy = "eager"
    
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
                    log(f"[STEP 4/6] Trying fallback: {fallback_duty}")
                    select.select_by_visible_text(fallback_duty)
                    log(f"[STEP 4/6] ✅ Fallback selected: {fallback_duty}")
                except Exception:
                    log(f"[STEP 4/6] ❌ Fallback also failed")
                    return {"status": "FAILED", "message": "No available duty", "screenshot": None}
            else:
                return {"status": "FAILED", "message": "Duty not available", "screenshot": None}

        time.sleep(DELAY_SECONDS)
        
        # 4. กรอกชื่อ
        log(f"[STEP 5/6] Entering name: {name}")
        name_input = driver.find_element(By.XPATH, '//*[@id="name"]')
        name_input.clear()
        name_input.send_keys(name)
        time.sleep(DELAY_SECONDS)
        log("[STEP 5/6] ✅ Name entered")
        
        # 5. กดปุ่มบันทึก
        log("[STEP 6/6] Clicking submit button...")
        submit_btn = driver.find_element(By.XPATH, '//*[@id="submitBtn"]')
        submit_btn.click()
        
        # 6. ตรวจสอบผลลัพธ์
        screenshot_path = None
        result_status = "UNKNOWN"
        result_message = "No success message"
        
        try:
            success_msg = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "success"))
            )
            log(f"[STEP 6/6] 🎉 SUCCESS: {success_msg.text}")
            result_status = "SUCCESS"
            result_message = success_msg.text
        except:
             # ลองหา error message
            try:
                error_msg = driver.find_element(By.CLASS_NAME, "error")
                log(f"[STEP 6/6] ❌ FAILED: {error_msg.text}")
                result_status = "FAILED"
                result_message = error_msg.text
            except:
                log("[STEP 6/6] ⚠️ No success/error message detected")
        
        # 7. Reload หน้าเว็บ และ Capture Full Page Screenshot
        log("[STEP 7/7] Reloading page and capturing full screenshot...")
        screenshot_path = capture_full_page_screenshot(driver, log)
        
        return {"status": result_status, "message": result_message, "screenshot": screenshot_path}

    except Exception as e:
        error_msg = str(e) or "Unknown error"
        log(f"[ERROR] ❌ Bot crashed: {error_msg}")
        
        # พยายามถ่าย Screenshot ตอน Error ด้วย
        try:
            screenshot_path = capture_full_page_screenshot(driver, log, prefix="error")
        except:
            screenshot_path = None
            
        return {"status": "ERROR", "message": error_msg, "screenshot": screenshot_path}
    finally:
        log("=" * 50)
        log("🏁 BOT SCRIPT FINISHED")
        log("=" * 50)
        time.sleep(0.5)
        try:
            driver.quit()
        except:
            pass

def capture_full_page_screenshot(driver, log_func, prefix="booking"):
    """ถ่าย Screenshot แบบ viewport (ไม่ resize window เพื่อประหยัด RAM)"""
    try:
        if prefix == "booking":
            time.sleep(1)
            driver.refresh()
            log_func("[SCREENSHOT] Waiting 3s for page load...")
            time.sleep(3)

        driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(0.3)

        screenshots_dir = os.path.join(os.path.dirname(__file__), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(screenshots_dir, f"{prefix}_{timestamp}.png")
        driver.save_screenshot(screenshot_path)
        log_func(f"[SCREENSHOT] ✅ Saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        log_func(f"[SCREENSHOT] ⚠️ Failed: {e}")
        return None

if __name__ == "__main__":
    result = run_bot()
    print(f"\n📊 FINAL RESULT: {result}")

