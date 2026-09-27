# Twitch Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. Recommended for this plan: native execution via executing-plans, with a final independent review.

**Goal:** Dodać lokalny nasłuch Twitcha sterujący klawiaturą, z wyborem jednej aktywnej platformy TikTok / Twitch.

**Architecture:** Adaptery platform zasilają wspólny matcher i wykonawcę klawiatury. Twitch używa EventSub WebSocket oraz osobnej usługi OAuth DCF z natywnym magazynem tokenów. Konfiguracja v3 przechowuje ustawienia obu źródeł, ale aktywny nasłuch działa na niezmiennym snapshotcie.

**Tech Stack:** Istniejący Python/asyncio, FastAPI/Pydantic, PySide6, React/TypeScript, pytest/Vitest; HTTP przez httpx, transport przez istniejące websockets, magazyn przez keyring.

**Spec:** [Zatwierdzony projekt](../specs/2026-09-27-twitch-chat-design.md).

Status: wykonano w trybie Native; odbiór rzeczywistego Twitcha i Windows pozostaje niewykonany. Wyniki i ograniczenia w `docs/TWITCH_ACCEPTANCE.md`.

## Global Constraints

- Jedna aktywna platforma naraz; poza zakresem wysyłanie czatu i dodatkowe zdarzenia Twitcha.
- Wspólne mapowania, cooldown 0,3 s na trigger, opcjonalne odliczanie 3 s.
- Konfiguracja v3; migracja v1/v2 z kopią oryginalnych bajtów, atomowy zapis, zachowanie rozszerzeń danych.
- Konfiguracja nadal trafia wyłącznie do katalogu użytkownika. Repozytoryjny `config.json` nie jest źródłem ustawień.
- Publiczny klient DCF; jedyny zakres `user:read:chat`; bez `client_secret` i publicznego serwera.
- `TIKOPLAY_TWITCH_CLIENT_ID` w rozwoju, publiczna stała w wydaniu. Brak ID nie blokuje TikToka.
- Tokeny tylko w natywnym magazynie macOS/Windows, bez jawnego fallbacku. Testy nie dotykają rzeczywistych poświadczeń.
- Walidacja sesji przy przywróceniu i co godzinę; serializacja rotacji refresh tokena.
- Deduplikacja: 600 s, najwyżej 10 000 wpisów na cache, zachowanie cache przez kontrolowany reconnect.
- Nieoczekiwana utrata połączenia wymaga ponownego Startu. Stop blokuje nowe akcje przed sprzątaniem sieci.
- Zmiany ustawień wymagają Stop → Start; stare generacje nie mogą wykonać akcji.
- Testy izolują katalog konfiguracji, klienty sieciowe, magazyn poświadczeń i klawiaturę.
- Historyczne `src/views` pozostaje poza zakresem; oba motywy panelu muszą działać.

## Review Focus

1. Spóźniony zapis tokenów po odłączeniu konta — lokalne poświadczenia pozostają usunięte (zadanie 2).
2. Timeout po zużyciu jednorazowego refresh tokena — brak ślepego retry; wymagana nowa autoryzacja (zadanie 2).
3. Duplikat wiadomości na starym i nowym socketcie — dokładnie jedna akcja również po upływie cooldownu (zadania 3–4).
4. Edycja platformy w drugim panelu podczas nasłuchu — UI pokazuje rzeczywisty aktywny snapshot, konflikt nie gubi konfiguracji (zadanie 6).
5. Pełny dysk lub istniejąca kopia migracji — oryginał i poprzednia kopia pozostają nienaruszone (zadanie 1).

## Wykonanie i organizacja plików

Przed kodowaniem sprawdzić stan Git i utworzyć izolowany checkout zgodnie z `using-git-worktrees`; nie nadpisywać cudzych zmian. Kroki wykonywać kolejno. Każde zadanie kończy się testami wskazanego zakresu i osobnym commitem obejmującym tylko jego pliki. Nie oznaczać ręcznych odbiorów jako wykonanych na podstawie atrap.

Podział: modele/migracja i matcher w `src/core`; adaptery, OAuth i tokeny w `src/adapters`; publiczne ustawienia integracji w nowym `src/twitch_settings.py`; endpointy w `src/api/twitch.py`; składanie usług w `src/desktop/backend.py`; komponent ustawień źródeł w `frontend/src/components/ChatSourceSettings.tsx`. Nie tworzyć ogólnego systemu pluginów ani osobnego silnika klawiatury dla Twitcha.

