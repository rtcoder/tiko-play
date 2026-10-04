# TikoPlay — kontekst techniczny

## Instalator Windows — v0.28, 2026-10-04

Ograniczona zmiana istniejącego Inno Setup: PL/EN i informacje przed instalacją, opcjonalny pulpit (unchecked, UsePreviousTasks), jawnie opcjonalny start po instalacji, ograniczenie x64compatible. Zachowano AppId, per-user, tryb rejestru i UsePreviousAppDir, żeby aktualizacja trafiała w poprzednią instalację. Restart Manager uwzględnia także PYD; bez force i bez automatycznego restartu. Brak usuwania AppData/poświadczeń lub wildcardowego czyszczenia instalacji. Odznaczenie pulpitu nie usuwa istniejącego skrótu.

Nowy test `packaging/test-windows-installer.ps1` wymaga jednorazowego GitHub-hosted Windows i czystego stanu TikoPlay. Sprawdza świeżą instalację PL bez pulpitu, aktualizację poprzedniego opublikowanego instalatora w niestandardowym katalogu, EN z pulpitem, reinstalację, hash EXE, rejestr i skróty, start gotowego EXE/health/panel, deinstalację i hashe fixtur AppData. Aplikacja startuje na osobnych danych, bez LIVE; wymuszone zakończenie to wyłącznie sprzątanie testu, nie test poprawnego shutdown. `workflow_dispatch` buduje/testuje bez publikacji; publikacja tylko z tagu po sukcesie wszystkich jobów. Szczegóły i ograniczenia: `docs/PACKAGING.md`, `releases/v0.28.md`.

Lokalnie: 274 testy Python zaliczone (1 natywny pominięty), 53 frontend. Pierwszy przebieg Python w sandboxie miał 11 błędów blokady gniazd; ten sam zestaw poza sandboxem przeszedł. Review wykrył maskowanie testu pulpitu przez skrót z poprzedniej wersji — test teraz usuwa odziedziczony skrót i sprawdza jego odtworzenie oraz pamięć wyboru. Kontrolny workflow 37199517075 przeszedł na wszystkich trzech platformach: buildy, 274 testy Python (1 pominięty) i 53 frontend na każdej. Windows potwierdził świeżą instalację PL, aktualizację v0.27 → 0.28, EN, odtworzenie pulpitu/pamięć wyboru, start zamrożonego EXE oraz deinstalację i zachowanie fixtur danych. Lokalny macOS arm64: build, codesign --verify --deep --strict i hdiutil verify poprawne. Ręczny odbiór na czystym Windows 10/11 bez Pythona/Node, konta bez uprawnień administratora, kreatora PL/EN i zamykania z traya podczas LIVE pozostaje otwarty. Nie utożsamiać runnera Windows Server 2022 z takim odbiorem.

## Ochrona gry i awaryjny STOP — v0.27, 2026-10-04

Wdrożono podstawowy zakres zadania 6; natywny odbiór Windows i fizycznego skrótu w paczce pozostaje otwarty. `OutputGuard` i `TargetIdentity` porównują ścieżkę aplikacji, PID i czas uruchomienia procesu. macOS: NSWorkspace/NSRunningApplication (Cocoa już w zależnościach); Windows: GetForegroundWindow, EnumWindows, QueryFullProcessImageNameW, GetProcessTimes. Brak wyniku lub wyjątek odczytu blokuje chronione wyjście. Cel dotyczy całej aplikacji, nie konkretnego okna/dialogu.

Executor sprawdza `output_check` przed klawiszami/krokami i w pętli hold/wait z interwałem do 50 ms. Wynik negatywny wyłącza executor, zwiększa epokę, czyści kolejkę i raportuje focus_lost z generacją/epoką. Listener ma dodatkowy monitor 50 ms dla bezczynności. Pauza pozostawia czat, ale nie przyjmuje nowych akcji. Wznowienie z panelu czeka na fokus i 3 s jego ciągłości; powrót fokusu po pauzie nie wznawia automatycznie. STOP i cleanup anulują monitor/oczekiwanie, a stara generacja/epoka nie zatrzymuje nowego wyjścia.

`EmergencyHotkey` żyje na głównym wątku Qt. macOS używa Carbon RegisterEventHotKey/InstallEventHandler, Windows RegisterHotKey/WM_HOTKEY i natywnego filtra Qt. Domyślnie Ctrl+Alt+Shift+F10, warianty F9/F11; F12 nie jest używany ze względu na rezerwację Windows. Zmiana z API idzie sygnałem Qt i Future; nowa rejestracja przed zwolnieniem starej. Błąd widoczny, poprzedni skrót pozostaje aktywny. Callback wywołuje istniejący BackendHost.request_stop. Rejestracja zwalniana przy zamknięciu.

`GET/PUT /api/output-safety` i `POST /api/output-safety/resume` korzystają z sesji/origin/CSRF i wspólnej blokady Start/config. Zmiana celu lub skrótu zabroniona podczas connecting/connected/stopping. API ponownie weryfikuje wybraną tożsamość na liście aktualnych procesów. Stan ochrony i skrótu dotyczy bieżącego uruchomienia — brak zapisu PID w profilu. Konfiguracja pozostaje v7, eksport v3. Publiczny OBS nie zawiera nazw/ścieżek procesów.

Weryfikacja: 274 testy Python (1 natywny pominięty), 53 frontend; PID reuse, wyjątek odczytu, przerwanie hold i release, oczekiwanie/odliczanie, brak auto-resume, STOP, konflikt skrótu, auth/CSRF i blokada zmian LIVE. Natywna próba macOS: tożsamości dostępne, rejestracja poprawna, duplikat odrzucony, ponowna rejestracja po close poprawna. Automatyzacja naciśnięcia skrótu w oknie testowym zakończyła się timeoutem — nie uznano odbioru fizycznego skrótu. Dodatkowy test potwierdza wykonanie rejestracji zgłoszonej z wątku backendu na głównym wątku Qt. Build macOS arm64 0.27, metadane wersji, codesign --verify --deep --strict i hdiutil verify poprawne. Panel PL/EN sprawdzony z atrapami (wybór, zastosowanie, odliczanie, Stop, pola blokowane podczas LIVE), brak poziomego overflow i błędów konsoli. Review wychwycił brak tłumaczeń, uzupełniono i zweryfikowano EN.

Ograniczenia: odczyt i wejście OS nie są atomowe, 50 ms nie jest gwarancją, brak kontroli osobnych okien tej samej aplikacji. Odbiór Windows/gry/LIVE, dialogów systemowych i utraty uprawnień pozostaje niewykonany. Plan: `docs/superpowers/plans/2026-10-04-output-safety.md`.


## Kontrola spamu i kolejki — v0.24, 2026-10-01

