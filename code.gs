function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('ระบบจองเวร 5/1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// รายการหน้าที่ทั้งหมด
const ALL_DUTIES = [
  "กวาดห้อง 1",
  "กวาดห้อง 2",
  "กวาดห้อง 3",
  "กวาดห้อง 4",
  "ถูห้อง 1",
  "ถูห้อง 2",
  "เช็ดกระจก",
  "จัดโต๊ะ",
  "ทิ้งขยะ"
];

/**
 * ตรวจสอบว่าเป็นวันพฤหัสบดีหรือวันศุกร์หรือไม่
 */
function isThursdayOrFriday(dateString) {
  const date = new Date(dateString);
  const day = date.getDay(); // 0 = Sunday, 4 = Thursday, 5 = Friday
  return day === 4 || day === 5;
}

/**
 * ดึงรายการหน้าที่ที่ยังว่างในวันที่ระบุ
 */
function getAvailableDuties(dateString) {
  const sheet = getSheet();
  const data = sheet.getDataRange().getValues();
  const bookedDuties = [];
  
  // เริ่มจากแถวที่ 2 (index 1) เพื่อข้าม header
  for (let i = 1; i < data.length; i++) {
    const rowDate = Utilities.formatDate(new Date(data[i][1]), Session.getScriptTimeZone(), "yyyy-MM-dd");
    if (rowDate === dateString) {
      bookedDuties.push(data[i][2]); // Duty อยู่ column 3 (index 2)
    }
  }
  
  const isThuFri = isThursdayOrFriday(dateString);
  
  return ALL_DUTIES.filter(duty => {
    // เงื่อนไขพิเศษ: กวาดห้อง 4 ไม่ได้ในวันพฤหัส/ศุกร์
    if (isThuFri && duty === "กวาดห้อง 4") {
      return false;
    }
    // ต้องไม่ถูกจองไปแล้ว
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
      new Date(), // Timestamp
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
 * ดึงรายการการจองของวันนี้
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