### Task 1: Konfiguracja v3 i dopasowanie użytkowników

**Pliki:** zmienić `src/core/models.py`, `src/core/config_store.py`, `src/core/users.py`, `src/core/matching.py`; testy `tests/core/test_config_store.py`, `tests/core/test_matching.py`.

**Interfejsy:**
- `Platform = Literal["tiktok", "twitch"]`.
- `ChannelConfig(channel: str = "", target_user: str = "")`; `AppConfig` ma `platform`, `tiktok`, `twitch` oraz wspólne dotychczasowe pola, `version: Literal[3]`.
- `AppConfig.active_source() -> ChannelConfig` zwraca sekcję wybraną przez `platform`.
- `Matcher(config: AppConfig, clock=time.monotonic)` i `match(user_id: str, comment: str)` zachowują dotychczasowy kontrakt wyniku.

- [x] Dodać testy migracji v1/v2, zachowania ID, rozszerzeń oraz osobnych ustawień źródeł. Główne asercje: `snapshot.config.version == 3`, `snapshot.config.tiktok.channel == legacy["streamer_id"]`, `backup.read_bytes() == original`, `snapshot.config.platform == "tiktok"`.
- [x] Dodać przypadki kolizji kopii, błędu zapisu kopii/replace i przyszłej wersji: `path.read_bytes() == original`, istniejąca kopia niezmieniona. Dodać matcher Twitcha: `match("ALICE", " left ") == ("left",)`, dla TikToka odmienna wielkość liter nadal nie pasuje; puste listy dopuszczają wszystkich, same separatory są błędem.
- [x] Uruchomić `.venv/bin/python -m pytest tests/core/test_config_store.py tests/core/test_matching.py -q`; nowe testy mają zawieść z powodu brakujących zachowań.
- [x] Wprowadzić modele i normalizację: Twitch trim, opcjonalne `@`, lowercase; przyjmować login, odrzucać URL i białe znaki wewnątrz loginu. Puste kanały wolno zapisać, ale nie wolno z nimi startować. Migracja usuwa stare pola korzenia, zachowuje rozszerzenia; kopie `config.vN.backup.json`, przy kolizji `config.vN.backup.<uuid>.json`.
- [x] Dostosować matcher do aktywnej sekcji. Zachować monotoniczny cooldown i dokładne dopasowanie pełnego tekstu.
- [x] Powtórzyć testy tego zadania: wszystkie PASS. Commit `feat: migrate chat configuration to v3`.

### Task 2: OAuth DCF i bezpieczne przechowywanie sesji

**Pliki:** utworzyć `src/twitch_settings.py`, `src/adapters/twitch_credentials.py`, `src/adapters/twitch_auth.py`, `tests/core/test_twitch_credentials.py`, `tests/core/test_twitch_auth.py`; zmienić `requirements.txt`, `requirements-dev.txt`.

**Interfejsy:**
- `get_twitch_client_id() -> str` w ustawieniach; stała wydania domyślnie pusta, env ma pierwszeństwo.
- `TwitchCredentials`: wewnętrzny dataclass z `client_id`, `user_id`, `login`, `access_token`, `refresh_token`, `expires_at: float` (czas Unix); tokeny z `repr=False`.
- `CredentialStore` ma asynchroniczne `load() -> TwitchCredentials | None`, `save(credentials) -> None`, `delete() -> None`. `NativeCredentialStore` implementuje ten kontrakt; atrapa testowa nie używa keyring.
- `TwitchAuthService(client_id, store, http, events, *, clock, sleep)`; `restore()`, `start() -> dict`, `cancel()`, `disconnect()`, `close()` asynchroniczne; `state() -> dict` synchroniczne; `credentials() -> TwitchCredentials` asynchroniczne, po walidacji/odświeżeniu.
- Stan publiczny: `configured: bool`, `status: "disconnected" | "pending" | "connected" | "error"`, `login: str | None`, `error: dict | None`. Odpowiedź `start` dodaje `user_code`, `verification_uri`, `expires_at`; te dane nie są buforowane w EventBus.
- `subscribe_invalidated(callback: Callable[[], None]) -> Callable[[], None]` rejestruje natychmiastowy callback utraty uprawnień i zwraca funkcję wyrejestrowania; korzysta z niego zadanie 4.