Wdrożono zadanie 5 roadmapy. Zakładka Kontrola spamu zapisuje `GameProfile.limits`: action_cooldown_ms 0–60000 (300), viewer_cooldown_ms 0–60000 (0), queue_capacity 1–100 (100), action_ttl_ms 100–5000 (1000). Nowe ustawienia działają od kolejnego Startu. Konfiguracja v7 migruje wcześniejsze pliki z kopią oryginału; format eksportu v3 obejmuje limity, importer v1/v2 zachowuje domyślne. Podgląd importu pokazuje parametry.

LIVE używa czystego `Matcher.resolve`, następnie `RateLimiter.check`, `KeyboardExecutor.submit_reason` i `commit` tylko po przyjęciu. Jedynym właścicielem limitera jest pętla listenera; brak await między check i commit. Limiter porównuje całkowite ticki milisekundowe z monotonicznego zegara; symulator korzysta z tego samego mechanizmu. Stan widzów jest ograniczony do 10000 ostatnio przyjętych autorów i czyszczony po 120 s podczas kolejnego sprawdzania/przyjęcia. Przy wyłączonym limicie widza nie jest przechowywany. Nie chroni to przed wieloma kontami/botami.

Kolejka liczy wyłącznie oczekujących. Pełna odrzuca nowe; odmowa nie zużywa cooldownu. TTL sprawdzany tylko przed wykonaniem (strict >, zachowana ważność dokładnie na granicy). Executor raportuje wykonane, wygasłe, anulowane i błędy. Listener odcina wyniki poprzedniej generacji; spóźnione wykonanie po Stop/zmianie epoki nie aktualizuje OBS.

`ControlStats` ma dokładne liczniki przyjęć, wykonań i powodów pominięcia oraz deque 30 decyzji. `ListenerState.control_stats` zapewnia snapshot po reconnect; event control_stats publikuje zmianę najwyżej raz na sekundę. Start resetuje stan i odcina poprzedni timer. Komentarze i wykonania w starym EventLog są próbkowane do 1/s na typ, co jest opisane w panelu; bieżący stan OBS nadal jest aktualizowany po każdym potwierdzonym wykonaniu. Publiczna projekcja OBS nie obejmuje nowych statystyk.

Testy izolują konfigurację i wywołania klawiatury. Sprawdzono odmowę bez cooldownu, granice czasu, 10000 komentarzy, reset/generacje, pojemność, TTL, migrację i eksport. W przeglądarce potwierdzono układ pól, zapis i trwałość po reload oraz wspólne limity w symulatorze. Niezależny review: brak P1/P2. Końcowa kontrola wychwyciła stare numery schematu w formularzu naprawy; poprawiono z regresją v6/v7 zachowującą profile i limity. 266 testów Python zaliczonych (1 natywny pominięty); 51 testów frontendu zaliczonych. Build macOS arm64 0.24 zakończony, metadane wersji, codesign --verify --deep --strict i hdiutil verify poprawne. Odbiór rzeczywistych czatów, gier i Windows pozostaje niewykonany. Plan: `docs/superpowers/plans/2026-10-01-spam-queue.md`.


## Nakładka OBS — v0.21, 2026-09-30

Zadanie 4 ma implementację podstawową, z odbiorem OBS pozostającym do wykonania (OBS nie zainstalowano w środowisku, Windows niedostępny). Osobna zakładka zawiera włącznik, port, kopię adresu, próbny podgląd i ustawienia widoczności/fontu/koloru. `/overlay` jest niezależnym widokiem React z przezroczystym HTML/body. Osobny serwer udostępnia tylko stronę, assets i WebSocket, bez operator API. Domyślnie wyłączony, port 18765 (1024–65535); panel zachowuje port losowy. Konfiguracja gry nadal v6, profile wymiany v2.

`OverlayStore` zapisuje oddzielny `overlay.json` atomowo, 0600 na POSIX. Zawiera token 32 bajtów URL-safe i prezentację. Nick ukryty domyślnie; snapshot nie zawiera wówczas pola autora. Token przechodzi we fragmencie adresu i pierwszej wiadomości WS, z limitem 5 s; Host i Origin muszą odpowiadać dedykowanemu serwerowi. Rotacja jest trwała, odcina istniejące źródła; token nie autoryzuje sesji operatora. Maks. 16 połączeń, odczyt tylko auth/ping. Aktualizacje co najwyżej 5/s, pełny snapshot po reconnect. Timeout send 2 s i close 0,2 s gwarantują wyjście handlera także przy zatkanym transporcie (uvicorn zamyka go po return).

`ListenerService.active_snapshot` przechowuje snapshot Startu dla listy komend w trakcie LIVE. `KeyAction.comment` oraz istniejący actor_id przechodzą do potwierdzenia executora po wykonaniu wszystkich kroków. `last_executed` powstaje tylko z tego potwierdzenia, ma licznik ID i jest czyszczone przed nowym Startem. Komentarz/autor są ograniczone do 2000/128 znaków. Publiczna projekcja ma allowlistę: schema/sequence/mode/paused/commands/last_action/language/presentation — bez kanałów, filtrów, tokenów, błędów i całego czatu.

`OverlayServer.configure` rezerwuje nowy port przed zapisem i zamknięciem poprzedniego; kolizja lub błąd zapisu zachowują poprzednie ustawienia i usługę. Awaria portu przy starcie jest pokazywana w panelu i nie zatrzymuje głównego backendu. GET/PUT `/api/overlay`, POST `/api/overlay/rotate` podlegają sesji/origin/CSRF panelu. Osobny serwer jest zamykany przy shutdown.

Weryfikacja: 257 testów Python zaliczonych (1 natywny pominięty) i 47 testów frontendu zaliczonych, prawdziwy restart serwera z otwartym WS, kolizja portu/błąd zapisu, regresja backpressure z niezależnego review; testy nie używają czatów ani klawiatury systemowej. Przeglądarka: włączenie, przezroczysty CSS, brak poziomego overflow, font 24→32 w otwartej stronie, Pauza→Czat steruje grą z atrapą nasłuchu. Instrukcja i ograniczenia: `docs/OBS_OVERLAY.md`; plan: `docs/superpowers/plans/2026-09-30-obs-overlay.md`.


## Symulator czatu — v0.18, 2026-09-30

Wdrożono zadanie 7 roadmapy: osobna zakładka Symulator, wybór zapisanego profilu/platformy, pojedynczy komentarz oraz rozwijany scenariusz z przykładem spamu. Raport pokazuje przyczyny odrzucenia, kroki press/hold/wait, profil, platformę i rewizję; ostrzega po zmianie zapisu. Niezapisany szkic jest pomijany. Brak zmian schematu konfiguracji v6.

`Matcher.resolve` daje czystą decyzję `MatchDecision`; `decide` dodaje istniejący cooldown. Produkcyjna ścieżka używa tej samej decyzji. `output_policy` współdzieli limity 300 ms, 100 oczekujących i TTL 1 s oraz porównanie wygaśnięcia strict >. Symulator używa integer ms, LIVE nadal sekund monotonicznych. Zachowano zużycie cooldownu przed odmową kolejki. Zakończenie akcji w chwili wiadomości obsługiwane jest pierwsze. Press kosztuje umownie 0 ms; hold/wait według deklaracji, bez opóźnień OS/gry/wątku.

