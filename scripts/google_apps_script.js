/**
 * Google Apps Script — Refresh prices + compute 50d MA + SPY daily change.
 *
 * Deployed as a web app so the Python job triggers it via HTTP.
 * Returns all market data Python needs — no yfinance required.
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
 *   7. Copy the Web app URL
 *   8. Add it as a GitHub secret: APPS_SCRIPT_URL
 *
 * UPDATING after code changes:
 *   Deploy → Manage deployments → edit the existing deployment →
 *   Version: New version → Deploy
 */

function doGet(e) {
  try {
    var result = refreshAll();
    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.message
    })).setMimeType(ContentService.MimeType.JSON);
  }
}


function refreshAll() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Holdings");
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

  // Collect all symbols
  var symbols = [];
  for (var i = 1; i < data.length; i++) {
    var sym = data[i][symbolCol];
    if (sym && sym !== "") symbols.push(sym);
  }

  // Phase 1: Set live GOOGLEFINANCE price formulas (IFERROR tries MUTF: for mutual funds)
  for (var i = 1; i < data.length; i++) {
    var symbol = data[i][symbolCol];
    if (!symbol || symbol === "") continue;

    var cell = sheet.getRange(i + 1, priceCol + 1);
    var formula = '=IFERROR(GOOGLEFINANCE("' + symbol + '","price"),GOOGLEFINANCE("MUTF:' + symbol + '","price"))';
    cell.setFormula(formula);
  }

  SpreadsheetApp.flush();
  Utilities.sleep(3000);

  // Read resolved values for the response
  var updated = 0;
  var failed = [];
  var prices = {};

  for (var i = 1; i < data.length; i++) {
    var symbol = data[i][symbolCol];
    if (!symbol || symbol === "") continue;

    var value = sheet.getRange(i + 1, priceCol + 1).getValue();
    if (typeof value === "number" && value > 0) {
      prices[symbol] = value;
      updated++;
    } else {
      failed.push(symbol);
    }
  }

  // Phase 2: Fetch previous close prices (for day-over-day comparison)
  var prevPrices = {};
  for (var j = 0; j < symbols.length; j++) {
    try {
      var prev = getPrevClose(symbols[j]);
      if (prev !== null) prevPrices[symbols[j]] = prev;
    } catch (e) {
      Logger.log("Prev close error for " + symbols[j] + ": " + e.message);
    }
    Utilities.sleep(200);
  }

  // Phase 3: Compute 50-day moving averages
  var movingAverages = {};
  for (var j = 0; j < symbols.length; j++) {
    try {
      var ma = get50dMA(symbols[j]);
      if (ma !== null) {
        movingAverages[symbols[j]] = ma;
      }
    } catch (e) {
      Logger.log("MA error for " + symbols[j] + ": " + e.message);
    }
    Utilities.sleep(300);
  }

  // Phase 4: SPY daily change
  var spyChange = null;
  try {
    spyChange = getSpyDailyChange();
  } catch (e) {
    Logger.log("SPY change error: " + e.message);
  }

  // Write timestamp
  var configSheet = ss.getSheetByName("Portfolio_Config");
  if (configSheet) {
    setConfigValue(configSheet, "PRICES_LAST_REFRESHED", new Date().toISOString());
  }

  return {
    status: "ok",
    updated: updated,
    failed: failed,
    prev_prices: prevPrices,
    moving_averages: movingAverages,
    spy_daily_change_pct: spyChange,
    timestamp: new Date().toISOString()
  };
}


/**
 * Compute 50-day moving average using GOOGLEFINANCE historical data.
 */
function get50dMA(symbol) {
  var scratch = getScratchSheet();
  var cell = scratch.getRange("A1");

  // Fetch ~70 days of closing prices to ensure 50 trading days
  var endDate = new Date();
  var startDate = new Date();
  startDate.setDate(startDate.getDate() - 80);

  var startStr = formatDate(startDate);
  var endStr = formatDate(endDate);

  cell.setFormula('=GOOGLEFINANCE("' + symbol + '", "close", "' + startStr + '", "' + endStr + '", "DAILY")');
  SpreadsheetApp.flush();
  Utilities.sleep(1000);

  // GOOGLEFINANCE returns a 2D array: [[Date, Close], [date1, price1], ...]
  var range = scratch.getRange("A1:B80");
  var values = range.getValues();
  scratch.getRange("A1:B80").clearContent();

  var closePrices = [];
  for (var i = 1; i < values.length; i++) {
    var price = values[i][1];
    if (typeof price === "number" && price > 0) {
      closePrices.push(price);
    }
  }

  if (closePrices.length < 20) return null;

  // Take last 50 (or all if fewer)
  var window = Math.min(closePrices.length, 50);
  var slice = closePrices.slice(closePrices.length - window);
  var sum = 0;
  for (var k = 0; k < slice.length; k++) sum += slice[k];

  return Math.round((sum / slice.length) * 10000) / 10000;
}


/**
 * Get SPY's daily price change percentage.
 */
function getSpyDailyChange() {
  var scratch = getScratchSheet();
  var cell = scratch.getRange("A1");

  var endDate = new Date();
  var startDate = new Date();
  startDate.setDate(startDate.getDate() - 7);

  cell.setFormula('=GOOGLEFINANCE("SPY", "close", "' + formatDate(startDate) + '", "' + formatDate(endDate) + '", "DAILY")');
  SpreadsheetApp.flush();
  Utilities.sleep(1000);

  var range = scratch.getRange("A1:B10");
  var values = range.getValues();
  scratch.getRange("A1:B10").clearContent();

  var closes = [];
  for (var i = 1; i < values.length; i++) {
    if (typeof values[i][1] === "number" && values[i][1] > 0) {
      closes.push(values[i][1]);
    }
  }

  if (closes.length < 2) return null;

  var today = closes[closes.length - 1];
  var prev = closes[closes.length - 2];
  return Math.round((today - prev) / prev * 10000) / 100;
}


/**
 * Fetch previous trading day's closing price via GOOGLEFINANCE closeyest.
 */
function getPrevClose(symbol) {
  var scratch = getScratchSheet();
  var cell = scratch.getRange("A1");

  cell.setFormula('=IFERROR(GOOGLEFINANCE("' + symbol + '","closeyest"),GOOGLEFINANCE("MUTF:' + symbol + '","closeyest"))');
  SpreadsheetApp.flush();
  Utilities.sleep(600);

  var value = cell.getValue();
  cell.clearContent();

  if (typeof value === "number" && value > 0) return value;
  return null;
}


function getScratchSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var scratch = ss.getSheetByName("_scratch");
  if (!scratch) {
    scratch = ss.insertSheet("_scratch");
    scratch.hideSheet();
  }
  return scratch;
}


function formatDate(d) {
  return (d.getMonth() + 1) + "/" + d.getDate() + "/" + d.getFullYear();
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
