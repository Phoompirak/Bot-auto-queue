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
TARGET_URL = os.getenv("TARGET_URL", "http://localhost:3000")
TARGET_DATE = os.getenv("TARGET_DATE", "2026-01-16")
TARGET_DUTY = os.getenv("TARGET_DUTY", "ลบกระดานปิดหน้าต่าง")
TARGET_NAME = os.getenv("TARGET_NAME", "ต่อ")
DELAY_SECONDS = int(os.getenv("DELAY_SECONDS", 1))

def run_bot(url=TARGET_URL, date=TARGET_DATE, duty=TARGET_DUTY, name=TARGET_NAME):
    print(f"🚀 สตาร์ทบอทจองเวรสำหรับ {name}...")
    
    # Setup Chrome Driver
    options = webdriver.ChromeOptions()
    
    # ตั้งค่าพิเศษเพื่อให้ Browser ไม่ปิดเองทันที และซ่อนแถบควบคุมสถานะบอท
    options.add_experimental_option("detach", True)
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    
    # options.add_argument("--headless") # เปิดทิ้งไว้หากไม่ต้องการให้เห็นหน้าต่าง Browser
    
    try:
        # พยายามเปิด Driver (เวอร์ชันปกติ)
        driver = webdriver.Chrome(options=options)
    except Exception:
        # ถ้าเวอร์ชันไม่ตรง ให้ใช้ ChromeDriverManager ช่วยดาวน์โหลด
        print("🔧 กำลังอัปเดต ChromeDriver ให้ตรงกับ Browser...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # 1. เข้าสู่หน้าเว็บ
        print(f"🌐 กำลังเปิดเว็บ: {url}")
        driver.get(url)
        
        # ปรับซูมหน้าเว็บเพื่อให้เห็นข้อมูลครบถ้วน
        driver.execute_script("document.body.style.zoom='70%'")
        time.sleep(DELAY_SECONDS)
        
        # ส่วนสำหรับการจัดการ iframe
        try:
             WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "sandboxFrame")))
             print("Switched to sandboxFrame")
             WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "userHtmlFrame")))
             print("Switched to userHtmlFrame")
        except:
             pass

        # 2. ป้อนวันที่
        print(f"📅 ระบุวันที่: {date}")
        date_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="date"]'))
        )
        driver.execute_script(f"arguments[0].value = '{date}';", date_input)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", date_input)
        
        time.sleep(DELAY_SECONDS) 
        
        # 3. เลือกหน้าที่
        print(f"🧹 เลือกหน้าที่: {duty}")
        duty_select_elem = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="duty"]'))
        )
        
        WebDriverWait(driver, 10).until(
            lambda d: duty_select_elem.get_attribute("disabled") is None
        )
        
        select = Select(duty_select_elem)
        try:
            select.select_by_visible_text(duty)
            print(f"✅ เลือก {duty} สำเร็จ")
        except Exception:
            print(f"❌ ไม่พบหน้าที่ '{duty}' ในรายการเวรที่ว่าง!")
            
            # Fallback logic
            fallback_duty = "ลบกระดานปิดหน้าต่าง"
            if duty != fallback_duty:
                try:
                    print(f"🔄 พยายามเลือกหน้าที่สำรอง: {fallback_duty}")
                    select.select_by_visible_text(fallback_duty)
                    print(f"✅ เลือก {fallback_duty} สำเร็จ")
                except Exception:
                    print(f"❌ ไม่พบหน้าที่สำรอง '{fallback_duty}' เช่นกัน")
                    time.sleep(DELAY_SECONDS)
                    available_options = [o.text for o in select.options]
                    print(f"รายการที่ว่างตอนนี้: {available_options}")
                    return
            else:
                return

        time.sleep(DELAY_SECONDS)
        
        # 4. กรอกชื่อผู้จอง
        print(f"✍️ กรอกชื่อ: {name}")
        name_input = driver.find_element(By.XPATH, '//*[@id="name"]')
        name_input.clear()
        name_input.send_keys(name)
        
        time.sleep(DELAY_SECONDS)
        
        # 5. กดปุ่มบันทึก
        print("🚀 กำลังส่งข้อมูล (กดปุ่มบันทึก)...")
        submit_btn = driver.find_element(By.XPATH, '//*[@id="submitBtn"]')
        submit_btn.click()
        
        # 6. ตรวจสอบผลลัพธ์
        try:
            success_msg = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "success"))
            )
            print(f"🎉 บรรลุเป้าหมาย: {success_msg.text}")
        except:
            print("⚠️ ไม่ได้รับข้อความยืนยันจากหน้าเว็บ (อาจจะช้าหรือมีปัญหา)")
            
        print("🏁 จบการทำงาน (Browser จะเปิดค้างไว้ตามที่ตั้งค่า detach)")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดระหว่างรันบอท: {e}")
    finally:
        print("🏁 จบการทำงาน ปิด Browser...")
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    run_bot()