`POST /api/simulation` ma istniejące session/origin/CSRF, limit strumienia 4 MiB i expected_revision (409 przy konflikcie). Model: 1–1000 wiadomości, offset całkowity 0–60000 ms, widz 1–128 znaków, komentarz do 2000 znaków. Wybór profilu nie zmienia aktywnego profilu. Snapshot jest kopiowany, obliczenia wykonują się poza pętlą API; silnik nie ma dostępu do listenera, adaptera klawiatury ani sieci. Symulacja podczas LIVE nie zmienia historii, konfiguracji ani cooldownu.

Weryfikacja: 241 testów Python zaliczonych (1 natywny pominięty), 41 testów frontend zaliczonych; TypeScript/Vite i build macOS arm64 poprawne, podpis ad-hoc zweryfikowany.

Niezależny review odtworzył błędy float przy dokładnie 300 ms cooldownu i 1000 ms TTL; poprawione przez integer clock i test regresji. Test API nazwano `tests/api/test_simulation_routes.py`, aby uniknąć kolizji modułów pytest z testami core. Podgląd przeglądarki na danych tymczasowych potwierdził wyrównanie pól oraz wynik komentarza 8; rzeczywistych czatów i gry nie używano. Plan: `docs/superpowers/plans/2026-09-30-chat-simulator.md`.


## Czytelność mapowań — v0.15, 2026-09-30

Mapowania mają teraz kompaktowy widok „Widz pisze → Naciśnij klawisz”. Jedno press z najwyżej jednym klawiszem ma bezpośredni select; pozostałe akcje opis słowny i przycisk edycji. MappingRow przechowuje wyłącznie stan rozwinięcia, nie kopię danych. Opcje sekwencji rozwijają się bez konwersji lub spłaszczania akcji. Niepoprawne zaawansowane akcje są rozwijane automatycznie i nie można ukryć błędu do czasu poprawienia. Czytelne etykiety/optgroup nie zmieniają identyfikatorów klawiszy zapisywanych w konfiguracji.

ActionEditor ma osobne etykiety typu/czasu i reset marginesów odziedziczonych z globalnych label/input. Select i input mają 42 px oraz wspólną linię na desktopie; na małym ekranie są ułożone pionowo. ProfileManager.compact zwija narzędzia profili tylko na ekranie Mapowania. Brak zmian backendu i formatów danych.

Weryfikacja: 213 testów Python zaliczonych, 1 natywny pominięty; 38 testów frontendu zaliczonych. Kontrola w przeglądarce na konfiguracji tymczasowej: widok prosty, edycja i zapis, wyrównanie select/input (42 px i to samo y), ekran 390 px bez poziomego overflow. Przegląd niezależny wychwycił zwijanie automatycznie otwartego szkicu po poprawieniu błędu; poprawione z testem RED→GREEN, rozwinięcie pozostaje do jawnego zamknięcia.


## Sekwencje klawiszy — v0.14, 2026-09-29

Wdrożono propozycję 2: `ActionDefinition.steps` (1–20), `press(keys)`, `hold(keys, duration_ms)` 50–3000 ms i `wait(duration_ms)` 10–3000 ms, suma czasów do 10000 ms. Modele są niezmienne, nie dopuszczają dodatkowych pól w krokach ani niecałkowitych czasów. `Mapping.action` jest źródłem prawdy; wejściowe `keys` migruje do jednego press, właściwość `Mapping.keys` służy tylko odczytowi pojedynczej starej kombinacji (dla sekwencji zgłasza błąd).

Konfiguracja ma schemat v6. ConfigStore migruje v1–v5 z kopią bajtów oryginału; dotychczasowe profile, ID, filtry i dodatkowe pola mapowań pozostają zachowane. Eksport profilu v2 zawiera wyłącznie nazwę, triggery i action; importer obsługuje v1/v2, zachowuje limity 1 MiB/500 mapowań. NumPad 2468 i szablony nadal tworzą pojedyncze press.

KeyboardExecutor wykonuje jeden krok po drugim, z metadanymi mapowania/widza, epoką wyjścia i terminem rozpoczęcia (domyślnie 1 s od otrzymania). Kolejka ma 100 miejsc; ważność sprawdzana przed rozpoczęciem, nie ucina aktywnej sekwencji po sekundzie. disable/enable zmienia epokę, opróżnia kolejkę i budzi Condition. Klawisze są rejestrowane przed keyDown, zwalniane w finally w odwrotnej kolejności, także po częściowym błędzie down. Cleanup adaptera wywołuje `pyautogui.keyUp.__wrapped__` (przypięte 0.9.54), omijając wyłącznie dekorator fail-safe przy zwalnianiu, bez zmiany globalnego FAILSAFE. Nowe naciśnięcia nadal mają fail-safe, a hold/wait sprawdzają go w interwałach do 50 ms. Wszystkie keyUp są próbowane; błąd dowolnego blokuje wyjście do restartu. Callback błędu release jest globalny, także ze starej generacji. Wywołania OS nie są przerywalne; Stop odcina kolejne kroki i czeka tylko na powrót trwającego wywołania systemowego. Twarde zabicie procesu nie daje gwarancji cleanup.

ActionEditor zapewnia edycję typów, czasów, kombinacji i kolejności, zachowuje niepełne szkice i blokuje ich autosave/Start. Profile, podgląd importu, kopiowanie i EventLog obsługują sekwencje. Dodatkowy koszt: domyślne 1 s na rozpoczęcie może odrzucać kolejkę podczas długiego hold — konfigurowalne limity pozostają propozycją 5. Ochrona fokusu to propozycja 6; wyjście nadal trafia do aktywnego okna.

Plan i decyzje: `docs/superpowers/plans/2026-09-29-key-sequences.md`. Wcześniejsze wpisy poniżej opisują historyczne schematy konfiguracji i profile v1.

## Profile gier — v0.12, 2026-09-28

Wdrożono zadanie 1 z roadmapy wraz z dodatkowym presetem **NumPad 2468**. Schemat konfiguracji v5 zapisuje `profiles` i `active_profile_id`; mapowania i filtry widzów należą do profilu. `AppConfig.mappings` oraz `active_source()` rozwiązują aktywny profil dla istniejącego rdzenia. Pole kanału `target_user` jest wyłącznie wewnętrznym widokiem zgodności, wyłączonym z serializacji; nie jest drugim źródłem danych. Kanały, konta i klucze pozostają globalne. Migracje v1–v4 zachowują bajty oryginału i wszystkie stare mapowania, także ponad 500 wpisów.

`ProfileManager` udostępnia wybór, pusty profil, szablony, zmianę nazwy, duplikowanie z nowymi ID, usuwanie z wyborem zastępcy oraz import z podglądem i eksport. CRUD korzysta z istniejącego PUT konfiguracji i kontroli rewizji; transakcja frontendu najpierw zapisuje szkic i nie podmienia profilu po nieudanym zapisie. Niepełny szkic można odrzucić jawnie. API blokuje zmianę aktywnego profilu i zbioru ID profili przy connecting/connected/stopping. Wspólna blokada serializuje Start i zapis; STOP pozostaje niezależny. Stan sesji podaje nazwę i ID profilu ze Startu.

