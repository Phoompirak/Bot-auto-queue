function doGet(e) {
  // ป้องกัน error เมื่อกด Run ใน Editor (e จะเป็น undefined)
  if (!e || !e.parameter) {
    return ContentService
      .createTextOutput(JSON.stringify({ error: 'No parameters provided. Use web URL to call this API.' }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  
  const action = e.parameter.action;
  
  // ถ้าไม่มี action ให้แสดงหน้า HTML
  if (!action) {
    return HtmlService.createHtmlOutputFromFile('index')
      .setTitle('ระบบจองเวร 5/1')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  }
  
  // จัดการ API requests
  let result = {};
  
  switch (action) {
    case 'getReservations':
      result = { reservations: getTodayReservations(e.parameter.date) };
      break;
    case 'saveReservation':
      result = saveReservation({
        date: e.parameter.date,
        duty: e.parameter.duty,
        name: e.parameter.name
      });
      break;
    case 'getAvailableDuties':
      result = { duties: getAvailableDuties(e.parameter.date) };
      break;
    // === Scheduled Jobs API ===
    case 'addScheduledJob':
      result = addScheduledJob({
        scheduled_date: e.parameter.scheduled_date,
        scheduled_time: e.parameter.scheduled_time,
        booking_date: e.parameter.booking_date,
        duty: e.parameter.duty,
        name: e.parameter.name,
        channel_id: e.parameter.channel_id
      });
      break;
    case 'getPendingJobs':
      result = getPendingJobs();
      break;
    case 'markJobDone':
      result = markJobDone(e.parameter.job_id, e.parameter.result_status);
      break;
    case 'cancelJob':
      result = cancelJob(e.parameter.job_id);
      break;
    default:
      result = { error: 'Unknown action' };
  }
  
  return ContentService
    .createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

// รายการหน้าที่ทั้งหมด
const ALL_DUTIES = [
  "เทขยะ1",
  "เทขยะ2",
  "กวาดห้อง1",
  "กวาดห้อง2",
  "กวาดห้อง3",
  "กวาดห้อง4",
  "จัดโต๊ะปิดไฟปิดพัดลม",
  "ลบกระดานปิดหน้าต่าง"
];

/**
 * ตรวจสอบว่าเป็นวันพฤหัสบดีหรือวันศุกร์หรือไม่
 */
function isThursdayOrFriday(dateString) {
  const date = new Date(dateString);
  const day = date.getDay();
  return day === 4 || day === 5;
}

/**
 * ดึงรายการหน้าที่ที่ยังว่างในวันที่ระบุ
 */
function getAvailableDuties(dateString) {
  const sheet = getSheet();
  const data = sheet.getDataRange().getValues();
  const bookedDuties = [];
  
  for (let i = 1; i < data.length; i++) {
    const rowDate = Utilities.formatDate(new Date(data[i][1]), Session.getScriptTimeZone(), "yyyy-MM-dd");
    if (rowDate === dateString) {
      bookedDuties.push(data[i][2]);
    }
  }
  
  const isThuFri = isThursdayOrFriday(dateString);
  
  return ALL_DUTIES.filter(duty => {
    if (isThuFri && duty.includes("กวาดห้อง4")) {
      return false;
    }
    return !bookedDuties.includes(duty);
  });
}

/**
 * ตรวจสอบการจองซ้ำ
 */
function checkDuplicateBooking(dateString, duty) {
  const sheet = getSheet();
  const data = sheet.getDataRange().getValues();
  
  for (let i = 1; i < data.length; i++) {
    const rowDate = Utilities.formatDate(new Date(data[i][1]), Session.getScriptTimeZone(), "yyyy-MM-dd");
    const rowDuty = data[i][2];
    if (rowDate === dateString && rowDuty === duty) {
      return true;
    }
  }
  return false;
}

/**
 * บันทึกการจอง
 */
function saveReservation(formData) {
  try {
    const isDuplicate = checkDuplicateBooking(formData.date, formData.duty);
    if (isDuplicate) {
      return { success: false, message: "หน้าที่นี้ถูกจองไปแล้ว" };
    }
    
    const sheet = getSheet();
    sheet.appendRow([
      new Date(),
      formData.date,
      formData.duty,
      formData.name
    ]);
    
    return { success: true, message: "บันทึกการจองสำเร็จ!" };
  } catch (e) {
    return { success: false, message: "เกิดข้อผิดพลาด: " + e.toString() };
  }
}

/**
 * ดึงรายการการจองของวันที่ระบุ
 */
function getTodayReservations(dateString) {
  const sheet = getSheet();
  const data = sheet.getDataRange().getValues();
  const reservations = [];
  
  for (let i = 1; i < data.length; i++) {
    const rowDate = Utilities.formatDate(new Date(data[i][1]), Session.getScriptTimeZone(), "yyyy-MM-dd");
    if (rowDate === dateString) {
      reservations.push({
        duty: data[i][2],
        name: data[i][3]
      });
    }
  }
  return reservations;
}

/**
 * จัดการ Google Sheet (สร้างถ้ายังไม่มี)
 */
function getSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName("Reservations");
  if (!sheet) {
    sheet = ss.insertSheet("Reservations");
    sheet.appendRow(["Timestamp", "Date", "Duty", "Name"]);
    sheet.getRange(1, 1, 1, 4).setFontWeight("bold").setBackground("#f3f3f3");
    sheet.setFrozenRows(1);
  }
  return sheet;
}

// ============================================
// SCHEDULED JOBS FUNCTIONS
// ============================================

/**
 * จัดการ ScheduledJobs Sheet (สร้างถ้ายังไม่มี)
 */
function getScheduledJobsSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName("ScheduledJobs");
  if (!sheet) {
    sheet = ss.insertSheet("ScheduledJobs");
    sheet.appendRow(["JobID", "CreatedAt", "ScheduledDate", "ScheduledTime", "BookingDate", "Duty", "Name", "ChannelID", "Status"]);
    sheet.getRange(1, 1, 1, 9).setFontWeight("bold").setBackground("#d9ead3");
    sheet.setFrozenRows(1);
  }
  return sheet;
}

/**
 * เพิ่ม Scheduled Job
 */
function addScheduledJob(data) {
  try {
    const sheet = getScheduledJobsSheet();
    const jobId = "JOB_" + new Date().getTime();
    
    sheet.appendRow([
      jobId,
      new Date(),
      data.scheduled_date,  // วันที่จะให้บอททำงาน (YYYY-MM-DD)
      data.scheduled_time,  // เวลาที่จะให้บอททำงาน (HH:MM)
      data.booking_date,    // วันที่จะจอง (YYYY-MM-DD)
      data.duty,
      data.name,
      data.channel_id || "",
      "PENDING"
    ]);
    
    return { success: true, job_id: jobId, message: "บันทึกคิวสำเร็จ!" };
  } catch (e) {
    return { success: false, message: "เกิดข้อผิดพลาด: " + e.toString() };
  }
}

/**
 * ดึง Jobs ที่ถึงเวลาแล้ว (PENDING และ เวลาปัจจุบัน >= เวลาที่ตั้งไว้)
 */
function getPendingJobs() {
  const sheet = getScheduledJobsSheet();
  const data = sheet.getDataRange().getValues();
  const pendingJobs = [];
  const debugLogs = [];
  
  const now = new Date();
  const TIMEZONE = "Asia/Bangkok"; // Force Bangkok Timezone
  const nowDate = Utilities.formatDate(now, TIMEZONE, "yyyy-MM-dd");
  const nowTime = Utilities.formatDate(now, TIMEZONE, "HH:mm");
  
  debugLogs.push(`Server Time: ${nowDate} ${nowTime}`);
  
  for (let i = 1; i < data.length; i++) {
    const status = data[i][8];
    if (status !== "PENDING") {
      // debugLogs.push(`Row ${i+1}: Skipped (Status=${status})`);
      continue;
    }
    
    let scheduledDate = data[i][2];
    let scheduledTime = data[i][3];
    
    // Original values for debug
    const rawDate = scheduledDate;
    const rawTime = scheduledTime;
    
    // Convert Date objects to strings
    if (scheduledDate instanceof Date) {
      scheduledDate = Utilities.formatDate(scheduledDate, TIMEZONE, "yyyy-MM-dd");
    }
    
    if (scheduledTime instanceof Date) {
      scheduledTime = Utilities.formatDate(scheduledTime, TIMEZONE, "HH:mm");
    } else {
       scheduledTime = String(scheduledTime).substring(0, 5); 
    }
    
    const isDue = (scheduledDate < nowDate || (scheduledDate === nowDate && scheduledTime <= nowTime));
    
    debugLogs.push(`Row ${i+1}: Due=${isDue} | Sch=${scheduledDate} ${scheduledTime} | Now=${nowDate} ${nowTime} | RawTimeType=${typeof rawTime}`);

    if (isDue) {
      // Format booking_date if it's a Date object
      let bookingDate = data[i][4];
      if (bookingDate instanceof Date) {
        bookingDate = Utilities.formatDate(bookingDate, TIMEZONE, "yyyy-MM-dd");
      }
      
      pendingJobs.push({
        job_id: data[i][0],
        row_index: i + 1,
        scheduled_date: scheduledDate,
        scheduled_time: scheduledTime,
        booking_date: bookingDate,
        duty: data[i][5],
        name: data[i][6],
        channel_id: data[i][7]
      });
    }
  }
  
  return { jobs: pendingJobs, debug_logs: debugLogs };
}

/**
 * อัปเดตสถานะ Job เป็น DONE หรือ FAILED
 */
function markJobDone(jobId, resultStatus) {
  try {
    const sheet = getScheduledJobsSheet();
    const data = sheet.getDataRange().getValues();
    
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] === jobId) {
        sheet.getRange(i + 1, 9).setValue(resultStatus || "DONE");
        return { success: true, message: "อัปเดตสถานะสำเร็จ" };
      }
    }
    
    return { success: false, message: "ไม่พบ Job ID: " + jobId };
  } catch (e) {
    return { success: false, message: "เกิดข้อผิดพลาด: " + e.toString() };
  }
}

/**
 * ยกเลิก Job
 */
function cancelJob(jobId) {
  return markJobDone(jobId, "CANCELLED");
}
