/**
 * Google Apps Script — Refresh prices in the Holdings tab.
 *
 * Deployed as a web app so the Python job can trigger it via HTTP
 * before reading the sheet. No separate timer needed.
 *
 * SETUP:
 *   1. Open your Google Sheet → Extensions → Apps Script
 *   2. Delete the default code, paste this entire file
 *   3. Click Save
 *   4. Click Deploy → New deployment
 *   5. Type: Web app
 *      Execute as: Me
 *      Who has access: Anyone
 *   6. Click Deploy → Authorize when prompted
 *   7. Copy the Web app URL — it looks like:
 *      https://script.google.com/macros/s/AKfyc.../exec
 *   8. Add it as a GitHub secret: APPS_SCRIPT_URL
 *
 * The Python job calls this URL before reading the sheet.
 * You can also open the URL in a browser to trigger a manual refresh.
 */

function doGet(e) {
  try {
    var result = refreshPrices();
    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.message
    })).setMimeType(ContentService.MimeType.JSON);
  }
}


function refreshPrices() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Holdings");
  if (!sheet) {
    return { status: "error", message: "Holdings tab not found" };
  }

  var data = sheet.getDataRange().getValues();
  var header = data[0];

  var symbolCol = header.indexOf("symbol");
  var priceCol = header.indexOf("current_price");

  if (symbolCol === -1 || priceCol === -1) {
    return { status: "error", message: "Could not find symbol or current_price columns" };
  }

  var updated = 0;
  var failed = [];

  for (var i = 1; i < data.length; i++) {
    var symbol = data[i][symbolCol];
    if (!symbol || symbol === "") continue;

    try {
      var price = getPrice(symbol);
      if (price && price > 0) {
        sheet.getRange(i + 1, priceCol + 1).setValue(price);
        updated++;
      } else {
        failed.push(symbol);
      }
    } catch (e) {
      Logger.log("Error fetching " + symbol + ": " + e.message);
      failed.push(symbol);
    }

    Utilities.sleep(500);
  }

  // Write timestamp so Python can verify freshness
  var configSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Portfolio_Config");
  if (configSheet) {
    setConfigValue(configSheet, "PRICES_LAST_REFRESHED", new Date().toISOString());
  }

  return {
    status: "ok",
    updated: updated,
    failed: failed,
    timestamp: new Date().toISOString()
  };
}


/**
 * Fetch a single price using a temporary GOOGLEFINANCE formula.
 */
function getPrice(symbol) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var scratch = ss.getSheetByName("_scratch");

  if (!scratch) {
    scratch = ss.insertSheet("_scratch");
    scratch.hideSheet();
  }

  var cell = scratch.getRange("A1");
  cell.setFormula('=GOOGLEFINANCE("' + symbol + '", "price")');

  SpreadsheetApp.flush();
  Utilities.sleep(1000);

  var value = cell.getValue();
  cell.clearContent();

  if (typeof value === "number" && value > 0) {
    return value;
  }

  // Mutual fund fallback
  if (value === "" || value === "#N/A" || value === null) {
    cell.setFormula('=GOOGLEFINANCE("MUTF:' + symbol + '", "price")');
    SpreadsheetApp.flush();
    Utilities.sleep(1000);
    value = cell.getValue();
    cell.clearContent();

    if (typeof value === "number" && value > 0) {
      return value;
    }
  }

  return null;
}


function setConfigValue(configSheet, key, value) {
  var data = configSheet.getDataRange().getValues();
  for (var i = 0; i < data.length; i++) {
    if (data[i][0] === key) {
      configSheet.getRange(i + 1, 2).setValue(value);
      return;
    }
  }
  configSheet.appendRow([key, value]);
}