Szablony: WASD, Strzałki, NumPad 2468, Hugo, Tetris, Pac-Man, Sokoban i Baba Is You. Komentarze `2/4/6/8` wysyłają odpowiednio `down/left/right/up`. Szablony gier wymagają dopasowania ustawień konkretnej wersji; nie są integracją z grą ani obsługą hold.

Format wymiany profilu v1 ma allowlistę nazwy i mapowań bez ID, filtrów i dodatkowych pól. Podgląd importu jest chroniony sesją/origin/CSRF, limituje strumień żądania do 1 MiB oraz 500 mapowań; nadaje nowe identyfikatory i niczego nie zapisuje. Konfiguracja pozwala na 100 profili i wymaga co najmniej jednego. Eksport większego istniejącego profilu trzeba podzielić przed ponownym importem.

Weryfikacja: 191 testów Python poprawnych, 1 natywny pominięty; 31 testów frontend i build TypeScript/Vite poprawne. Przegląd niezależny odtworzył i skorygowano dwa przypadki: blokadę UI po zmianie profilu w drugiej karcie w trakcie importu oraz limit 500 błędnie obejmujący migrację. Oba mają testy RED → GREEN. W przeglądarce na danych tymczasowych i atrapach sprawdzono tworzenie NumPada, mapowania, trwałość po odświeżeniu, PL/EN oraz blokadę profili po Start i odblokowanie po Stop; konsola bez błędów. Build macOS utworzył `TikoPlay.app` i `TikoPlay-0.12-macos-arm64.dmg`; metadane 0.12 i `codesign --verify --deep --strict` poprawne (podpis ad-hoc, bez notaryzacji). Rzeczywistych gier i czatów LIVE nie uruchamiano. Szczegóły decyzji: [plan wykonania](superpowers/plans/2026-09-28-profiles-implementation.md). Pozostałe zadania roadmapy nie zostały wdrożone.

## Roadmapa rozwoju — 2026-09-28

Na prośbę użytkownika zapisano [opis i szczegółowy plan ośmiu rozszerzeń](superpowers/plans/2026-09-28-roadmap-rozwoju.md): profile gier, przytrzymywanie/sekwencje, głosowanie, nakładka transmisji, konfigurowalne limity, ochrona fokusu i awaryjny STOP, symulator oraz widz przy sterach. Dokument określa zależności, proponowane parametry, pliki, interfejsy, kroki testowania i odbiór. W chwili zapisania roadmapy był to wyłącznie plan. Obecnie wdrożono zadania 1, 2, 5 i 7, podstawową ochronę z zadania 6 oraz podstawową nakładkę z zadania 4 (bez odbioru w OBS); pozostałe wymagają osobnego wdrożenia. Istniejące limity kolejki (100 akcji, ważność 1 s) zostały uwzględnione jako punkt wyjścia, nie jako brakująca funkcja.

Wersja 0.9 obejmuje dokumentację roadmapy i aktualizację numeru wymaganą przez zasady tagowania każdego zestawu zmian. Nie zmienia zachowania aplikacji; wcześniejsze sekcje opisują stan odpowiednich historycznych wydań.

Weryfikacja tego zestawu: 12 testów wersjonowania/pakowania i 23 testy frontend przeszły; walidator wydania i build macOS zakończyły się poprawnie. Powstały `dist/TikoPlay.app` i `dist/TikoPlay-0.9-macos-arm64.dmg`. Nie wykonywano odbioru LIVE ani testów nowych funkcji, ponieważ dokument ich nie implementuje.

## Automatyczne wydania i wspólna wersja — 2026-09-28

Pierwszy workflow v0.7 zbudował instalator Windows i obie paczki macOS, ale zablokował publikację na `test_second_instance_notifies_owner` w Windows. Test uruchamiał dwa obiekty w jednym wątku i blokował pętlę zdarzeń serwera; teraz uruchamia rzeczywistą drugą instancję w osobnym procesie i sprawdza sygnał oraz kod zakończenia. Poprawka testu jest częścią v0.8; nie zmienia produkcyjnego IPC.

`VERSION` jest jedynym źródłem wersji aplikacji (`major.minor`, obecnie 0.8). React osadza go przy buildzie w `.version` i Ustawieniach; macOS używa go w Info.plist, a skrypty w nazwach DMG i instalatora Windows. Usunięto historyczne stałe 2.0/2.0.0 z aktywnego UI i pakowania. Wersja schematu konfiguracji pozostaje niezależna.

`.github/workflows/release.yml` reaguje na push tagu `v*`: `release_support.py` sprawdza zgodność z VERSION i niepusty opis w `releases/<tag>.md`; trzy runnery budują macOS arm64/Intel i Windows x64 oraz uruchamiają testy. Dopiero wszystkie poprawne buildy pozwalają opublikować release z opisem i sumami SHA-256. Opis musi być napisany przed tagowaniem; walidator sprawdza obecność treści, a jej jakość pozostaje obowiązkiem autora. Numery dobieramy do liczby i znaczenia zmian, z uzasadnieniem w opisie, zamiast mechanicznego +1. Szczegóły: `AGENTS.md` i `docs/PACKAGING.md`.

Lokalna weryfikacja: 174 testy Python, 1 natywny pominięty offscreen; 23 testy frontend i build TypeScript/Vite poprawne. Testy HTTP/WebSocket wymagają dostępu do lokalnych portów. Zbudowano `dist/TikoPlay.app` i `dist/TikoPlay-0.8-macos-arm64.dmg`. Paczki nadal bez podpisu dystrybucyjnego/notaryzacji; Windows i Intel podlegają odrębnej weryfikacji workflow i odbiorowi na docelowym systemie.

## Systemowe menu traya — 2026-09-28

Na macOS ikona używa bezpośrednio AppKit (`src/desktop/mac_tray.py`): `NSStatusItem` z przypiętym `NSMenu`. Lewy i prawy klik otwierają menu systemowe; przeglądarka otwiera się po wyborze „Otwórz panel”. Usunięto macOS-owy popup Qt i oczekiwanie na aktywację aplikacji. Qt nadal przechowuje model akcji i tłumaczeń, ale nie wyświetla ikony ani menu na Cocoa, więc natywne śledzenie menu omija ścieżkę Qt opisaną w QTBUG-147449. Ikona pozostaje szablonem 18 pt. Na pozostałych platformach lewy klik pokazuje istniejące menu kontekstowe Qt, prawy używa standardowej obsługi traya.

