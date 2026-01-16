function doGet(e) {
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
