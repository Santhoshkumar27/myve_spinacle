const args = require('minimist')(process.argv.slice(2));
let userId = null;
if (args.user) {
  userId = args.user;
  console.log("🧠 Electron launched with user:", userId);
}
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const axios = require('axios');
const screenshot = require('screenshot-desktop');
const express = require("express");
const cors = require("cors");

let win;
let visionProcess = null;

const SIZES = {
  small: { width: 80, height: 80 },
  large: { width: 380, height: 520 }
};

function createWindow() {
  if (win) {
    win.focus();
    return;
  }

  win = new BrowserWindow({
    ...SIZES.small,
    alwaysOnTop: true,
    transparent: true,
    frame: false,
    resizable: false,
    hasShadow: true,
    roundedCorners: true,
    backgroundColor: '#00000000',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  win.loadFile('index.html');

  win.webContents.once('did-finish-load', () => {
    if (userId) {
      win.webContents.executeJavaScript(`
        window.userId = "${userId}";
        window.myveData = window.myveData || { netWorth: { totalNetWorthValue: { units: "N/A" } } };
        window.resetState = () => {
          // Add any UI reset logic here if needed
          console.log('UI reset state initialized');
        };
        window.resetState();
      `);
    }
  });

  win.on('focus', () => {
    if (userId) {
      win.webContents.executeJavaScript(`window.userId = "${userId}"`);
    }
  });

  win.on('closed', () => {
    win = null;
    userId = null; // Reset userId when app is closed
  });
}

app.whenReady().then(createWindow);

const localApp = express();
localApp.use(cors());
localApp.use(express.json());

localApp.post("/start-vision", (req, res) => {
  if (!userId && req.body.mobile) {
    userId = req.body.mobile;
    console.log("📨 Trigger received for Myve Vision from Web, user:", userId);
  } else {
    console.log("🔁 Vision already active for user:", userId);
  }
  createWindow();
  res.send({ status: "✅ Vision launched or focused" });
});

localApp.post("/stop-vision", (req, res) => {
  if (win) {
    win.close();
    win = null;
    userId = null;
    res.send({ status: "🛑 Vision window closed and user reset." });
  } else {
    res.send({ status: "⚠️ Vision was not running." });
  }
});

localApp.listen(1414, () => console.log("📡 Vision trigger server on :1414"));

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

ipcMain.on('expand-window', () => {
  if (win) {
    win.setResizable(true);
    win.setSize(SIZES.large.width, SIZES.large.height, true);
    win.setResizable(false);
  }
});

ipcMain.on('shrink-window', () => {
  if (win) {
    win.setResizable(true);
    win.setSize(SIZES.small.width, SIZES.small.height, true);
    win.setResizable(false);
  }
});

ipcMain.on('minimize-window', () => {
  if (win) win.minimize();
});

ipcMain.on('reset-ui', () => {
  if (win) {
    win.reload();
  }
});

ipcMain.on('close-vision', () => {
  if (win) {
    win.close();
    win = null;
  }
});

ipcMain.handle('capture-screen', async () => {
  try {
    const imgBuffer = await screenshot({ format: 'png' });
    console.log("📸 Captured image buffer size:", imgBuffer.length);
    if (!imgBuffer || imgBuffer.length < 1000) {
      throw new Error("❌ Screenshot buffer is too small or empty");
    }
    const base64Str = imgBuffer.toString('base64');
    console.log("📸 Base64 image preview:", base64Str.slice(0, 80));
    const fullBase64 = 'data:image/png;base64,' + base64Str;
    const userContext = await win.webContents.executeJavaScript(`
      window.myveData ?
        \`User financials: net worth ₹\${window.myveData.netWorth?.totalNetWorthValue?.units || "N/A"}\` :
        "User viewed this screen. Provide financial advice.";
    `);
    return { imageBase64: fullBase64, userContext: userContext, mobile_number: userId || "unknown" };
  } catch (error) {
    console.error("❌ Capture error:", error);
    return { error: 'Error during capture.' };
  }
});