- [x] Dodać testy DCF: sukces, pending, odmowa, wygaśnięcie, anulowanie, throttling, wymiana konta, dwa panele; HTTP i zegary są atrapami. Asercje: zakres wysłany to dokładnie `user:read:chat`, brak client secret; `save_calls == 0` po anulowaniu spóźnionej próby; anulowanie zachowuje wcześniej połączone konto.
- [x] Dodać testy odnowienia i invalidation: równoległe wywołania powodują jedną rotację, `saved.refresh_token == new_refresh_token`; niejednoznaczny timeout powoduje `refresh_calls == 1` i wymóg logowania. Walidacja przed użyciem i po 3600 s odrzuca inne client ID/user ID/zakres; 401 unieważnia sesję, błąd sieci blokuje korzystanie z nieweryfikowanej sesji bez udawania cofnięcia uprawnień.
- [x] Dodać test magazynu: backend plaintext odrzucony, operacja poza pętlą asyncio, błędy dostępu redagowane; po wylogowaniu `await store.load() is None` nawet gdy wcześniejszy zapis kończy się późno lub revoke zawodzi.
- [x] Uruchomić `.venv/bin/python -m pytest tests/core/test_twitch_auth.py tests/core/test_twitch_credentials.py -q` i potwierdzić RED.
- [x] Zaimplementować magazyn jednego rekordu JSON w natywnym keyring; stały service/account dla TikoPlay. Serializować modyfikacje tokenów oraz operacje logout, sprawdzać generację próby po każdym await. Nie logować wyjątków z sekretami ani treści odpowiedzi OAuth.
- [x] Zaimplementować usługę OAuth z wstrzykniętym klientem httpx, timeoutem HTTP, interwałem DCF, bezpiecznym odświeżaniem i zadaniem walidacji. `close` anuluje wszystkie zadania bez usuwania poprawnie zapisanej sesji. Odłączenie najpierw emituje invalidation; revoke ma ograniczony timeout, usunięcie lokalne działa niezależnie.
- [x] Zadeklarować httpx jako zależność runtime (obecnie przypięty w dev do 0.28.1), dodać kompatybilną, zweryfikowaną podczas implementacji przypiętą wersję keyring; nie aktualizować niezwiązanych bibliotek. Potwierdzić GREEN i commit `feat: add Twitch device authorization and credential storage`.

### Task 3: Adapter EventSub

**Pliki:** utworzyć `src/adapters/chat.py`, `src/adapters/twitch.py`, `src/adapters/twitch_protocol.py`, `tests/core/test_twitch_adapter.py`, `tests/core/test_twitch_protocol.py`; dostosować `src/adapters/tiktok.py` tylko jeśli wymaga tego kontrakt.

**Interfejsy:**
- `CommentHandler = Callable[[str, str], Awaitable[None]]` i `ChatAdapter` Protocol z `async connect(on_comment: CommentHandler) -> asyncio.Task[None]`, `async disconnect() -> None`.
- `TwitchAdapter(channel: str, auth: TwitchAuthService, http, ws_connect, *, clock=time.monotonic)`; factory później w zadaniu 4.
- `SeenMessages(ttl=600, limit=10000, clock=time.monotonic).accept(event_id: str, message_id: str) -> bool` w `twitch_protocol.py`, dwa ograniczone cache; TTL nie jest odnawiany przez duplikaty.
- `validate_reconnect_url(url: str) -> str`: wss, hostname równy `eventsub.wss.twitch.tv` albo jego subdomena, bez userinfo, tylko port domyślny/443; inną domenę odrzuca. Dokładna allowlista musi zostać potwierdzona z oficjalnym protokołem przy implementacji; nie rozszerzać jej na arbitralne hosty.

