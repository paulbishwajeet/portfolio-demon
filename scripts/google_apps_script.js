/**
 * Google Apps Script — Refresh prices in the Holdings tab.
 *
 * This runs server-side inside Google Sheets on a timed trigger.
 * It fetches live prices via GOOGLEFINANCE and writes them as plain
 * values into the current_price column so they're always fresh —
 * even when the sheet isn't open in a browser.
 *
 * SETUP:
 *   1. Open your Google Sheet
 *   2. Extensions → Apps Script
 *   3. Delete the default code, paste this entire file
 *   4. Click the clock icon (Triggers) on the left sidebar
 *   5. + Add Trigger:
 *        Function: refreshPrices
 *        Event source: Time-driven
 *        Type: Day timer
 *        Time: 6am to 7am (runs before the 9am ET GitHub Action)
 *   6. Save — authorize when prompted
 *
 * The trigger runs once per day. You can also run it manually from
 * the Apps Script editor (select refreshPrices → click Run).
 */

function refreshPrices() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Holdings");
  if (!sheet) {
    Logger.log("Holdings tab not found");
    return;
  }

  var data = sheet.getDataRange().getValues();
  var header = data[0];

  // Find column indexes
  var symbolCol = header.indexOf("symbol");
  var priceCol = header.indexOf("current_price");

  if (symbolCol === -1 || priceCol === -1) {
    Logger.log("Could not find symbol or current_price columns");
    return;
  }

  var updated = 0;
  var failed = [];

  for (var i = 1; i < data.length; i++) {
    var symbol = data[i][symbolCol];
    if (!symbol || symbol === "") continue;

    try {
      var price = getPrice(symbol);
      if (price && price > 0) {
        // Write as plain value (row i+1 because sheets are 1-indexed)
        sheet.getRange(i + 1, priceCol + 1).setValue(price);
        updated++;
      } else {
        failed.push(symbol);
      }
    } catch (e) {
      Logger.log("Error fetching " + symbol + ": " + e.message);
      failed.push(symbol);
    }

    // Small delay to avoid hitting Google's rate limit
    Utilities.sleep(500);
  }

  // Write timestamp to a known cell so Python can verify freshness
  var configSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Portfolio_Config");
  if (configSheet) {
    setConfigValue(configSheet, "PRICES_LAST_REFRESHED", new Date().toISOString());
  }

  var msg = "Refreshed " + updated + " prices.";
  if (failed.length > 0) {
    msg += " Failed: " + failed.join(", ");
  }
  Logger.log(msg);
}


/**
 * Fetch a single price using a temporary GOOGLEFINANCE formula.
 * We write the formula to a scratch cell, read the result, then clear it.
 */
function getPrice(symbol) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var scratch = ss.getSheetByName("_scratch");

  // Create a hidden scratch sheet if it doesn't exist
  if (!scratch) {
    scratch = ss.insertSheet("_scratch");
    scratch.hideSheet();
  }

  var cell = scratch.getRange("A1");
  cell.setFormula('=GOOGLEFINANCE("' + symbol + '", "price")');

  // GOOGLEFINANCE needs a moment to resolve
  SpreadsheetApp.flush();
  Utilities.sleep(1000);

  var value = cell.getValue();
  cell.clearContent();

  if (typeof value === "number" && value > 0) {
    return value;
  }

  // Some mutual funds need a different format
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


/**
 * Set a key-value pair in the Portfolio_Config tab.
 */
function setConfigValue(configSheet, key, value) {
  var data = configSheet.getDataRange().getValues();
  for (var i = 0; i < data.length; i++) {
    if (data[i][0] === key) {
      configSheet.getRange(i + 1, 2).setValue(value);
      return;
    }
  }
  // Key not found — append it
  configSheet.appendRow([key, value]);
}
