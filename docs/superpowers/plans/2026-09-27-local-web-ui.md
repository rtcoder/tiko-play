# TikoPlay Local Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zachować funkcje TikoPlay, zastępując główne GUI panelem webowym automatycznie otwieranym po kliknięciu ikony programu na pulpicie.

**Architecture:** Jeden proces: Qt w głównym wątku obsługuje tray i launcher, osobny wątek asyncio obsługuje FastAPI i listener, jeden wykonawca realizuje klawisze. Panel React jest dołączony do paczki, a backend pozostaje niezależny od przeglądarki. Najpierw weryfikujemy działający przekrój uruchomienia z ikony, następnie pełne UI.

**Tech Stack:** Python, TikTokLive, PyAutoGUI, PySide6, FastAPI, Uvicorn, Pydantic; React, TypeScript, Vite; pytest, pytest-asyncio, httpx, pytest-qt, Vitest, Testing Library; PyInstaller, Inno Setup.

**Spec:** [Zatwierdzony kierunek i szczegółowy projekt](../specs/2026-09-26-local-web-ui-design.md). Użytkownik zaakceptował przejście do następnego etapu słowem „odpalaj” 2026-09-27. Plan został następnie zaakceptowany przez użytkownika poleceniem „plan jest ok, przejdz do dzialania”.

## Global Constraints

- Kliknięcie ikony ma uruchamiać aplikację, a nie samą stronę wymagającą wcześniej włączonego backendu.
- Panel dostępny tylko na tym komputerze; brak dostępu z telefonu i sieci LAN.
- Bind tylko do 127.0.0.1, nigdy do 0.0.0.0.
- Uvicorn działa bez reload i bez wielu workerów.
- Cooldown wynosi 0,3 s na trigger; kolejka klawiszy ma limit 100, akcje starsze niż 1 s są odrzucane.
- Odliczanie wynosi 3 s i można je wyłączyć; komentarze w trakcie odliczania nie są kolejkowane.
- Gotowość startu: limit 15 s; uporządkowane zamykanie: limit 5 s.
- Token otwarcia jest jednorazowy, ważny 60 s; cookie HttpOnly, SameSite=Strict, osobne dla instancji.
- Bufor: 1000 zdarzeń, kolejka klienta: 200, tekst komentarza w logu: maksymalnie 2000 znaków.
- Autosave: 500 ms; najwyżej jeden zapis w locie; kontrola expected_revision.
- Diagnostyka: do 3 plików po 1 MB, bez tokenów i domyślnie bez pełnych komentarzy.
- UI po polsku, ciemny motyw, minimum 900 × 550, dostępne Start/Stop przy przewijaniu.
- Zachować istniejącą konfigurację użytkownika i jej katalog; nie używać repozytoryjnego config.json jako danych użytkownika.
- Nie nadpisywać zastanych zmian w src/listener.py, src/ui_logger.py i src/views/main_window.py ani nie dodawać ich przypadkowo do commitów.
- Testy używają katalogów tymczasowych i atrap klienta/klawiatury. Rzeczywiste TikTok i klawisze tylko w świadomym teście integracyjnym.
- Windows i macOS wymagają osobnego builda i odbioru. Brak platformy oznacza test niewykonany.
- Wersje bibliotek i Pythona przypiąć po sprawdzeniu zgodności w zadaniu 1; nie utożsamiać lokalnego Pythona 3.14.2 z wymaganiem produktu.

## Review Focus

1. Ścieżki instalacji zawierają spacje/Unicode, a working directory jest inny niż katalog programu: ikona nadal działa. Test zadania 10.
2. Backend ginie i uruchamia się na innym porcie: stara karta nie może wyglądać na połączoną ani automatycznie wysyłać Start. Test zadania 9.
3. Starsza konfiguracja ma nieznane pola albo przyszłą wersję schematu: brak cichego zniszczenia danych. Test zadania 2.
4. Stop i przychodzący komentarz zachodzą jednocześnie: żadna oczekująca akcja starej sesji nie wykonuje się po restarcie. Testy zadań 4–5.
5. Trzecia edycja powstaje przed odpowiedzią na pierwszy autosave: ostatnia wersja nie ginie ani nie przepisuje się starszą odpowiedzią. Test zadania 12.

## Organizacja pracy i zależności

To jeden powiązany przepływ aplikacji, nie niezależne produkty. Zadania realizować kolejno; małe commity obejmują tylko pliki danego zadania. Przed wykonaniem zastosować using-git-worktrees. Repo ma niezatwierdzone zmiany: worktree nie kopiuje ich automatycznie, więc zachować ich patch i przenieść do izolowanej gałęzi tylko po sprawdzeniu bazowego stanu, bez kasowania oryginałów. Nie używać stash/reset/clean na zmianach użytkownika. Przenieść również nieśledzone AGENTS.md i PROJECT_CONTEXT.md jako kontekst, bez prywatnej konfiguracji.