Weryfikacja: 165 testów Python przeszło (1 natywny pominięty offscreen). Osobno wykonano bezpośrednio funkcję testową prawdziwego AppKit (runner pytest-qt zawieszał się w przygotowaniu pętli Cocoa): przypięcie menu, ikona template, akcje panel/stop/quit, aktualizacja PL/EN i statusu oraz usunięcie ikony. Zbudowano aktualną `dist/TikoPlay.app` i `dist/TikoPlay-2.0.0-test.dmg`; weryfikacja podpisu ad-hoc aplikacji przeszła. Fizyczne kliknięcia w paczce nie zostały zweryfikowane. Poniższe opisy popupu i otwierania panelu kliknięciem ikony są historyczne.

## Język polski / angielski — 2026-09-28

Aktualny panel React i powłoka desktopowa obsługują PL/EN. Pierwszy start bez poprawnego `preferences.json` pokazuje natywny dialog „Wybierz język / Choose language” przed backendem i przeglądarką. `QLocale.system().uiLanguages()` określa główny język interfejsu systemu: `pl` → Polski, `en` i pozostałe → English. Użytkownik zawsze zatwierdza wybór; anulowanie kończy uruchomienie bez zapisu. Dotyczy to również istniejących instalacji bez wybranego języka.

Preferencja jest zapisywana atomowo w `preferences.json` w tym samym katalogu danych co konfiguracja (także z `--data-dir`), niezależnie od `config.json` v4 i przeglądarki. Zmiana przez Ustawienia → Język działa bez restartu, aktualizuje tray oraz inne otwarte karty przez `preferences_changed`; nie zmienia rewizji konfiguracji, mapowań ani aktywnego nasłuchu. Endpointy `/api/preferences` korzystają z istniejących zabezpieczeń sesji/origin/CSRF. Nieudany zapis zachowuje poprzedni wybór.

Katalog `src/locales/en.json` jest wspólny dla Reacta i Qt; polskie teksty źródłowe są kluczami. Komunikaty rdzenia/API pozostają tekstami źródłowymi i są tłumaczone podczas wyświetlania, tak samo jak historia zdarzeń. Treść komentarzy, nicki, triggery, klawisze i identyfikatory presetów nie są tłumaczone. Tłumaczenie obejmuje aktywną aplikację, nie historyczne GUI w `src/views`. `packaging_support.py` dołącza katalog językowy do obu paczek. Dodając komunikat, należy uzupełnić katalog i tłumaczenie na granicy UI; nie podawać do tłumacza treści użytkownika.

Weryfikacja: 165 testów Python przeszło, 2 natywne testy traya pominięte w trybie offscreen; 24 testy frontend i build TypeScript/Vite poprawne. Testy wykorzystują dane tymczasowe i atrapy integracji. W przeglądarce sprawdzono zmianę PL ↔ EN i oba motywy. Testy sprawdzają wybór według systemu, restart, anulowanie, błędny plik preferencji, błąd zapisu, synchronizację kart, tłumaczenie traya oraz niezmienione komentarze i presety. Paczka macOS `dist/i18n/TikoPlay.app` zbudowana i uruchomiona na danych tymczasowych: health, panel z `lang="en"` i dołączony katalog tłumaczeń potwierdzone. Paczki Windows nie uruchamiano.

## Zakładki platform — 2026-09-28

Select źródła zastąpiony grupą czterech zakładek nad lewą kartą ustawień: ikona SVG + nazwa platformy. `PlatformTabs` obsługuje ARIA tablist/tab/tabpanel, pojedynczy punkt wejścia Tab, strzałki i Home/End. Aktywna ikona ma kolor platformy; układ dostosowuje się do szerokości i obu motywów. Zapis i przełączanie źródeł używają dotychczasowego onChange. Testy panelu: 21 passed; TypeScript/Vite build poprawny; wizualnie sprawdzono motywy Klasyczny i Glass.

## YouTube i Kick — 2026-09-27

Dodano źródła `youtube` i `kick` do wspólnej fabryki/rdzenia oraz panelu. Nadal działa tylko jedno źródło naraz; mapowania są wspólne, kanały i filtry oddzielne. Konfiguracja v4 migruje v1/v2/v3 z kopią oryginału, zachowując aktywnego Twitcha w migracji v3. Historia notatek poniżej dotyczy wcześniejszych etapów.

YouTube: link/ID konkretnej transmisji → oficjalne `videos.list` → bezpośredni `StreamList` przez gRPC. Wpisywany w panelu klucz API tylko w natywnym keyring (`TikoPlay.YouTube/api-key`), write-only `/api/youtube/key`, istniejące cookie/origin/CSRF. Mutacje klucza i Start są serializowane; klucza nie zmienia się podczas nasłuchu YT. Filtry używają stabilnych ID kanałów `UC…`, dokładne dopasowanie. Pierwsza paczka historii i wiadomości starsze niż rozpoczęcie połączenia są pomijane; deduplikacja; tylko zwykłe komentarze tekstowe. Protobuf to minimalny podzbiór schematu Google z zachowaniem numerów pól, wygenerowany plik w repo. Nowe runtime: grpcio/protobuf; generator grpcio-tools tylko dev.

Kick: na życzenie użytkownika integracja nieoficjalna, anonimowa i lokalna — publiczny odczyt kanału i Pusher WSS, żadnego webhooka/serwera/tunelu. Obsługuje dwie wersje nazw kanałów/zdarzeń z deduplikacją; czeka na potwierdzenie subskrypcji, obsługuje heartbeat i sprząta po anulowaniu startu. Opcjonalne `kick.chatroom_id` omija zablokowany odczyt loginu; to ID jest autorytatywne, nie jest weryfikowane z loginem. Panel wyjaśnia to i czyści ID przy zmianie loginu. Filtr loginów ignoruje wielkość liter.

Nieoczekiwana utrata połączenia zatrzymuje klawisze i wymaga ponownego Start. Testy izolują konfigurację, magazyn klucza i klawiaturę. Pełny wynik: 150 testów Python + 20 frontend, 2 natywne pominięte. Paczka macOS `dist/youtube-kick/TikoPlay.app` zbudowana i uruchomiona testowo na izolowanych danych; health i panel działają. Weryfikacja i ograniczenia: [YOUTUBE_KICK_ACCEPTANCE.md](YOUTUBE_KICK_ACCEPTANCE.md). Istniejące zmiany traya/Cocoa zostały zachowane.

## Pierwsze kliknięcie menu traya (macOS)

W paczce `LSUIElement` menu Qt mogło zostać otwarte przed aktywacją aplikacji. Użytkownik potwierdził, że pierwszy wybór „Zakończ” nie działał, a drugi zamykał program. Test natywny odtworzył otwieranie menu przy `NSApplication.isActive() == False`. Tray teraz żąda aktywacji Cocoa i czeka na `applicationStateChanged(ApplicationActive)` przed pokazaniem menu; aktywna aplikacja pokazuje je od razu. Zachowano odpięte menu chroniące przed QTBUG-147449. Jawna zależność macOS: `pyobjc-framework-Cocoa`. Test aktywnej i nieaktywnej aplikacji: `QT_QPA_PLATFORM=cocoa python -m pytest tests/desktop/test_tray_native.py -q`; w testach offscreen jest pomijany. Test natywny nie zastępuje odbioru fizycznego kliknięcia w zbudowanej paczce.

