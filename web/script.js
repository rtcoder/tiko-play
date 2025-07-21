const q = selector => document.querySelector(selector);
const qAll = selector => document.querySelectorAll(selector);
    const eel = window.eel || {
        get_settings: () => () => {
        },
        save_settings: () => {
        },
        toggle_listening: () => {
        },
        get_listener_status: () => () => {
        },
    };
const TikoPlay = {
    mappings: {},
    elements: {
        navBtns: null,
        views: null,
        listenButton: null,
        saveButton: null,
        singleKeyArea: null,
        comboKeyArea: null,
        specialKeysTemplate: null,
        comboList: null,
        newComment: null,
        typedKey: null,
        streamerIdInput: null,
        targetUserInput: null,
    },
};

function setElements() {
    TikoPlay.elements = {
        navBtns: qAll('.nav-button'),
        views: qAll('.view'),
        listenButton: q('#listen-button'),
        saveButton: q('#save-button'),
        singleKeyArea: q('#single-key-area'),
        comboKeyArea: q('#combo-key-area'),
        specialKeysTemplate: q('#special-keys-template').innerHTML,
        comboList: q('#combo-list'),
        newComment: q('#new_comment'),
        typedKey: q('#typed_key'),
        streamerIdInput: q('#streamer_id'),
        targetUserInput: q('#target_user'),
    };
}

async function initialize() {
    const settings = await eel.get_settings()() || {
        streamer_id: '',
        target_user: '',
        mappings: {},
    };
    TikoPlay.elements.streamerIdInput.value = settings.streamer_id;
    TikoPlay.elements.targetUserInput.value = settings.target_user;
    TikoPlay.mappings = settings.mappings || {};
    updateMappingList();
    updateListenButton(settings.running);
    TikoPlay.elements.singleKeyArea.prepend(getSpecialKeysSelect('special_keys'));
    TikoPlay.elements.comboKeyArea.prepend(getSpecialKeysSelect('special_keys_combo'));
    setListeners();
}

function getSpecialKeysSelect(new_id) {
    const div = document.createElement('div');
    div.innerHTML = TikoPlay.elements.specialKeysTemplate;
    const select = div.querySelector('select');
    select.id = new_id;
    return select;
}

function updateMappingList() {
    const table = q('#mapping-table');
    table.innerHTML = '';
    for (let comment in TikoPlay.mappings) {
        const keyCombo = TikoPlay.mappings[comment].join('+');
        table.innerHTML += `<tr><td>${comment}</td><td>${keyCombo}</td></tr>`;
    }
}

function getKeyMappingMode() {
    return document.querySelector('input[name="key_mode"]:checked').value;
}

function addComboKey(value) {
    const span = document.createElement('span');
    span.textContent = value;
    TikoPlay.elements.comboList.appendChild(span);
}

function updateListenButton(isRunning) {
    if (isRunning) {
        TikoPlay.elements.listenButton.textContent = '⏹️ Zatrzymaj';
        TikoPlay.elements.listenButton.classList.add('running');
    } else {
        TikoPlay.elements.listenButton.textContent = '🎧 Nasłuchuj';
        TikoPlay.elements.listenButton.classList.remove('running');
    }
}

function getSpecialKeyValue() {
    const mode = getKeyMappingMode();
    const select = mode === 'combo'
        ? TikoPlay.elements.comboKeyArea.querySelector('#special_keys_combo')
        : TikoPlay.elements.singleKeyArea.querySelector('#special_keys');

    return select.value;
}

function resetKeysValues() {
    TikoPlay.elements.comboKeyArea.querySelector('#special_keys_combo').value = '';
    TikoPlay.elements.singleKeyArea.querySelector('#special_keys').value = '';
    TikoPlay.elements.typedKey.value = '';
    TikoPlay.elements.newComment.value = '';
    TikoPlay.elements.comboList.innerHTML = '';
}

function setListeners() {

    TikoPlay.elements.comboKeyArea.querySelector('#special_keys_combo').addEventListener('change', ({target}) => {
        const mode = getKeyMappingMode();
        if (mode === 'combo') {
            addComboKey(target.value);
            target.value = '';
        }
    });
    q('#add-mapping').addEventListener('click', () => {
        const comment = TikoPlay.elements.newComment.value.trim();
        const mode = getKeyMappingMode();

        if (!comment) {
            return alert('Podaj treść komentarza');
        }

        let keys = [];

        if (mode === 'single') {
            const special = getSpecialKeyValue();
            const typed = TikoPlay.elements.typedKey.value.trim();
            if (special) {
                keys = [special];
            } else if (typed) {
                keys = [typed.toLowerCase()];
            } else {
                return alert('Wybierz lub wpisz klawisz');
            }
        } else {
            const combo = Array.from(TikoPlay.elements.comboList.querySelectorAll('span')).map(el => el.textContent);
            if (combo.length === 0) {
                return alert('Dodaj chociaż jeden klawisz do kombinacji');
            }
            keys = combo;
        }
        resetKeysValues();
        TikoPlay.mappings[comment] = keys;
        updateMappingList();
    });

    q('#add-combo-key').addEventListener('click', () => {
        const key = q('#combo-input').value.trim().toLowerCase();
        if (!key) {
            return;
        }
        addComboKey(key);
        q('#combo-input').value = '';
    });

    qAll('input[name="key_mode"]').forEach(el =>
        el.addEventListener('change', () => {
            const isCombo = getKeyMappingMode() === 'combo';
            TikoPlay.elements.comboKeyArea.style.display = isCombo ? 'block' : 'none';
            TikoPlay.elements.singleKeyArea.style.display = isCombo ? 'none' : 'block';
        }));

    TikoPlay.elements.navBtns.forEach(b => b.addEventListener('click', () => {
        const targetView = b.dataset.view;
        TikoPlay.elements.views.forEach(view => view.classList.remove('active'));
        q(`#${targetView}-view`).classList.add('active');
        TikoPlay.elements.navBtns.forEach(btn => btn.classList.remove('active'));
        b.classList.add('active');
    }));

    TikoPlay.elements.saveButton.addEventListener('click', async () => {
        const settings = {
            streamer_id: TikoPlay.elements.streamerIdInput.value,
            target_user: TikoPlay.elements.targetUserInput.value,
            mappings: TikoPlay.mappings,
        };
        const success = await eel.save_settings(settings)();
        if (success) {
            alert('Ustawienia zapisane!');
        }
    });

    TikoPlay.elements.listenButton.addEventListener('click', async () => {
        const result = await eel.toggle_listening()();
        if (result.error) {
            alert(`Błąd: ${result.error}`);
        }
        updateListenButton(result.running);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setElements();


    setInterval(async () => {
        const status = await eel.get_listener_status()();
        updateListenButton(status.running);
    }, 3000);

    initialize();
});