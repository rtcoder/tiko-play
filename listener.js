const { TikTokLiveConnection } = require('tiktok-live-connector');
const fs = require('fs');
const path = require('path');

// Wczytujemy konfigurację
const configPath = path.join(__dirname, 'config.json');

if (!fs.existsSync(configPath)) {
    console.error('[TikoPlay] Brak pliku konfiguracyjnego!');
    process.exit(1);
}

const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
const streamerId = config.streamerId;
const acceptedChars = config.acceptedChars || [];
const acceptedUser = config.acceptedUser || null;

if (!streamerId || acceptedChars.length === 0) {
    console.error('[TikoPlay] Nieprawidłowa konfiguracja. Sprawdź streamerId i acceptedChars.');
    process.exit(1);
}

console.log(`[TikoPlay] Rozpoczynam nasłuch streamera: ${streamerId}`);
if (acceptedUser) {
    console.log(`[TikoPlay] Filtrowanie komentarzy od użytkownika: ${acceptedUser}`);
}
console.log(`[TikoPlay] Akceptowane komendy: ${acceptedChars.join(', ')}`);

// Tworzymy połączenie
let tiktok = new TikTokLiveConnection(streamerId, {
    enableExtendedGiftInfo: false
});

// Obsługa komentarzy
tiktok.on('chat', (data) => {
    const username = data.uniqueId;
    const comment = (data.comment || '').trim();

    // Filtruj po użytkowniku, jeśli ustawiony
    if (acceptedUser && username !== acceptedUser) {
        return;
    }

    // Akceptujemy tylko pojedyncze znaki, które są na liście
    if (comment.length === 1 && acceptedChars.includes(comment)) {
        console.log(`[HIT] ${username}: "${comment}" -> akcja!`);
        // TODO: tutaj zasymuluj naciśnięcie klawisza
    } else {
        console.log(`[POMINIĘTO] ${username}: "${comment}"`);
    }
});

// Obsługa błędów i połączenia
tiktok.on('connected', () => {
    console.log('[TikoPlay] Połączono ze streamem!');
});

tiktok.on('disconnected', () => {
    console.log('[TikoPlay] Rozłączono.');
});

tiktok.on('streamEnd', () => {
    console.log('[TikoPlay] Stream zakończony.');
});

tiktok.on('error', (err) => {
    console.error('[TikoPlay] Błąd:', err.message);
});

// Start połączenia
tiktok.connect().catch((err) => {
    console.error('[TikoPlay] Nie udało się połączyć:', err.message);
});
