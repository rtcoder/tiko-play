const fs = require('fs');
const path = require('path');

const configPath = path.join(__dirname, '..', 'config.json');

function loadConfig() {
    if (fs.existsSync(configPath)) {
        return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    }
    return {};
}

function saveConfig(data) {
    fs.writeFileSync(configPath, JSON.stringify(data, null, 2));
}

function loadAcceptedChars() {
    const config = loadConfig();
    const acceptedArray = config.acceptedChars || [];
    document.getElementById('acceptedChars').value = acceptedArray.join(',');
}

document.getElementById('saveBtn').addEventListener('click', () => {
    const rawInput = document.getElementById('acceptedChars').value.trim();
    const charsArray = rawInput
        .split(',')
        .map(c => c.trim())
        .filter(c => c.length > 0);

    const invalid = charsArray.filter(c => c.length !== 1);
    if (invalid.length > 0) {
        alert(`Błąd: tylko pojedyncze znaki są dozwolone.\nNiepoprawne wartości: ${invalid.join(', ')}`);
        return;
    }

    const config = loadConfig();
    config.acceptedChars = charsArray;
    saveConfig(config);

    alert('Zapisano akceptowane znaki!');
});

document.getElementById('settingsBtn').addEventListener('click', () => {
    location.href = 'index.html';
});

window.addEventListener('DOMContentLoaded', loadAcceptedChars);
