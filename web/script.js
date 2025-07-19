document.addEventListener('DOMContentLoaded', () => {
    const allowed_keys = [];
    const navButtons = document.querySelectorAll('.nav-button');
    const views = document.querySelectorAll('.view');
    const listenButton = document.getElementById('listen-button');
    const saveButton = document.getElementById('save-button');
    const mappingList = document.getElementById('mapping-list');
    const newCommentInput = document.getElementById('new_comment');
    const newKeyInput = document.getElementById('new_key');
    const addMappingBtn = document.getElementById('add-mapping');
    let keyMapping = {};


    function renderMapping() {
        mappingList.innerHTML = '';
        for (const [comment, key] of Object.entries(keyMapping)) {
            const item = document.createElement('div');
            item.classList.add('mapping-item');
            item.innerHTML = `<div class="single-key"><div class="delete-key"></div><strong>${comment}</strong> → ${key}</div>`;
            mappingList.appendChild(item);
        }
    }

    async function initialize() {
        const settings = await eel.get_settings()();
        keyMapping = settings.key_mapping || {};
        renderMapping();
        document.getElementById('streamer_id').value = settings.streamer_id;
        document.getElementById('target_user').value = settings.target_user;
        updateListenButton();
    }

    addMappingBtn.addEventListener('click', () => {
        const comment = newCommentInput.value.trim().toLowerCase();
        const key = newKeyInput.value.trim();
        if (comment && key) {
            keyMapping[comment] = key;
            renderMapping();
            newCommentInput.value = '';
            newKeyInput.value = '';
        }
    });

    mappingList.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-key')) {
            const key = e.target.parentElement.innerText.trim();
            allowed_keys.splice(allowed_keys.indexOf(key), 1);
            e.target.parentElement.remove();
        }
    });

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
            key_mapping: keyMapping,
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