- [x] Napisać scenariusze: Welcome → zaakceptowana subskrypcja → wiadomość; `connect` nie kończy się przed sukcesem subskrypcji. Asercje danych żądania: type `channel.chat.message`, version `1`, broadcaster ID wybranego kanału, user ID z uwierzytelnionej sesji, session ID z Welcome.
- [x] Testy parsowania: `callback_calls == [("alice", "left")]`; duplikaty z różnymi kopertami i tym samym chat ID nie dodają wywołania; Shared Chat z obcego kanału pomijany; pusty wynik Helix to błąd kanału, 403 to brak uprawnień. Brak transmisji LIVE nie blokuje czatu.
- [x] Testy keepalive, watchdog, revocation, błędnych danych, nieznanych zdarzeń, reconnect i anulowania. Dwa sockety dostarczające ten sam chat dają jeden callback; podczas handoff `subscription_calls == 1`, po Welcome nowego socketu stary zamknięty. Timeout transferu kończy child task błędem. Deduplikacja ograniczona do 10 000 wpisów i 600 s.
- [x] Uruchomić `.venv/bin/python -m pytest tests/core/test_twitch_adapter.py tests/core/test_twitch_protocol.py -q`, potwierdzić RED.
- [x] Zaimplementować protokół oraz adapter na httpx/websockets. Obsłużyć ping/pong biblioteką, ustawić limity rozmiaru ramki i ograniczoną kolejkę; nie wysyłać własnych komend do EventSub. Zakładać subskrypcję w limicie Welcome; brak pola limitu oznacza domyślne 10 s. Watchdog odnawiać zgodnie z ruchem serwera, z timeoutem Welcome.
- [x] Zaimplementować handoff z równoległym odczytem starego socketu, wspólnymi cache i zamknięciem obu po Stop. `disconnect` działa także po częściowym błędzie `connect`; nie zamyka wspólnego HTTP należącego do backendu. Potwierdzić GREEN i commit `feat: receive Twitch chat through EventSub`.

### Task 4: Jeden silnik dla dwóch źródeł

**Pliki:** zmienić `src/adapters/chat.py`, `src/core/models.py`, `src/core/listener_service.py`, `tests/core/test_listener_service.py`, `tests/core/test_listener_races.py`, `tests/core/test_adapters.py`; nowy `tests/core/test_chat_factory.py`.

**Interfejsy:**
- `ChatAdapterFactory(auth, http, ws_connect).__call__(config: AppConfig) -> ChatAdapter` wybiera adapter z aktywnej sekcji.
- `ListenerState` dodaje `active_platform: Platform | None`, `active_channel: str | None`.
- `ListenerService.start(snapshot)` zachowuje synchroniczny kontrakt; factory otrzymuje `snapshot.config`. Weryfikacja pełnych poświadczeń następuje asynchronicznie w `connect`, przed uzbrojeniem klawiatury.
- `ListenerService.authorization_lost() -> None` zatrzymuje wejście Twitcha natychmiast i zachowuje błąd wymaganej autoryzacji. Wywołanie przy aktywnym TikToku nic nie zmienia.

- [x] Uaktualnić istniejące fixtures do v3, dodać test wyboru fabryki oraz stanu: `active_platform == "twitch"`, `active_channel == "alice"`; zapis konfiguracji innego kanału/platformy nie zmienia aktywnego klienta.
- [x] Testować Stop w connect/countdown/handoff, utratę auth, błąd klawiatury i spóźnione callbacki: brak nowych akcji, czysta kolejka, stara generacja ignorowana przed matcherem i publikacją komentarza. Duplikat po 0,4 s nadal daje `len(keyboard.actions) == 1`, dzięki adapterowi.
- [x] Uruchomić `.venv/bin/python -m pytest tests/core/test_listener_service.py tests/core/test_listener_races.py tests/core/test_chat_factory.py -q`, potwierdzić RED nowych zachowań.
- [x] Wpiąć fabrykę i aktywny snapshot. Komentarze w EventBus dodają `platform`, `channel` i `generation`; zachować istniejące `user`, `comment`. Wszystkie błędy ogólne uogólnić, błędy specyficzne pozostawić w adapterach.
- [x] Zablokować wyjście i opróżnić kolejkę przed publikacją stanu awarii i przed await sprzątania; nie maskować błędu autoryzacji jako zwykłego Stopu. Świadomie zachować granicę już rozpoczętej akcji PyAutoGUI.
- [x] Uruchomić `.venv/bin/python -m pytest tests/core -q`; wszystkie PASS, również TikTok. Commit `feat: route selected chat source through listener service`.

