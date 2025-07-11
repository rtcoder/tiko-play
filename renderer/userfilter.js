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

function loadAcceptedUser() {
    const config = loadConfig();
    document.getElementById('acceptedUser').value = config.acceptedUser || '';
}

document.getElementById('saveBtn').addEventListener('click', () => {
    const acceptedUser = document.getElementById('acceptedUser').value.trim();

    const config = loadConfig();
    config.acceptedUser = acceptedUser;
    saveConfig(config);

    alert('Zapisano filtr użytkownika!');
});

document.getElementById('backBtn').addEventListener('click', () => {
    location.href = 'mapping.html';
});
document.getElementById('startListeningBtn').addEventListener('click', () => {
    alert('Tu w przyszłości uruchomimy nasłuch TikTok Live i reakcję na komentarze!');
    // TODO: Tutaj później podłączymy funkcję nasłuchu i symulacji klawiszy
});
window.addEventListener('DOMContentLoaded', loadAcceptedUser);