## Integracja Twitch — 2026-09-27

W izolowanym checkoutcie wdrożono wybór TikTok/Twitch (jedno aktywne źródło), konfigurację v3 z migracją v1/v2, niezależne kanały/filtry i wspólne mapowania. Nowe adaptery `twitch.py`, `twitch_protocol.py`, `twitch_auth.py`, `twitch_credentials.py`; fabryka w `adapters/chat.py`. `ListenerService` otrzymuje fabrykę całej konfiguracji, a stan podaje aktywną platformę/kanał/generację. Filtr Twitcha jest case-insensitive, TikToka zachowuje wcześniejsze zasady.

OAuth: publiczny Client ID z `src/twitch_settings.py` lub `TIKOPLAY_TWITCH_CLIENT_ID`, DCF i wyłącznie `user:read:chat`. Tokeny tylko w natywnym keyring; wszystkie endpointy `/api/twitch/auth` podlegają istniejącym zabezpieczeniom sesji. Brak Client ID nie blokuje TikToka. Żaden prywatny token nie został dostarczony ani użyty w implementacji.

Stan odbioru i ograniczenia: [TWITCH_ACCEPTANCE.md](TWITCH_ACCEPTANCE.md). Testy na atrapach nie dowodzą rzeczywistego działania Twitcha. Specyfikacja i plan znajdują się w `docs/superpowers`, a kod pozostaje w checkoutcie funkcji do decyzji o integracji z main.


## Wielu dozwolonych użytkowników

Pole „Dozwoleni użytkownicy” obsługuje nicki po przecinku, średniku albo w osobnych wierszach, opcjonalnie z `@`. Puste pole (również same białe znaki) dopuszcza wszystkich; same separatory/znaki `@` są odrzucane. Zachowano tekstowe pole `target_user` w konfiguracji v2, więc pojedynczy wcześniej zapisany nick działa bez migracji. Matcher przygotowuje zbiór nicków, zachowuje dokładne dopasowanie z rozróżnianiem wielkości liter i wspólny cooldown 0,3 s na akcję. Zmiana listy w czasie nasłuchu, tak jak pozostałe ustawienia, wymaga Stop → Start.

## Otwieranie panelu

Każde jawne żądanie otwarcia panelu (kliknięcie traya, „Otwórz panel”, kolejne uruchomienie aplikacji) otwiera nową kartę domyślnej przeglądarki przez `webbrowser.open_new_tab`. Na życzenie użytkownika nie wykrywamy ani nie przywołujemy istniejących kart i nie łączymy równoległych żądań otwarcia.

## Awaria po kolejnych kliknięciach traya (macOS 27)