### Task 5: API autoryzacji i składanie backendu

**Pliki:** utworzyć `src/api/twitch.py`, `tests/api/test_twitch.py`; zmienić `src/api/app.py`, `src/desktop/backend.py`, `tests/api/test_routes.py`, `tests/desktop/test_backend.py`, `tests/test_application_flow.py`.

**Interfejsy:** `create_twitch_router(auth: TwitchAuthService) -> APIRouter`; `create_app(..., static_dir: Path, *, twitch_auth: TwitchAuthService)`; wszystkie testowe wywołania dostają atrapę. Backend tworzy magazyn, wspólny klient HTTP, auth i fabrykę; rejestruje `listener.authorization_lost` przez kontrakt zadania 2.

- [x] Testy GET/start/cancel/DELETE pod `/api/twitch/auth`, stanu po przeładowaniu, brakującego client ID; odpowiedzi nie zawierają access/refresh/device code. Parametryzować POST/DELETE bez cookie, poprawnego originu lub CSRF: odmowa zgodna z istniejącymi testami sesji.
- [x] Test odłączenia: Twitch blokuje klawiaturę przed revoke; TikTok działa dalej. Test startu Twitcha bez autoryzacji daje błąd przed jakąkolwiek akcją. Test shutdown anuluje DCF, walidator i transport, zamyka wspólne HTTP.
- [x] Uruchomić `.venv/bin/python -m pytest tests/api/test_twitch.py tests/desktop/test_backend.py tests/test_application_flow.py -q`, potwierdzić RED.
- [x] Dodać router przed fallbackiem `/api/{path:path}` i montażem panelu. Start listenera weryfikuje dostępność autoryzacji (409 z kodem `twitch_auth_required`), kanał pozostaje walidacją 422. Eksportować jedynie stan publiczny usługi; prywatnych struktur nie serializować automatycznie.
- [x] Składać usługi i zamykać w kolejności listener → auth → HTTP. Przywracanie sesji Twitcha nie może blokować gotowości TikToka; zadanie restore jest śledzone i anulowane przy shutdown. Dodać logi wyłącznie z redagowanymi kodami błędów.
- [x] Uruchomić `.venv/bin/python -m pytest tests/api tests/desktop tests/test_application_flow.py -q`, potwierdzić GREEN. Commit `feat: expose Twitch authorization in local API`.

### Task 6: Panel wyboru źródła i konta

**Pliki:** nowe `frontend/src/components/ChatSourceSettings.tsx`, `frontend/src/components/ChatSourceSettings.test.tsx`; zmienić `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/api/client.test.ts`, `frontend/src/components/EventLog.tsx`, `frontend/src/components/EventLog.test.tsx`, `frontend/src/components/ConfigRecovery.tsx`, `frontend/src/state/configController.test.ts` oraz istniejące fixtures v2 w testach frontendu. Style dopisać tylko w razie potrzeby w obu istniejących arkuszach.

**Interfejsy:** TypeScript `AppConfig`, `AppState`, `TwitchAuthState` odpowiadają zadaniom 1, 2 i 4. `twitchAuthApi` eksportuje `state`, `start`, `cancel`, `disconnect`, korzystając z istniejącego klienta CSRF. `ChatSourceSettings` dostaje `config`, `onChange(Partial<AppConfig>)`, `auth`, `onAuthChanged()`; komponent nie zarządza odrębną kopią całej konfiguracji.

