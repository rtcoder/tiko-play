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

// Przełączanie widoków
const views = {
    'nav-streamer': 'view-streamer',
    'nav-keys': 'view-keys',
    'nav-userfilter': 'view-userfilter'
};

Object.keys(views).forEach(navId => {
    document.getElementById(navId).addEventListener('click', () => {
        // ukryj wszystkie widoki
        Object.values(views).forEach(id => {
            document.getElementById(id).classList.remove('active');
        });
        // pokaż wybrany
        document.getElementById(views[navId]).classList.add('active');
    });
});

// Załaduj config i wypełnij inputy oraz sidebar info
function loadAll() {
    const config = loadConfig();

    document.getElementById('streamerId').value = config.streamerId || '';
    document.getElementById('acceptedChars').value = (config.acceptedChars || []).join(',');
    document.getElementById('acceptedUser').value = config.acceptedUser || '';

    document.getElementById('sidebar-streamer-id').textContent = config.streamerId || '-';
    document.getElementById('sidebar-accepted-chars').textContent = (config.acceptedChars || []).join(',') || '-';
    document.getElementById('sidebar-accepted-user').textContent = config.acceptedUser || '-';
}

loadAll();

// Zapis konfiguracji
document.getElementById('saveStreamerBtn').addEventListener('click', () => {
    const streamerId = document.getElementById('streamerId').value.trim();
    if (!streamerId) {
        alert('Podaj ID streamera!');
        return;
    }
    const config = loadConfig();
    config.streamerId = streamerId;
    saveConfig(config);
    alert('Zapisano ID streamera!');
    loadAll();
});

document.getElementById('saveKeysBtn').addEventListener('click', () => {
    const rawInput = document.getElementById('acceptedChars').value.trim();
    const charsArray = rawInput
        .split(',')
        .map(c => c.trim())
        .filter(c => c.length === 1);

    if (charsArray.length === 0) {
        alert('Podaj co najmniej jeden znak (pojedynczy znak, oddzielone przecinkami)');
        return;
    }

    const invalid = rawInput
        .split(',')
        .map(c => c.trim())
        .filter(c => c.length !== 1);

    if (invalid.length > 0) {
        alert(`Błąd: tylko pojedyncze znaki są dozwolone.\nNiepoprawne wartości: ${invalid.join(', ')}`);
        return;
    }

    const config = loadConfig();
    config.acceptedChars = charsArray;
    saveConfig(config);
    alert('Zapisano akceptowane znaki!');
    loadAll();
});

document.getElementById('saveUserBtn').addEventListener('click', () => {
    const acceptedUser = document.getElementById('acceptedUser').value.trim();
    const config = loadConfig();
    config.acceptedUser = acceptedUser;
    saveConfig(config);
    alert('Zapisano filtr użytkownika!');
    loadAll();
});

// Placeholder do startu nasłuchu
document.getElementById('startListeningBtn').addEventListener('click', () => {
    alert('Tu w przyszłości uruchomimy nasłuch TikTok Live!');
});