Raporty `TikoPlay-2026-09-27-114548.ips` i `TikoPlay-2026-09-27-114938.ips` potwierdziły SIGABRT w `libqcocoa.dylib` → `NSEvent.clickCount` podczas natywnego śledzenia menu (Qt 6.11.2, macOS 27.0). To ścieżka opisana w [QTBUG-147449](https://qt-project.atlassian.net/browse/QTBUG-147449). Na macOS `TrayController` nie przypina już QMenu przez `setContextMenu`; lewy klik otwiera panel, prawy pokazuje QMenu przez `popup`. Windows zachowuje natywne przypięte menu. Usunięto otwieranie przeglądarki na każde `ApplicationActivate`; jawne akcje traya i IPC kolejnego uruchomienia nadal otwierają panel. Test regresji sprawdza 20 aktywacji, osobne menu i jawne zakończenie; 46 testów przeszło. Paczka przebudowana. Fizyczne kliknięcia wymagają potwierdzenia użytkownika — narzędzie UI nie uzyskuje dostępu do aplikacji działającej wyłącznie w trayu.

## Ikona traya macOS

`src/desktop/tray_icon.py` tworzy przezroczysty, monochromatyczny kontur wielkiego, pochylonego „T”, zgodny ze znakiem głównej ikony w rozmiarach 18/36/54 px. `QIcon.setIsMask(True)` przekazuje macOS dobór białego/czarnego koloru do wyglądu paska menu, również przy zmianach motywu. Pozostałe platformy zachowują `tiko_play.ico`; ikona Docka/aplikacji pozostaje bez zmian.

## Wygląd panelu — tylko Glass (2026-09-28)

Jedyny styl panelu to Glass, stosowany bezwarunkowo przez `frontend/src/styles-glass.css` na wspólnych stylach komponentów i układu z `frontend/src/styles.css`. Usunięto motyw klasyczny, komponent przełącznika i jego testy oraz odczyt/zapis preferencji `tikoplay-theme` w localStorage. Wcześniej zapisany wybór nie wpływa na wygląd. Glass nie ma limitów szerokości kontenera i treści; bazowy padding `:root body` wynosi `32px` z każdej strony. Zachowano wewnętrzne odstępy i responsywność. Inspiracja: CodePen Aysenur Turk (ZEpxeYm); tło to lokalne gradienty CSS.

## Aktualizacja 2026-09-27: wdrożony panel webowy w worktree

Nowy `main.py` uruchamia launcher Qt/tray, jeden backend FastAPI na loopback i panel React dołączony do paczki. Rdzeń znajduje się w `src/core`, integracje w `src/adapters`, API w `src/api`, powłoka systemowa w `src/desktop`, frontend w `frontend`. Zapis konfiguracji v2 jest atomowy z backupem v1; aktywny listener używa snapshotu ze Startu. Testy używają atrap i katalogów tymczasowych. Uruchomienie developerskie i paczki opisuje README.md; rzeczywisty stan odbioru, ograniczenia i wyniki opisuje [WEB_UI_ACCEPTANCE.md](WEB_UI_ACCEPTANCE.md).

Poniższy tekst zachowano jako **historyczną analizę starego GUI**. Opisane w nim problemy nie powinny być automatycznie przypisywane nowemu rdzeniowi. Stare pliki i zmiany użytkownika nie zostały usunięte; w nowym entrypoincie nie są uruchamiane. Windows i rzeczywista integracja LIVE wymagają odbioru.


Stan analizy: 2026-09-26. Przeczytano wszystkie 11 plików Python aplikacji, konfigurację repozytoryjną, skrypty budowania i lokalny diff. Punktem odniesienia jest HEAD `77079d9` oraz niezacommitowane zmiany. Dokument opisuje stan zastany, nie docelowy projekt.

## Planowana przebudowa interfejsu — jeszcze niewdrożona

Szczegółowy projekt i etapy migracji zapisano w [projekcie lokalnego panelu webowego](superpowers/specs/2026-09-26-local-web-ui-design.md). Wymagania użytkownika: panel tylko na komputerze z grą, zachowanie funkcji programu i uruchamianie kliknięciem ikony na pulpicie. Propozycja: FastAPI + React, Python jako niezależny silnik, PySide6 do traya i launchera. Dnia 2026-09-27 użytkownik zaakceptował przejście do następnego etapu. Powstał [plan wykonawczy obejmujący 14 zadań](superpowers/plans/2026-09-27-local-web-ui.md), oczekujący przeglądu i wyboru trybu wykonania. Dokumenty nie oznaczają wykonania migracji ani napraw poniższych błędów.

## Do czego służy

TikoPlay to niewielka aplikacja desktopowa do sterowania grą lub innym programem komentarzami z TikTok LIVE. Użytkownik podaje streamera, opcjonalnie jednego dopuszczonego komentującego i mapowania pełnego komentarza na klawisz lub kombinację klawiszy.

Program nie zawiera własnej gry, serwera HTTP ani bazy danych. PyAutoGUI wysyła klawisze systemowo; kod nie wybiera okna docelowego, więc znaczenie ma aktualny fokus. Nie ma obsługi prezentów, polubień ani głosowania widzów.

Interfejs jest po polsku, z ciemnym stylem, trzema zakładkami: Streamer, Klawisze, Użytkownik oraz przyciskiem start/stop nasłuchu. Opcjonalny panel logów zależy od konfiguracji; nie ma przełącznika logów w GUI.

## Mapa kodu

| Plik | Rola |
| --- | --- |
| `main.py` | Punkt wejścia, QApplication, styl i MainWindow; ustawia ścieżkę pluginów Qt w paczce PyInstaller. |
| `src/config.py` | Ścieżka danych użytkownika, domyślna konfiguracja, odczyt i zapis JSON. |
| `src/listener.py` | Klient TikTokLive, filtrowanie komentarzy i użytkownika, cooldown, wysyłanie klawiszy. |
| `src/ui_logger.py` | QObject z sygnałem `message(str)` do przekazywania logów do UI. |
| `src/views/main_window.py` | Nawigacja, zapis streamera/użytkownika, uruchomienie listenera w wątku. |
| `src/views/log_view.py` | QTextEdit tylko do odczytu, dopisywanie i przewijanie logów. |
| `src/views/key_editor/key_editor.py` | Lista mapowań, presety, ręczny zapis i timer autosave. |
| `src/views/key_editor/mapping_row.py` | Edycja triggera i klawiszy jednego mapowania. |
| `src/views/key_editor/key_chip.py` | Przycisk klawisza; kliknięcie usuwa go z mapowania. |
| `src/views/key_editor/presets.py` | WASD, Strzałki, NumPad i Hugo. |
| `src/views/key_editor/special_keys.py` | Lista liter, cyfr, strzałek, modyfikatorów i klawiszy funkcyjnych. |
| `build.spec`, `build*.sh`, `build-windows.bat` | Pakowanie PyInstaller, macOS .app i DMG, skrypt Windows. |

## Przepływ działania

1. `MainWindow` wczytuje konfigurację i przekazuje ten sam słownik do `KeysEditor`.
2. Streamer i użytkownik mają osobne przyciski „Zapisz”. Edytor mapowań ma zapis ręczny i zamierzony autosave z opóźnieniem 500 ms.
3. Start nasłuchu ponownie wczytuje JSON do `MainWindow.config`, leniwie importuje `TikTokListener`, tworzy wątek daemon i uruchamia w nim `asyncio.run(...)`.
4. Listener ustawia `running=True`, usuwa część przed pierwszym `@`, buduje słownik triggerów pisanych małymi literami i rejestruje handler `CommentEvent`.
5. Komentarz jest normalizowany przez `strip().lower()`. Dopasowanie dotyczy całego komentarza, nie fragmentu. Duplikaty triggerów po zmianie wielkości liter: ostatnie mapowanie wygrywa.
6. Niepusty `target_user` wymaga dokładnej zgodności z `event.user.unique_id`. Ten filtr nie usuwa `@`, białych znaków ani nie normalizuje wielkości liter.
7. Cooldown wynosi 0,3 s na trigger, wspólnie dla wszystkich użytkowników, i korzysta z `time.time()`.
8. Jeden klawisz powoduje `pyautogui.press`, kilka — `pyautogui.hotkey(*keys)`. To kombinacja, nie makro wpisujące sekwencję znaków ani sterowanie z czasem przytrzymania.
9. `stop()` zmienia flagę; pętla listenera sprawdza ją co 0,1 s po zakończeniu startu klienta, następnie rozłącza klienta.

Konfiguracja listenera jest przygotowywana przy starcie. Zmiany podczas nasłuchu nie są świadomie synchronizowane; użytkownik powinien zatrzymać nasłuch, zapisać zmiany i uruchomić go ponownie, z zastrzeżeniem problemów edytora poniżej.

W lokalnie obecnym TikTokLive 6.6.5 `await client.start()` zestawia połączenie i zwraca Task pętli WebSocket. TikoPlay ignoruje ten Task i czeka na własną flagę. Nie należy zakładać, że `start()` blokuje przez cały czas transmisji. Sprawdzono to w lokalnym kodzie biblioteki, nie w dokumentacji sieciowej.

## Konfiguracja — ważna pułapka

`CONFIG_PATH` wskazuje na:

- macOS: `~/Library/Application Support/TikoPlay/config.json`;
- Windows: `~/AppData/Roaming/TikoPlay/config.json`;
- pozostałe platformy: `~/.config/TikoPlay/config.json`.

Import `src.config` tworzy katalog aplikacji. Pierwsze wczytanie zapisuje wartości domyślne, jeśli plik nie istnieje. Uszkodzony JSON daje wartości domyślne w pamięci. Brakujące pola są uzupełniane; nie ma migracji wersji ani walidacji typów.

Przykładowy schemat:

```json
{
  "version": 1,
  "show_logs": false,
  "streamer_id": "",
  "target_user": "",
  "mappings": [
    {"trigger": "lewo", "keys": ["left"]},
    {"trigger": "skrot", "keys": ["ctrl", "a"]}
  ]
}
```

Repozytoryjny `config.json` zawiera wcześniejsze ustawienia i jest dodawany do paczki w `build.spec`, ale aktualny loader go nie używa. Nie traktować go jako aktywnej konfiguracji ani domyślnego szablonu. Nie odczytywano prywatnego pliku konfiguracji poza repozytorium w ramach tej analizy.

## Uruchamianie i budowanie

Zależności runtime w `requirements.txt`: PySide6, TikTokLive, pyautogui. Brak przypiętych wersji i lockfile. Brak deklaracji minimalnej wersji Pythona.

Standardowy start ze środowiska mającego zależności, z katalogu repozytorium:

```sh
python -m pip install -r requirements.txt
python main.py
```

Zastane środowiska lokalne pochodzą z Pythona 3.14.2. `.venv/bin/python` wskazuje na istniejący plik, natomiast `venv/bin/python` ma zerwany symlink. Metadane w `.venv`: PySide6 6.10.1, TikTokLive 6.6.5, PyAutoGUI 0.9.54. Są to dane lokalnego środowiska, nie gwarantowana kompatybilność ani wymagania projektu.

- `bash build-macos.sh`: używa `venv`, instaluje zależności i PyInstaller, usuwa `build`/`dist`, buduje `dist/TikoPlay.app`, usuwa quarantine i tworzy `TikoPlay.dmg` w katalogu repozytorium. Samo istnienie uszkodzonego `venv` uniemożliwia jego automatyczne odtworzenie przez ten skrypt.
- `build-windows.bat`: podobny przebieg, wspólny `build.spec`. Spec ma bezwarunkowy `BUNDLE` macOS i konfigurację EXE bez `COLLECT`; wypisywana przez skrypt ścieżka `dist\TikoPlay\` wymaga weryfikacji z rzeczywistym wynikiem. Build Windows nie został sprawdzony.
- `bash build.sh`: minimalny skrypt tworzący `venv` i wywołujący PyInstaller.
- `build.spec` zawiera ukryty import `pynput`, którego nie ma w zależnościach ani kodzie aplikacji. Brak podpisywania/notaryzacji w skryptach.

Przy zmianach pakowania zachować mechanizm ścieżki Qt w `main.py` i leniwy import listenera w `toggle_listener`, dopóki nie zostanie sprawdzone ich zastąpienie. Są obecne w historii jako osobne poprawki.

## Problemy stwierdzone w analizie kodu — nienaprawione

1. **Logger może być `None`.** Domyślnie `show_logs=false`. `MainWindow.save_config()` zapisuje plik, po czym bezwarunkowo wywołuje `self.logger.log`, co powoduje AttributeError. Tak samo logują trzy gałęzie obsługi błędów startu listenera. Helper `TikTokListener.log()` już obsługuje brak loggera, ale te gałęzie go omijają.
2. **Rozdzielenie konfiguracji po starcie.** `toggle_listener()` podmienia `MainWindow.config`, a `KeysEditor.config` nadal wskazuje stary słownik. Autosave zapisuje stary słownik, natomiast callback ręcznego zapisu zapisuje nowy `MainWindow.config`. Może to gubić mapowania lub cofać ustawienia streamera/użytkownika.
3. **Autosave edycji nie jest wywoływany.** W `add_row` callback `lambda: self.schedule_autosave` tylko zwraca metodę. Po `rebuild()` callback to `lambda: None`. Timer jest uruchamiany przy dodawaniu/usuwaniu mapowania i zastosowaniu presetu, ale nie przy zwykłej edycji istniejącego wiersza.
4. **Niepoprawne indeksy początkowych wierszy.** `add_row()` dla każdego istniejącego mapowania ustawia `index=len(mappings)-1`. Usunięcie dowolnego początkowego wiersza usuwa ostatnie mapowanie. Lambda `on_remove=lambda r=mapping: ...` przyjmuje indeks przekazany przez `MappingRow`, więc problemem jest indeks, nie rzekome przekazanie słownika do porównania liczbowego. `rebuild()` nadaje poprawne indeksy.
5. **Dwa niespójne modele klawiszy w MappingRow.** Ukryte `key_boxes` powstają przez `add_key_box`, ale nie są dodawane do layoutu. Widoczne chipy i selektor zmieniają bezpośrednio `mapping['keys']`. Późniejsza edycja triggera wywołuje `update()` i nadpisuje klawisze zawartością starych, ukrytych comboboxów. Osobny przycisk `+` również dodaje ukryty combobox. Pusty/nieobsługiwany klawisz w nieedytowalnym comboboxie może zostać zastąpiony pierwszym elementem, `a`.
6. **Stan listenera i GUI nie odzwierciedla awarii.** Po obsłużonym błędzie startu `running` pozostaje `True`; brak `finally`, sygnału zakończenia i aktualizacji przycisku z wątku. Inne błędy mogą zakończyć wątek bez sprzątania. Zakończenie Task klienta nie jest monitorowane; brak reconnectu. Stop w trakcie łączenia nie anuluje samej operacji startu.
7. **Możliwe wyścigi start/stop.** Flaga jest ustawiana dopiero w wątku, a lambda wątku odczytuje zmienne `self.listener` i `self.config`. Szybkie kliknięcia mogą zmienić te referencje. Brak jawnego zamykania i dołączania wątku przy zamknięciu okna. To ryzyko wynikające z konstrukcji, bez odtworzenia runtime.
8. **Słaba walidacja i trwałość JSON.** `load_config` zakłada słownik; np. poprawny JSON będący listą wywoła błąd przy `setdefault`. `DEFAULT_CONFIG.copy()` współdzieli zagnieżdżoną listę mapowań. Zapis nie jest atomowy. Edytor odrzuca tylko mapowania z pustym triggerem lub pustą listą klawiszy, nie sprawdza duplikatów czy pustych elementów; po filtrowaniu nie przebudowuje wierszy.

Dodatkowe uwagi: synchroniczne wywołania PyAutoGUI blokują pętlę asyncio na czas wykonania; logi są nieograniczone; `build_keys_view()` i `TikTokListener.task` nie są używane. `self.stack` jest dodawany do layoutu drugi raz przy włączonych logach; układ wymaga sprawdzenia wizualnego. Stretch w edytorze początkowo poprzedza wiersze, a `rebuild()` go usuwa.

Jeżeli zadaniem będzie naprawa, sensowna kolejność to: spójna konfiguracja i brak loggera → jeden model klawiszy, indeksy oraz autosave → cykl życia listenera → walidacja i powtarzalny build. Ta kolejność jest sugestią, nie zaakceptowanym planem wdrożenia.

## Weryfikacja i granice tej analizy

- Parsowanie `ast.parse` wszystkich 11 plików Python zakończyło się powodzeniem. Potwierdza składnię, nie poprawność działania.
- W repozytorium nie znaleziono testów, konfiguracji test runnera ani CI.
- Nie uruchamiano GUI, nasłuchu TikTok, wysyłania klawiszy, instalowania zależności ani buildów. Problemy powyżej wynikają z analizy źródeł; nie są raportem z testów integracyjnych.
- Przyszłe testy powinny izolować `CONFIG_PATH` i zastępować klienta TikTok oraz PyAutoGUI. Priorytetowe scenariusze: zapis z wyłączonymi logami, edycja mapowania po starcie, dodanie klawisza i zmiana triggera, usunięcie pierwszego z kilku wierszy, autosave oraz streamer offline/start-stop.

## Zastany stan roboczy

Przed tą analizą istniały niezacommitowane zmiany użytkownika:

- `src/listener.py`: usuwanie `@`, obsługa trzech wyjątków klienta;
- `src/ui_logger.py`: metoda `connect_log_view`;
- `src/views/main_window.py`: QButtonGroup, inicjalizacja pól i wspólny zapis z logowaniem.

Były też nieśledzone `.DS_Store` i katalogi `__pycache__`. Nie usuwano ich ani nie zmieniano kodu aplikacji. W tej sesji dodano wyłącznie `AGENTS.md` oraz niniejszy dokument. Stan Git i środowiska jest chwilowy: kolejna sesja powinna sprawdzić go ponownie.
