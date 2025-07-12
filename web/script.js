document.addEventListener('DOMContentLoaded', () => {
    // === Elementy DOM ===
    const navButtons = document.querySelectorAll('.nav-button');
    const views = document.querySelectorAll('.view');
    const listenButton = document.getElementById('listen-button');
    const saveButton = document.getElementById('save-button');

    // === Inicjalizacja ===
    // Po załadowaniu strony pobierz aktualne ustawienia i status z Pythona
    async function initialize() {
        const settings = await eel.get_settings()();
        document.getElementById('streamer_id').value = settings.streamer_id;
        document.getElementById('allowed_keys').value = settings.allowed_keys;
        document.getElementById('target_user').value = settings.target_user;
        document.querySelector('.keys').innerHTML = settings.allowed_keys.split(',').map(key => `<div class="single-key">${key.trim()}</div>`).join('');

        updateListenButton();
    }

    // === Logika przełączania widoków ===
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetView = button.dataset.view;

            views.forEach(view => view.classList.remove('active'));
            document.getElementById(`${targetView}-view`).classList.add('active');

            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });

    // === Zapisywanie ustawień ===
    saveButton.addEventListener('click', async () => {
        const settings = {
            streamer_id: document.getElementById('streamer_id').value,
            allowed_keys: document.getElementById('allowed_keys').value,
            target_user: document.getElementById('target_user').value
        };
        const success = await eel.save_settings(settings)();
        if (success) {
            alert('Ustawienia zapisane!');
        }
    });

    // === Uruchamianie/Zatrzymywanie nasłuchiwania ===
    listenButton.addEventListener('click', async () => {
        const result = await eel.toggle_listening()();
        if (result.error) {
            alert(`Błąd: ${result.error}`);
        }
        updateListenButton(result.running);
    });

    // === Funkcje pomocnicze ===
    function updateListenButton(isRunning) {
        if (isRunning) {
            listenButton.textContent = '⏹️ Zatrzymaj';
            listenButton.classList.add('running');
        } else {
            listenButton.textContent = '🎧 Nasłuchuj';
            listenButton.classList.remove('running');
        }
    }

    // Sprawdzaj status co 3 sekundy, aby zsynchronizować przycisk
    setInterval(async () => {
        const status = await eel.get_listener_status()();
        updateListenButton(status.running);
    }, 3000);

    // Uruchom aplikację
    initialize();
});