Komendy poniżej używają aktywnego środowiska developerskiego: python z nowego venv, npm w frontend/. Na Windows użyć odpowiedniego interpretera .venv/Scripts/python.exe; na macOS .venv/bin/python. Instalacje i wybór wersji należą do wykonania, nie zostały uruchomione podczas pisania planu.

Mapowanie spec → zadania: zgodność funkcji 1–5 i 11–12; lifecycle 4–5, 8, 10; API/sesje 6–7; UI 9, 11–12; pakowanie i ikona 8, 10, 13; migracja 2; odbiór 14.

## Mapa plików i kontraktów

| Pliki | Odpowiedzialność |
| --- | --- |
| src/core/models.py, matching.py, presets.py, keys.py | Konfiguracja v2, stan, reguły, katalog klawiszy |
| src/core/config_store.py | Migracja, backup, atomowy zapis i rewizje |
| src/core/events.py, diagnostics.py | Ograniczone bufory i rotowana diagnostyka |
| src/core/keyboard.py, src/adapters/pyautogui_keyboard.py | Kolejka oraz rzeczywiste wywołania klawiatury |
| src/core/listener_service.py, src/adapters/tiktok.py | Lifecycle i adapter biblioteki TikTokLive |
| src/api/session.py, app.py, routes.py, events.py | Sesje, HTTP, WebSocket i zasoby frontendu |
| src/desktop/instance.py, backend.py, launcher.py, tray.py, resources.py | Single-instance, asyncio, start, tray i ścieżki paczki |
| frontend/src/api/, state/, components/, App.tsx, styles.css | Komunikacja, stan edycji i interfejs |
| packaging/windows.spec, macos.spec, windows.iss | Paczki natywne i skrót na pulpicie |
| tests/core/, api/, desktop/, packaging/ | Izolowane testy backendu i pakowania |
| frontend/src/**/*.test.tsx, **/*.test.ts | Testy frontendu i synchronizacji |

Puste pakiety __init__.py tworzyć wraz z pierwszym modułem. Nie wprowadzać abstrakcji bez wskazanego poniżej konsumenta.

### Task 1: Modele, reguły i środowisko testowe

**Files:** Create src/core/{models,matching,presets,keys}.py, tests/conftest.py, tests/core/test_matching.py, tests/core/test_models.py, pyproject.toml, requirements-dev.txt; Modify requirements.txt, .gitignore. Źródło presetów: src/views/key_editor/presets.py; starego modułu na tym etapie nie usuwać.

**Interfaces:** Mapping(id: str, trigger: str, keys: tuple[str, ...]); AppConfig(version=2, streamer_id, target_user, mappings, show_logs, countdown_enabled); ConfigSnapshot(config: AppConfig, revision: int); AppError(code, message, field_errors); ListenerState(status, output, active_config_revision, error, generation). Modele konfiguracji zachowują dodatkowe pola. `normalize_trigger(text: str) -> str`; `Matcher(config: AppConfig, clock: Callable[[], float]).match(user_id: str, comment: str) -> tuple[str, ...] | None`. `get_presets() -> dict[str, list[dict]]`; `get_keys() -> list[str]`.

- [ ] **1. Test:** dodać testy normalizacji, dokładnego filtra, kombinacji i presetów. Asercje: `normalize_trigger(' LEWO ') == 'lewo'`; dopasowanie przy t=0 daje `('ctrl', 'a')`, przy t=0.299 daje None, przy t=0.3 ponownie kombinację; `user != target_user` daje None; dodatkowe słowo daje None. Duplikaty triggerów po normalizacji i powtórzone id powodują błąd walidacji, nie utratę wpisu.
- [ ] **2. RED:** utworzyć odizolowane venv, sprawdzić zgodne wersje i przypiąć zależności (w tym narzędzia build/test); `python -m pytest tests/core/test_matching.py tests/core/test_models.py -q` ma wykazać brak wdrożonych modułów/asercji. Brak biblioteki testowej naprawić przed uznaniem RED za właściwy.
- [ ] **3. Implementacja:** wdrożyć powyższe kontrakty, monotoniczny zegar, niezmienne snapshoty i katalog akceptujący wszystkie stare klawisze oraz poprawne nazwy backendu bez importowania PyAutoGUI w testach. Zależność rdzenia od Pydantic jest dopuszczona; import Qt/FastAPI/PyAutoGUI nie.
- [ ] **4. GREEN:** uruchomić wskazane testy, potwierdzić niezależność od Qt/display i prywatnej konfiguracji; testy używają wstrzykniętej ścieżki i atrap. Zapisać wersję Pythona i dokładne wersje zależności w metadanych projektu.
- [ ] **5. Commit:** `feat: extract typed configuration and comment matching core`; stage tylko pliki zadania.

### Task 2: ConfigStore i migracja bez utraty danych

**Files:** Create src/core/config_store.py, tests/core/test_config_store.py; Modify src/config.py (rozdzielenie ustalania ścieżki od efektów importu, zachowanie kompatybilnych funkcji dla starego GUI).

**Interfaces:** `ConfigStore(path: Path)`; `async load() -> ConfigSnapshot`; `snapshot() -> ConfigSnapshot`; `async save(config: AppConfig, expected_revision: int) -> ConfigSnapshot`. Brak pliku: domyślna v2, revision=1 po skutecznym zapisie. Rewizja jest monotoniczna w obrębie instance_id; po restarcie klienci muszą pobrać nowy snapshot. Uszkodzona konfiguracja: stan recovery z AppError i zachowanym oryginałem, brak aktywnego snapshotu. `async repair(config: AppConfig) -> ConfigSnapshot` tworzy niekolizyjną kopię oryginału przed zapisem.

- [ ] **1. Test:** `test_migrate_v1_preserves_keys_and_extras`: wersja 2, stabilne id po ponownym load, `keys == ('ctrl','a')`, nieznane pole zachowane, backup bajtowo równy oryginałowi. `test_failed_replace_keeps_state`: błąd os.replace pozostawia bajty, rewizję i snapshot bez zmiany. `test_stale_revision`: drugi zapis z tą samą rewizją kończy się konfliktem. `test_future_version_readonly`: version=99 nie jest przepisywana i Start niedostępny. `test_corrupt_json_requires_repair`: brak automatycznego nadpisania i backup przed jawną naprawą.
- [ ] **2. RED:** `python -m pytest tests/core/test_config_store.py -q`; oczekiwane niepowodzenie dla nowych kontraktów.
- [ ] **3. Implementacja:** serializować zapisy, plik tymczasowy w tym samym katalogu, flush/fsync, os.replace. Backup v1 tworzyć wyłącznie jeśli nie istnieje; recovery używa kolejnego wolnego backupu. Nowa instalacja ma countdown_enabled=True; migracja v1 również True, zachowując inne wartości. Nie dodawać skutków ubocznych odczytu danych użytkownika do importu.
- [ ] **4. GREEN:** komenda z kroku 2 oraz testy zadania 1; sprawdzić też niepoprawny typ JSON, pusty trigger/klawisz, id i przyszłą wersję. Walidacja nie może usuwać mapowań.
- [ ] **5. Commit:** `feat: add atomic versioned configuration store`.

### Task 3: Zdarzenia i diagnostyka

**Files:** Create src/core/events.py, src/core/diagnostics.py, tests/core/test_events.py, tests/core/test_diagnostics.py.

**Interfaces:** Event(id: int, instance_id: str, timestamp: str, type: str, payload: dict); `EventBus(instance_id).publish(type, payload) -> Event`; `recent() -> list[Event]`; `subscribe() -> Subscription`; Subscription(queue, closed), `unsubscribe(subscription)`. `configure_diagnostics(directory: Path) -> logging.Logger`.

- [ ] **1. Test:** publikacja 1001 zdarzeń pozostawia id 2…1001; klient zalegający ponad 200 zostaje oznaczony jako zamknięty, szybki nadal odbiera. Komentarz 2001 znaków w evencie ma 2000. Logger po wymuszeniu rotacji tworzy najwyżej 3 pliki po 1_000_000 bajtów; sekrety i komentarze nie są zapisywane.
- [ ] **2. RED:** `python -m pytest tests/core/test_events.py tests/core/test_diagnostics.py -q`.
- [ ] **3. Implementacja:** deque(maxlen=1000), numeracja w jednej pętli, nieblokujące kolejki subskrypcji, jawny powód rozłączenia; RotatingFileHandler(maxBytes=1_000_000, backupCount=2), ograniczenie wielkości pojedynczego rekordu. Publikacja błędu nie wymaga istnienia widoku logów.
- [ ] **4. GREEN:** komenda z kroku 2; potwierdzić zachowanie dla braku subskrybentów i czyszczenie subskrypcji po rozłączeniu.
- [ ] **5. Commit:** `feat: add bounded event stream and diagnostics`.

### Task 4: Wykonawca klawiatury

**Files:** Create src/core/keyboard.py, src/adapters/pyautogui_keyboard.py, tests/core/test_keyboard.py.

**Interfaces:** KeyboardPort `execute(keys: tuple[str, ...]) -> None`; KeyAction(keys, generation: int, created_at: float); `KeyboardExecutor(port, clock, report)` z `enable(generation)`, `submit(action) -> bool`, `disable()`, `async close(timeout: float)`. Report przekazuje wynik na pętlę backendu, nie wywołuje Qt z wątku.

- [ ] **1. Test:** zablokować atrapę pierwszego execute, napełnić 100 oczekujących wpisów, następny submit zwraca False; po przesunięciu zegara o >1 s brak execute starych wpisów. disable czyści kolejkę, po enable nowej generacji poprzednie akcje nie wykonują się. Test bariery start/stop dopuszcza wyłącznie już rozpoczęte execute; reszta jest odrzucana. Jeden klawisz przekazany do press, kombinacja do hotkey w oryginalnej kolejności.
- [ ] **2. RED:** `python -m pytest tests/core/test_keyboard.py -q`; wszystkie rzeczywiste funkcje PyAutoGUI zastąpić atrapami przed użyciem adaptera.
- [ ] **3. Implementacja:** pojedynczy worker, wspólna blokada decyzji rozpoczęcia akcji i disable, bounded queue=100, monotoniczne znaczniki. FailSafeException oraz inne błędy wyłączają wyjście, czyszczą kolejkę i raportują błąd. Odrzucenia agregować najwyżej raz na sekundę.
- [ ] **4. GREEN:** komenda z kroku 2; testy potwierdzają brak równoległych execute i brak blokowania pętli asyncio.
- [ ] **5. Commit:** `feat: serialize keyboard actions with bounded queue`.

### Task 5: Nadzorowany listener

**Files:** Create src/core/listener_service.py, src/adapters/tiktok.py, tests/core/test_listener_service.py, tests/core/test_tiktok_adapter.py. Obecny src/listener.py pozostaje nienaruszony do końcowego przełączenia.

**Interfaces:** TikTokPort `async connect(on_comment: Callable[[str, str], Awaitable[None]]) -> asyncio.Task`, `async disconnect() -> None`; factory `(streamer_id: str) -> TikTokPort`. `ListenerService(factory, keyboard, events, clock)`; `start(snapshot: ConfigSnapshot) -> ListenerState` przyjmuje i planuje pracę; `request_stop() -> ListenerState` synchronicznie wyłącza wyjście; `async stop() -> ListenerState` kończy sprzątanie; `state() -> ListenerState`.

- [ ] **1. Test:** dwa starty tworzą jeden klient; Stop przy zablokowanym connect kończy stopped bez klawiszy; komentarz podczas countdown nie jest wykonywany później; po 3 s aktywne wyjście; zadanie klienta kończące się wyjątkiem daje error i disabled. Zapis innej rewizji nie zmienia aktywnego snapshotu. Parametryzować offline, user-not-found, already-connected, fail-safe, utratę sieci i zwykłe zakończenie zadania.
- [ ] **2. RED:** `python -m pytest tests/core/test_listener_service.py tests/core/test_tiktok_adapter.py -q`.
- [ ] **3. Implementacja:** jeden nadzorowany task, jawne przejścia stanów i finally. Match i cooldown w backendzie, submit tylko gdy enabled. request_stop blokuje nowe akcje przed await. Nowy Start podczas stopping zwraca konflikt; powtórzony Stop jest idempotentny. Adapter uwzględnia rzeczywisty kontrakt przypiętego TikTokLive, nie zakłada blokującego start; brak automatycznego reconnectu.
- [ ] **4. GREEN:** komenda z kroku 2 oraz zadanie 4; testować ponowny Start po błędzie, błędy disconnect i anulowanie podczas countdown. Brak kontaktu z TikTokiem.
- [ ] **5. Commit:** `feat: supervise listener lifecycle independently of UI`.

### Task 6: Sesje lokalne i dostęp do API

**Files:** Create src/api/session.py, tests/api/test_session.py.

**Interfaces:** `SessionManager(instance_id, origin, clock)`; `issue_launch_token() -> str`; `exchange(token: str) -> Session`; `authenticate(cookie: str) -> Session`; Session(id, csrf_token); `validate_host(host)`, `validate_origin(origin)`, `validate_csrf(session, token)` zgłaszają AppError. Kontenery sekretów wyłącznie w pamięci.

- [ ] **1. Test:** wymiana przy t=59.9 udana, przy t=60 odrzucona; ponowne użycie odrzucone; nowy link nie unieważnia istniejącej sesji; obcy/brakujący Origin dla mutacji i WS odrzucony; obcy Host lub token CSRF odrzucony. Sekrety nie występują w caplog.
- [ ] **2. RED:** `python -m pytest tests/api/test_session.py -q`.
- [ ] **3. Implementacja:** secrets.token_urlsafe, dokładne porównanie origin z dynamicznym portem, losowa nazwa cookie instancji, sesje ważne do końca procesu. Ograniczyć oczekujące tokeny do 32 (wygasłe usuwać); sesje do 128, przekroczenie zgłaszać zamiast niejawnie wylogowywać aktywne karty. HTTPS nie jest wymagane dla loopback HTTP; nie ustawiać niedziałającego Secure cookie na tym URL.
- [ ] **4. GREEN:** komenda z kroku 2, również limity i nowa instancja odrzucająca stare cookie.
- [ ] **5. Commit:** `feat: secure local browser sessions`.

### Task 7: HTTP, WebSocket i zasoby

**Files:** Create src/api/app.py, routes.py, events.py, tests/api/test_routes.py, test_websocket.py, test_static.py.

**Interfaces:** `create_app(store, listener, events, sessions, static_dir: Path) -> FastAPI`; endpointy ze specyfikacji. Rozszerzenia potrzebne dla pełnego przepływu: GET /api/session zwraca csrf_token uwierzytelnionej sesji po odświeżeniu; POST /api/config/repair wyłącznie w recovery wykonuje ConfigStore.repair. Odpowiedzi konfiguracji `{config, config_revision}`; zapis `{config, expected_revision}`; Start `{expected_revision}`; błędy `{code, message, field_errors}`. GET state dodaje config_revision i instance_id do ListenerState.

- [ ] **1. Test:** 401 bez cookie, 403 z obcym Origin/CSRF, 409 dla starej rewizji i 422 dla walidacji; Start/Stop zwracają 202 bez czekania na connect/disconnect. GET session umożliwia odzyskanie CSRF bez nowego tokenu. Recovery zwraca błąd w state i blokuje Start; jawna naprawa zachowuje backup. GET health nie ujawnia danych.
- [ ] **2. RED:** `python -m pytest tests/api -q` z tymczasowym katalogiem zasobów i atrapami.
- [ ] **3. Implementacja:** rejestracja subskrypcji, snapshot i watermark bez await pomiędzy; potem wyłącznie nowsze eventy. Rozłączenie wolnego klienta nie zmienia listenera. StaticFiles po trasach API, brak fallbacku HTML dla nieznanych /api. CSP, no-store dla sesji/API, brak logowania ciał i sekretów; localhost i inne hosty niż właściwy 127.0.0.1:port odrzucane.
- [ ] **4. GREEN:** dodać asercje snapshotu bez luk/duplikatów, wyczyszczenia kolejki klienta, zasobów przy nieistniejącej ścieżce i requestu traversal; wszystkie tests/api przechodzą. HEAD/GET strony bez sesji dopuszczone do inicjalizacji; dane chronione.
- [ ] **5. Commit:** `feat: expose local API and resynchronizing event stream`.

### Task 8: Single-instance i wątek backendu

**Files:** Create src/desktop/instance.py, backend.py, tests/desktop/test_instance.py, test_backend.py.

**Interfaces:** `InstanceGuard(data_dir: Path).acquire_or_notify() -> bool` (True właściciel), `close()`, sygnał open_requested; `BackendHost(data_dir, static_dir)` z `start()`, `open_url() -> Future[str]`, `request_stop()`, `shutdown() -> Future[None]`, sygnałami ready(origin), failed(error), state_changed(state). Qt sygnały dostarczane do głównego wątku.

- [ ] **1. Test:** dwa równoczesne guardy → dokładnie jeden właściciel i jedno żądanie; stale lock po martwym procesie odzyskiwany, żywy nie jest usuwany; IPC z nieobsługiwaną komendą odrzucane. Fake server zgłasza ready dopiero po gotowości HTTP/assets; timeout 15 s kończy błąd i zwalnia zasoby.
- [ ] **2. RED:** `python -m pytest tests/desktop/test_instance.py tests/desktop/test_backend.py -q`; testy Qt w trybie offscreen, IPC i HTTP tylko loopback.
- [ ] **3. Implementacja:** QLockFile, QLocalServer UserAccessOption, bounded komunikat OPEN_PANEL i ACK; nie usuwać socketu żywego właściciela. Jedno bind port=0 z zachowaniem gniazda, Uvicorn w osobnym wątku asyncio. run_coroutine_threadsafe do komend; token wydawany w pętli. Nie blokować Qt oczekiwaniem na Future.
- [ ] **4. GREEN:** komenda z kroku 2; uruchomienie z błędem importu klienta, zamknięcie podczas startu, awaria wątku po ready, brak gniazd po shutdown. Instancja publikuje niezerowy port, nigdy 0.0.0.0.
- [ ] **5. Commit:** `feat: add single-instance local backend host`.

### Task 9: Minimalny panel i połączenie z backendem

**Files:** Create frontend/package.json, package-lock.json, tsconfig.json, vite.config.ts, index.html, src/main.tsx, src/App.tsx, src/api/{client,events,types}.ts, src/api/client.test.ts, src/api/events.test.ts, src/App.test.tsx.

**Interfaces:** `bootstrapSession(): Promise<void>`; `fetchState(): Promise<AppState>`; `subscribeEvents(onSnapshot, onEvent, onConnection): () => void`; struktury JSON zgodne z zadaniem 7. Vite buduje do frontend/dist, bez CDN. Production panel zawsze obsługiwany z FastAPI; do developmentu budowanie watch i ten sam origin, bez osłabiania sesji przez CORS.

- [ ] **1. Test:** token fragmentu usuwany przez history.replaceState przed wymianą; refresh bez tokenu pobiera CSRF przez GET session. Utrata WS pokazuje „Utracono połączenie z TikoPlay”; reconnect 1,2,5,10 s bez POST start. Zmiana instance_id resetuje watermark i bufor; backend na innym porcie wymaga otwarcia z ikony, brak zgadywania/skanowania portów.
- [ ] **2. RED:** po instalacji przypiętych narzędzi `npm --prefix frontend test -- --run`; testy powinny wykazać brak funkcji, nie błąd runnera.
- [ ] **3. Implementacja:** typowany fetch, rozróżnienie 401 od offline, ws reconnect i deduplikacja. Minimalny ekran pokazuje status i przyciski Start/Stop, bez ręcznej konfiguracji adresu. Każdy listener/subscription ma cleanup.
- [ ] **4. GREEN:** `npm --prefix frontend test -- --run` oraz `npm --prefix frontend run build` (tsc + vite); wynik zawiera index.html i lokalne assets, bez zewnętrznych żądań.
- [ ] **5. Commit:** `feat: add browser panel connection and status screen`.

### Task 10: Launcher, tray i wczesny build z ikony

**Files:** Create src/desktop/launcher.py, tray.py, resources.py, tests/desktop/test_launcher.py, packaging/windows.spec, macos.spec; Modify main.py. Zachować stare src/views i zmiany użytkownika; nowy entrypoint nie importuje MainWindow.

**Interfaces:** `resource_path(relative: str) -> Path`; `run_desktop() -> int`; TrayController(host) z open/stop/quit i fallbackiem okna; QApplication z quitOnLastWindowClosed(False), obsługa macOS reopen. main.py zachowuje działające ustawienie pluginów Qt przed importem Qt.

- [ ] **1. Test:** fake ready uruchamia browser.open raz; wcześniejsze open_requested koaleskowane; timeout wyświetla native error; browser.open=False daje link/ponów, nie zabija hosta. Usunięcie widoku nie zamyka backendu. resource_path dla frozen i ścieżki „Tiko Play Żółć” działa z obcym cwd. Quit wyłącza klawisze przed shutdown i kończy proces po limicie 5 s, bez zabijania obcych procesów.
- [ ] **2. RED:** `python -m pytest tests/desktop/test_launcher.py -q` z atrapą otwierania przeglądarki i hosta.
- [ ] **3. Implementacja:** powiązać tray i sygnały, menu fallback, komunikaty po polsku i obsługę błędów po ready. Dodać minimalne platformowe specyfikacje PyInstaller ze wszystkimi assets i ikonami; nie pakować repo config.json. Windowed/onedir na Windows, BUNDLE na macOS.
- [ ] **4. GREEN:** testy desktop + `npm --prefix frontend run build` + `python -m PyInstaller packaging/macos.spec --noconfirm` na macOS lub windows.spec na Windows. Uruchomić gotową paczkę przez skrót/alias w izolowanej konfiguracji. Potwierdzić brak konsoli i drugiego backendu. Nie modyfikować prawdziwego pulpitu bez potrzeby: testowy alias/skrót można umieścić w katalogu odbioru; końcowy test pulpitu jest w zadaniu 14.
- [ ] **5. Commit:** `feat: launch local web panel from desktop application`. Zanotować platformy rzeczywiście sprawdzone; brak drugiej platformy nie blokuje dalszego kodowania UI, lecz blokuje uznanie wydania za gotowe.

### Task 11: Edytor mapowań, pulpit i logi

**Files:** Create frontend/src/components/{Dashboard,MappingEditor,MappingRow,Settings,EventLog}.tsx i odpowiadające .test.tsx, src/styles.css; Modify App.tsx.

**Interfaces:** komponenty edycji otrzymują `config: AppConfig`, `onChange(next: AppConfig): void`, błędy pól i stan zapisu od kontrolera zadania 12. Logi otrzymują Event[] i onClear (czyści widok, nie backend). Nie utrzymują odrębnego trwałego configu.

- [ ] **1. Test:** zmiana triggera nie zmienia keys; usunięcie pierwszego z trzech id usuwa wyłącznie pierwszy; chip usuwa konkretny klawisz; preset Hugo odwzorowuje 1/2/3/4 → left/right/up/down. Anulowanie zastąpienia presetem zachowuje wpisy. Niepełny wiersz pozostaje szkicem. Tekst `<img onerror=...>` w logu nie tworzy elementu HTML.
- [ ] **2. RED:** `npm --prefix frontend test -- --run` dla nowych komponentów.
- [ ] **3. Implementacja:** ciemny pulpit z menu bocznym, stanami listenera i wyjścia, streamer/filtr/odliczanie, tabela, presety z API, panel ustawień i logów. Start niedostępny przy niepoprawnej konfiguracji, Stop zawsze dostępny podczas connecting/countdown/connected. show_logs nie wyłącza logowania backendu. Informacja o zamknięciu karty przy pierwszym użyciu.
- [ ] **4. GREEN:** testy frontu i build; wizualnie sprawdzić 900×550, skalowanie 200%, tab order, focus i przewijanie. Status nie polega wyłącznie na kolorze. Błędy widoczne poza panelem logów.
- [ ] **5. Commit:** `feat: add complete Polish web control panel`.

### Task 12: Serializowany autosave i naprawa konfiguracji

**Files:** Create frontend/src/state/configController.ts, configController.test.ts, components/ConfigRecovery.tsx, ConfigRecovery.test.tsx; Modify App.tsx i komponenty zadania 11.

**Interfaces:** `ConfigController(api, scheduler)` z `edit(config)`, `flush(): Promise<void>`, `reload(): Promise<void>`, `start(): Promise<void>`; stan draft, saved, revision, saveStatus, fieldErrors, conflict. Start czeka na flush, potem wysyła expected_revision. config_changed przy braku lokalnych edycji odświeża config; przy edycji oznacza konflikt bez nadpisania szkicu.

- [ ] **1. Test:** zegar 499 ms nie zapisuje, 500 ms zapisuje; przy zablokowanej odpowiedzi edit B i C kończą się zapisem A, potem C z nową rewizją (B nie musi być wysłane). Starsza odpowiedź nie cofa draftu C. 409 zachowuje lokalny draft i pokazuje wersję serwera. Błąd zapisu blokuje Start; sukces flush poprzedza Start. Pending restart jest prawdziwy gdy aktywna rewizja różni się od zapisanej.
- [ ] **2. RED:** `npm --prefix frontend test -- --run` dla kontrolera i recovery.
- [ ] **3. Implementacja:** debounce, jeden request w locie i numer lokalnej edycji; po 409 jawny wybór wczytania wersji serwera lub zachowania szkicu do ręcznego uzgodnienia. Brak automatycznego force-overwrite. Recovery poprawnego JSON pokazuje błędne pola; uszkodzony JSON wymaga świadomego odtworzenia ustawień przez POST repair z backupem. Przyszła wersja tylko do odczytu z instrukcją użycia odpowiedniej wersji programu.
- [ ] **4. GREEN:** pełne testy frontend/backend; ręczny test dwóch kart i odświeżenia przy zapisanym configu. Brak fałszywego „Zapisano” przy błędzie lub lokalnym szkicu. Potwierdzić manualny Zapisz i autosave identyczną ścieżką.
- [ ] **5. Commit:** `feat: synchronize edits and recover configuration safely`.

### Task 13: Instalatory, skróty i aktualizacje

**Files:** Create packaging/windows.iss, tests/packaging/test_resources.py, docs/PACKAGING.md; Modify build-macos.sh, build-windows.bat, build.sh, build.spec, packaging/*.spec, .gitignore.

**Interfaces:** build-macos.sh buduje dist/TikoPlay.app i DMG; build-windows.bat buduje dist/TikoPlay/ i instalator z Inno Setup; build.sh deleguje według systemu. build.spec wycofać na rzecz jasnego komunikatu wskazującego właściwy spec lub delegacji, nie utrzymywać wadliwego wspólnego BUNDLE. Skrypty wykonują npm ci, build i dopiero PyInstaller.

- [ ] **1. Test:** brak index.html/assets powoduje błąd przed pakowaniem; manifest zasobów zawiera ikony i frontend, nie repo config.json. Installer ma per-user install, skrót pulpitu do TikoPlay.exe oraz menu Start, brak localhost jako target; uninstall zachowuje dane domyślnie. W skrypcie brak automatycznego usuwania quarantine jako substytutu podpisu.
- [ ] **2. RED:** `python -m pytest tests/packaging -q`; testy struktury zasobów uzupełniają, nie zastępują uruchomienia paczki.
- [ ] **3. Implementacja:** sprawdzenie działającego interpretera venv (nie tylko katalogu), przypięte zależności, platformowe specs, ikony. macOS DMG i instrukcja aliasu na pulpicie. Udokumentować podpisywanie z sekretami z zewnętrznego środowiska, bez generowania/żądania certyfikatów w kodzie. Paczki bez podpisu oznaczyć testowymi.
- [ ] **4. GREEN:** `bash build-macos.sh` na macOS; `cmd /c build-windows.bat` na Windows z Inno Setup. Sprawdzić wynik, instalację, upgrade i uninstall per-user w środowisku testowym bez Python/Node. Raportować osobno build, podpis i uruchomienie.
- [ ] **5. Commit:** `build: package local panel and desktop shortcuts`.

### Task 14: Odbiór całości i dokumentacja

**Files:** Create README.md, docs/WEB_UI_ACCEPTANCE.md, tests/test_application_flow.py; Modify docs/PROJECT_CONTEXT.md i spec (status wdrożenia). Stare GUI wycofywać dopiero po odbiorze; zmodyfikowanych plików użytkownika nie usuwać bez zachowania ich zmian w historii lub uzgodnieniu.

**Interfaces:** raport odbioru: wersja/commit, system, architektura, paczka, wykonany scenariusz, wynik, dowód i ograniczenia; status PASS/FAIL/NOT RUN, nigdy domniemany PASS.

- [ ] **1. Test:** pełny izolowany przepływ: token → sesja → konfiguracja → Start → komentarz z atrapy → jedna akcja → rozłączenie panelu → kolejna akcja → ponowne podłączenie → Stop → brak dalszych akcji. Osobno zmiana konfiguracji wymaga restartu nasłuchu. Test korzysta z realnego lokalnego HTTP/WS i sztucznej klawiatury/TikToka.
- [ ] **2. RED:** `python -m pytest tests/test_application_flow.py -q`; jeśli przepływ już działa, test jest integracyjnym potwierdzeniem i nie wymaga sztucznego psucia kodu.
- [ ] **3. Odbiór:** wykonać 10 scenariuszy z sekcji 14 specyfikacji na obu platformach, w tym rzeczywisty skrót/alias na pulpicie, brak terminala, brak zależności developerskich, TikTok LIVE, klawisze w kontrolowanym oknie, sieć, uśpienie i uprawnienia. Rzeczywista konfiguracja nie jest używana bez potrzeby. Nie uruchamiać prawdziwych klawiszy w tle podczas pracy użytkownika.
- [ ] **4. Weryfikacja:** `python -m pytest -q`, `npm --prefix frontend test -- --run`, `npm --prefix frontend run build`, `git diff --check`; naprawy wymagają własnych testów regresji. Uzupełnić raport i dokumenty stanem faktycznym. Brak Windows/TikTok/certyfikatu jasno oznaczyć; nie deklarować gotowego wydania, jeśli wymagany odbiór nie przeszedł.
- [ ] **5. Commit:** `docs: record web UI verification and desktop usage`; przeprowadzić końcowy przegląd zgodności diffu ze specyfikacją przed integracją gałęzi.

## Wynik przeglądu planu

- Uwzględniono wszystkie sekcje specyfikacji w zadaniach 1–14 i wskazano testy pięciu dodatkowych ryzyk.
- Uściślono odzyskanie CSRF po odświeżeniu i jawną naprawę konfiguracji; bez tych dwóch endpointów wcześniejszy kontrakt nie obsługiwał pełnego UX.
- Rewizje są lokalne dla instancji; instance_id rozstrzyga restart, a stable mapping id pozostaje na dysku.
- Nie obiecuje się ponownego użycia tej samej karty przeglądarki ani przerwania już rozpoczętego wywołania PyAutoGUI.
- Dokument jest planem wykonawczym. Żadne pole wyboru nie jest zaznaczone; implementacja i testy produktu nie zostały wykonane w trakcie planowania.

## Przekazanie do wykonania

Rekomendacja: wykonanie bezpośrednio w tej sesji, zadanie po zadaniu, z końcowym niezależnym przeglądem. Interfejsy są silnie powiązane, więc taki tryb ogranicza koszt przekazywania kontekstu. Alternatywa: osobny agent implementujący i osobny reviewer dla każdego zadania, z większą liczbą niezależnych kontroli i większym kosztem.

Po przeglądzie planu i wyborze metody rozpocząć od zadania 1 w izolowanym worktree, zachowując istniejące zmiany użytkownika. Nie utożsamiać zatwierdzenia projektu architektury z wcześniejszym zatwierdzeniem jeszcze nieistniejącego planu wykonawczego.

## Stan wykonania 2026-09-27

Kod zadań 1–13 oraz lokalna integracja zadania 14 są wdrożone w worktree. Szczegółowe checkboxy pozostawiono niezaznaczone tam, gdzie obejmują także niezrealizowany odbiór Windows/prawdziwego LIVE; nie stanowią aktualnego rejestru testów. Aktualny rejestr: docs/WEB_UI_ACCEPTANCE.md, historia commitów i zapis niezależnego przeglądu. Zmieniono podział commitów i modułów na spójne grupy, bez zmiany kontraktu produktu. Testy po poprawkach review: 42 Python i 9 frontend, build Vite PASS; natywna .app macOS uruchomiona.
