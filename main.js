const {app, BrowserWindow, ipcMain} = require('electron');
const path = require('path');
const fs = require('fs');
const {spawn} = require('child_process');
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

let listenerProcess = null;

ipcMain.handle('start-listener', () => {
    if (listenerProcess) {
        return {status: 'already-running'};
    }

    listenerProcess = spawn('node', ['listener.js'], {
        cwd: __dirname,
        stdio: 'inherit', // lub 'pipe' jeśli chcesz odczytywać logi
        shell: true,
    });

    listenerProcess.on('exit', (code) => {
        console.log(`[TikoPlay] Nasłuch zakończony (kod ${code})`);
        listenerProcess = null;
    });

    return {status: 'started'};
});

ipcMain.handle('stop-listener', () => {
    if (listenerProcess) {
        listenerProcess.kill();
        listenerProcess = null;
        return {status: 'stopped'};
    } else {
        return {status: 'not-running'};
    }
});

app.whenReady().then(createWindow);
