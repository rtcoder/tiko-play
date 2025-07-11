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

function addMappingRow(command = '', key = '') {
    const row = document.createElement('div');
    row.innerHTML = `
    <input type="text" placeholder="komentarz" value="${command}">
    <input type="text" placeholder="klawisz" value="${key}">
  `;
    document.getElementById('mappings').appendChild(row);
}

function loadExistingMappings() {
    const config = loadConfig();
    const mappings = config.commandMappings || [];

    if (mappings.length > 0) {
        mappings.forEach(mapping => {
            addMappingRow(mapping.comment, mapping.key);
        });
    } else {
        // Dodaj przynajmniej jeden pusty wiersz na start
        addMappingRow();
    }
}

document.getElementById('addBtn').addEventListener('click', () => {
    addMappingRow();
});

document.getElementById('saveBtn').addEventListener('click', () => {
    const mappings = [];
    document.querySelectorAll('#mappings div').forEach(div => {
        const inputs = div.querySelectorAll('input');
        if (inputs[0].value && inputs[1].value) {
            mappings.push({
                comment: inputs[0].value.trim(),
                key: inputs[1].value.trim()
            });
        }
    });

    const config = loadConfig();
    config.commandMappings = mappings;
    saveConfig(config);

    alert('Zapisano mapowania!');
});

document.getElementById('settingsBtn').addEventListener('click', () => {
    location.href = 'index.html';
});

// 🔄 automatycznie wczytaj po załadowaniu strony
window.addEventListener('DOMContentLoaded', loadExistingMappings);
