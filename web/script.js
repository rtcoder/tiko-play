document.addEventListener('DOMContentLoaded', () => {
    const allowed_keys=[];
    const navButtons = document.querySelectorAll('.nav-button');
    const views = document.querySelectorAll('.view');
    const listenButton = document.getElementById('listen-button');
    const saveButton = document.getElementById('save-button');

    async function initialize() {
        const settings = await eel.get_settings()();
        document.getElementById('streamer_id').value = settings.streamer_id;
        allowed_keys.push(...settings.allowed_keys);
        document.getElementById('target_user').value = settings.target_user;
        document.querySelector('.keys').innerHTML = settings.allowed_keys
            .map(key => `<div class="single-key"><div class="delete-key"></div> ${key.trim()}</div>`).join('');
        updateListenButton();
    }

    document.querySelector('.keys').addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-key')) {
            const key = e.target.parentElement.innerText.trim();
            allowed_keys.splice(allowed_keys.indexOf(key), 1);
            e.target.parentElement.remove();
        }
    });
    document.querySelector('#allowed_keys').addEventListener('input', (e) => {
        if(e.data !== ',') {
            return;
        }
        allowed_keys.push(...e.target.value.split(',').map(key => key.trim()).filter(key => key.length > 0));
        document.querySelector('.keys').innerHTML = allowed_keys
            .map(key => `<div class="single-key"><div class="delete-key"></div> ${key.trim()}</div>`).join('');
        e.target.value = '';
    })

    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetView = button.dataset.view;
            views.forEach(view => view.classList.remove('active'));
            document.getElementById(`${targetView}-view`).classList.add('active');
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });
    saveButton.addEventListener('click', async () => {
        const settings = {
            streamer_id: document.getElementById('streamer_id').value,
            allowed_keys,
            target_user: document.getElementById('target_user').value,
        };
        const success = await eel.save_settings(settings)();
        if (success) {
            alert('Ustawienia zapisane!');
        }
    });
    listenButton.addEventListener('click', async () => {
        const result = await eel.toggle_listening()();
        if (result.error) {
            alert(`Błąd: ${result.error}`);
        }
        updateListenButton(result.running);
    });

    function updateListenButton(isRunning) {
        if (isRunning) {
            listenButton.textContent = '⏹️ Zatrzymaj';
            listenButton.classList.add('running');
        } else {
            listenButton.textContent = '🎧 Nasłuchuj';
            listenButton.classList.remove('running');
        }
    }

    setInterval(async () => {
        const status = await eel.get_listener_status()();
        updateListenButton(status.running);
    }, 3000);
    initialize();
});