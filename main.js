const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true, // dla prostoty na start
            contextIsolation: false
        }
    });

    win.loadFile('renderer/index.html');
}

app.whenReady().then(createWindow);
