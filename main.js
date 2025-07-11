const {app, BrowserWindow} = require('electron');
const path = require('path');
const fs = require('fs');

const configPath = path.join(__dirname, 'config.json');

function createWindow() {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true,  // tylko na starcie, potem warto izolować
            contextIsolation: false,
        },
    });

    let config = {};
    if (fs.existsSync(configPath)) {
        config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    }

    win.loadFile('renderer/index.html');
}

app.whenReady().then(createWindow);