- [x] Testy selektora i osobnych ustawień: przełączenie tam i z powrotem zachowuje kanały/filtry i wspólne mapowania. Test DCF: kod i link widoczne po Start, znikają po zakończeniu/anulowaniu; link otwierany wyłącznie kliknięciem, obcy host odrzucony.
- [x] Testy Startu, aktywnego snapshotu, autosave i konfliktu drugiego panelu. Asercje: Start disabled przy błędnym zapisie/braku auth, nagłówek aktywnego nasłuchu nadal pokazuje Twitch mimo szkicu TikToka, konflikt nie wysyła nadpisującego PUT. Stan auth po przeładowaniu jest pobierany przez GET; zdarzenie `twitch_auth` aktualizuje stan, reconnect odświeża go ponownie.
- [x] Uruchomić `npm --prefix frontend test -- --run`, potwierdzić RED nowych scenariuszy.
- [x] Zaimplementować komponent, API i integrację z istniejącym ConfigController. Panel rozróżnia autoryzowane konto i wybrany kanał. Teksty polskie: „Źródło czatu”, „Połącz konto Twitch”, „Odłącz konto”, „Anuluj logowanie”; wyjaśnić brak skonfigurowanego client ID.
- [x] Uaktualnić odzyskiwanie konfiguracji do v3, logi oznaczyć platformą/kanałem; usunąć sztywne napisy TikTok z elementów ogólnych. Pokazywać informację o oczekujących zmianach według aktywnej rewizji. Nie przechowywać tokenów ani kodów aktywacji w localStorage.
- [x] Ponownie uruchomić testy oraz `npm --prefix frontend run build`; oczekiwany exit 0. Sprawdzić oba motywy przez lokalny panel z atrapą backendu/autoryzacji. Commit `feat: add Twitch source and account controls to panel`.

### Task 7: Pakowanie, końcowa regresja i odbiór

**Pliki:** zmienić `packaging/macos.spec`, `packaging/windows.spec`, `tests/packaging/test_resources.py`, `README.md`, `docs/PROJECT_CONTEXT.md`; utworzyć `docs/TWITCH_ACCEPTANCE.md`. Bez zmian historycznych skryptów, chyba że aktualny build ich wymaga.

**Interfejsy:** gotowy kontrakt aplikacji z zadań 1–6, żadne nowe API.

- [x] Uzupełnić test zasobów/konfiguracji builda: paczka zawiera właściwy backend keyring dla platformy oraz transport HTTP/WS, nie zawiera client secret, tokenów ani konfiguracji użytkownika. Uruchomić `.venv/bin/python -m pytest tests/packaging -q` i potwierdzić brakujące elementy.
- [x] Dodać potrzebne importy/dane keyring do speców PyInstaller; używać backendu platformy, nie plaintext. Udokumentować rejestrację publicznego klienta, ustawienie `TIKOPLAY_TWITCH_CLIENT_ID`, logowanie i brak autowznowienia po awarii.
- [x] Uruchomić `.venv/bin/python -m pytest -q`, `npm --prefix frontend test -- --run`, `npm --prefix frontend run build`, `git diff --check`; wszystkie muszą zakończyć się kodem 0. Nie zastępować niezaliczonego testu opisem ograniczenia.
- [x] Zbudować na bieżącym macOS przez `.venv/bin/python -m PyInstaller --noconfirm packaging/macos.spec`, po sprawdzeniu, że nie nadpisze potrzebnych artefaktów użytkownika. Sprawdzić start paczki i dostępność natywnego magazynu. Windows: analogiczny build z `packaging/windows.spec` na Windows; gdy brak hosta, oznaczyć odbiór Windows jako niewykonany.
- [ ] Po dostarczeniu prawdziwego client ID i zalogowaniu przez użytkownika sprawdzić na rzeczywistym kanale: odbiór, filtr, akcję, Stop, restart, utratę autoryzacji. Wykonywanie rzeczywistych klawiszy wymaga kontrolowanego okna testowego. Bez tych warunków wpisać „niewykonane” i konkretną zależność; nie uznawać integracji LIVE za zweryfikowaną.
- [x] Zapisać wyniki/wersje/ograniczenia w TWITCH_ACCEPTANCE, zaktualizować PROJECT_CONTEXT i README. Wykonać końcowy niezależny przegląd zgodnie z wybranym trybem, poprawić znalezione problemy i powtórzyć dotknięte testy. Commit `build: package and document Twitch integration`.

## Handoff

Rekomendowany tryb: **Native** — zadania są sekwencyjne i współdzielą kontrakty konfiguracji, autoryzacji i cyklu życia; jeden implementer ogranicza koszt przekazywania kontekstu. Na końcu niezależny przegląd całości. Alternatywa **Subagent-driven**: implementer i reviewer dla każdego zadania, większy koszt kontekstu i wcześniejsze niezależne przeglądy.

Przed kodowaniem użytkownik przegląda ten plan i wybiera tryb. Brak publicznego client ID nie blokuje implementacji ani testów na atrapach, ale blokuje rzeczywiste logowanie i końcowy odbiór Twitcha.
