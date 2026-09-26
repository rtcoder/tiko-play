# TikoPlay — projekt przebudowy na lokalny panel webowy

Data: 2026-09-26. Status: szczegółowy projekt i kolejność wdrożenia do przeglądu przez użytkownika; implementacja nie została rozpoczęta.

## 1. Cel i ustalenia

TikoPlay pozostaje aplikacją instalowaną na komputerze z grą. Użytkownik uruchamia ją kliknięciem ikony na pulpicie, tak jak dotychczas. Program sam uruchamia lokalny backend i otwiera panel w domyślnej przeglądarce. Nie wymaga terminala, ręcznego uruchamiania serwera, instalowania Pythona ani Node.js.

Uzgodnione wymagania:

- Panel dostępny tylko na tym komputerze; brak dostępu z telefonu i sieci LAN.
- Priorytetem jest wygoda użytkownika i zachowanie funkcji programu.
- Python nadal odbiera komentarze TikTok LIVE i wykonuje klawisze systemowo.
- Frontend jest panelem obsługi, nie uczestniczy w ścieżce komentarz → klawisz.
- Kliknięcie ikony ma uruchamiać aplikację, a nie samą stronę wymagającą wcześniej włączonego backendu.

Decyzje projektowe proponowane w tym dokumencie: React/TypeScript/Vite, FastAPI/Uvicorn, istniejący PySide6 do traya i komunikatów natywnych, jeden proces aplikacji. Docelowe paczki obejmują Windows i macOS, zgodnie z istniejącymi skryptami. Linux nie jest kryterium wydania tej migracji.

## 2. Zakres i zachowanie funkcjonalności

| Obecna możliwość | Docelowe zachowanie |
| --- | --- |
| Wybór streamera | Pole w panelu, obsługa nicku z opcjonalnym początkowym @ |
| Filtr jednego komentującego | Zachowany; puste pole dopuszcza wszystkich, porównanie do unique_id pozostaje dokładne |
| Dopasowanie komentarza | Cały komentarz, strip i lower; identyczna normalizacja triggerów |
| Jeden klawisz | PyAutoGUI press |
| Wiele klawiszy | PyAutoGUI hotkey, zachowana kolejność; to kombinacja, nie makro |
| Cooldown | 0,3 s na trigger, wspólny dla użytkowników; pomiar monotoniczny |
| Presety | WASD, Strzałki, NumPad, Hugo z zachowaniem obecnych wartości |
| Edycja mapowań | Dodawanie, edycja, usuwanie, wybór klawiszy i chipy kombinacji |
| Zapis | Autosave poprawnych danych po 500 ms i przycisk Zapisz |
| Logi | Opcjonalny podgląd, ostatnie zdarzenia dostępne po ponownym otwarciu panelu |
| Start/stop | Z panelu; dodatkowo zatrzymanie z traya |
| Konfiguracja użytkownika | Ta sama lokalizacja; migracja bez ręcznego przepisywania |

Brak dodawania w tej migracji prezentów, głosowania, makr, profili gier, chmury, kont użytkowników i zdalnego sterowania. Nie obiecujemy wysyłania klawiszy do nieaktywnego okna ani zwiększenia kompatybilności z grami blokującymi PyAutoGUI.

Globalny skrót zatrzymania pozostaje opcjonalnym późniejszym rozszerzeniem: nie jest istniejącą funkcją, wymaga osobnej walidacji bibliotek, uprawnień i kolizji na obu systemach. Stop w panelu i trayu należy do pierwszego wydania.

## 3. Rozważone warianty

1. **FastAPI + React w przeglądarce — wybrany.** Wygodny edytor i logi, niezależność backendu od karty, brak dodatkowego runtime Node u użytkownika. Koszt: osobny frontend i etap budowania zasobów.
2. **FastAPI + prosty HTML/JS.** Mniej narzędzi, ale więcej ręcznego zarządzania edycją, stanem zapisu i synchronizacją kilku kart. Możliwe, lecz mniej wygodne przy rozbudowie panelu.
3. **Panel w WebView.** Osobne okno zamiast przeglądarki, ale dodatkowa obsługa silnika webowego i pakowania. Nie jest potrzebne do uzgodnionego sposobu pracy.

PySide6 zostaje tylko jako powłoka systemowa. Oznacza to większą paczkę niż po całkowitym usunięciu Qt, ale pozwala wykorzystać istniejącą zależność do traya, blokady instancji, IPC i błędów startowych. Ewentualne odchudzanie paczki to osobny etap po pomiarach.

## 4. Uruchomienie z ikony — wymaganie nadrzędne

### Zwykłe uruchomienie

1. Użytkownik klika skrót TikoPlay na pulpicie prowadzący do programu wykonywalnego lub aplikacji .app, nie do adresu HTTP.
2. Launcher ustala ścieżki zasobów niezależnie od bieżącego katalogu roboczego.
3. Uzyskuje blokadę pojedynczej instancji dla bieżącego użytkownika.
4. Inicjalizuje QApplication i tray; zamknięcie ostatniego okna nie kończy procesu.
5. Uruchamia backend na 127.0.0.1 i porcie przydzielonym przez system. Gniazdo jest wiązane raz i przekazywane serwerowi, bez wyścigu „sprawdź port, zamknij, otwórz ponownie”.
6. Czeka na rzeczywistą gotowość HTTP i zasobów panelu, z limitem 15 s. Nie otwiera przeglądarki na ślepo po stałym sleep.
7. Otwiera lokalny panel przez jednorazowy link inicjujący sesję.
8. Panel pobiera konfigurację i stan. Nasłuch jest domyślnie zatrzymany; użytkownik świadomie wybiera Start.

### Ponowne kliknięcie i kilka kart

- Drugi start komunikuje się z istniejącą instancją przez lokalne IPC i prosi ją o otwarcie panelu, po czym kończy się.
- Qt QLockFile i QLocalServer/QLocalSocket stanowią proponowaną podstawę blokady i kanału IPC; IPC ograniczony do bieżącego użytkownika.
- Blokada powstaje przed inicjalizacją listenera. Sam fakt istnienia pliku nie oznacza działającego procesu; obsługujemy pozostałości po awarii.
- Jeżeli pierwsza instancja jeszcze startuje, żądanie otwarcia jest kolejkowane i łączone z początkowym otwarciem.
- W razie zawieszonej, nadal żywej instancji pokazujemy błąd; nie uruchamiamy drugiego silnika i nie zabijamy procesu automatycznie.
- Na macOS obsługujemy również zdarzenie ponownego otwarcia już uruchomionej .app, a nie tylko drugi proces.
- Możliwe jest otwarcie kolejnej karty; przeglądarka nie gwarantuje odzyskania konkretnej istniejącej karty. Nigdy nie powstaje przez to drugi listener.

### Błędy i zakończenie

- Brak zasobów, błąd bind, konfiguracji lub startu backendu: polski komunikat natywny, możliwość otwarcia katalogu diagnostyki, sprzątnięcie częściowo uruchomionych zasobów.
- Nieudane otwarcie przeglądarki: launcher pozostaje dostępny w trayu, oferuje ponowienie oraz skopiowanie świeżego linku do panelu.
- Zamknięcie karty pozostawia backend i nasłuch. Panel informuje o tym przy pierwszym użyciu.
- Tray: Otwórz panel, aktualny status, Zatrzymaj nasłuch, Zakończ TikoPlay.
- Zakończ: natychmiast blokuje nowe akcje, czyści oczekującą kolejkę, zatrzymuje TikToka, kończy WebSocket/HTTP, dołącza wątki i usuwa blokadę/IPC. Limit uporządkowanego zamykania: 5 s, potem raport diagnostyczny i zakończenie procesu. Trwającego natywnego wywołania klawiatury nie można obiecać przerwać w połowie.
- Brak działającego traya: niewielkie natywne okno z Otwórz panel, Stop i Zakończ; proces nie może pozostać niewidoczny bez możliwości obsługi.

## 5. Architektura i współbieżność

```text
Skrót na pulpicie → launcher / Qt w głównym wątku
                         │
                         ├── tray, błędy, single-instance, otwarcie panelu
                         │
                         └── wątek backendu: jedna pętla asyncio
                              ├── FastAPI + Uvicorn, jeden worker
                              ├── ListenerService → klient TikTok LIVE
                              ├── ConfigStore + EventBus
                              └── kolejka akcji → jeden wątek PyAutoGUI

Przeglądarka ← HTTP + WebSocket → FastAPI
TikTok → dopasowanie + cooldown → wykonawca klawiszy → aktywne okno
```

- Rdzeń nie importuje Qt ani FastAPI. UI/API są adapterami do serwisów.
- Wszystkie mutacje stanu listenera i konfiguracji odbywają się w pętli backendu. Qt przekazuje komendy bezpiecznie między wątkami; backend przekazuje stan przez sygnały/kolejkę, bez bezpośredniego operowania widgetami.
- Uvicorn działa bez reload i bez wielu workerów. Nie tworzymy asyncio.run dla każdego startu nasłuchu.
- PyAutoGUI wykonuje działania szeregowo poza pętlą HTTP/TikToka. Proponowany limit kolejki: 100; akcje starsze niż 1 s są pomijane i raportowane. Pełna kolejka odrzuca nową akcję i emituje ograniczony częstotliwościowo komunikat. Są to jawne granice przeciążenia, nie ciche gubienie danych.
- Stop czyści oczekujące akcje; identyfikator generacji sesji uniemożliwia wykonanie starych akcji po kolejnym Starcie.
- Zapis na dysk wykonuje serializowany ConfigStore poza krytyczną obsługą komentarzy.

## 6. Cykl życia listenera i wykonywania akcji

Stany listenera: stopped, connecting, connected, stopping, error. Stan wyjścia klawiatury jest osobny: disabled, countdown, enabled. Dzięki temu komunikat „połączono” nie oznacza automatycznie wysyłania klawiszy.

- Start pobiera niezmienny snapshot zapisanej konfiguracji i jej rewizję; powtarzany Start nie tworzy nowego klienta.
- Stop działa podczas connecting i connected; anuluje oczekiwanie na start, wyłącza akcje i zawsze wykonuje sprzątanie.
- Monitorujemy zadanie zwracane przez klienta TikTokLive oraz jego zakończenie. Nie opieramy stanu wyłącznie na własnej fladze running.
- Streamer offline, nieistniejący użytkownik, utrata sieci i błąd klawiatury mają osobne czytelne komunikaty.
- Po utracie połączenia pierwsza wersja nie wykonuje automatycznego reconnectu; pokazuje błąd i przycisk ponowienia. Jest to zachowanie nie gorsze od aktualnego, bez niespodziewanego wznowienia klawiszy.
- Fail-safe PyAutoGUI pozostaje aktywny. Jego uruchomienie wyłącza akcje i wymaga świadomego ponownego startu.
- Opcjonalne odliczanie 3 s po połączeniu pozwala przełączyć fokus do gry; domyślnie włączone w nowej instalacji, możliwe do wyłączenia. Komentarze w czasie odliczania nie są odkładane do późniejszego wykonania.
- Panel nie próbuje przejąć fokusu po rozpoczęciu nasłuchu. Wybranie konkretnego okna gry pozostaje poza zakresem.

## 7. Konfiguracja i zgodność

Zachowujemy katalog wyznaczany przez src/config.py. Repozytoryjny config.json nadal nie jest źródłem ustawień użytkownika i nie powinien być pakowany jako prywatna konfiguracja.

- Jeden ConfigStore odpowiada za odczyt, walidację i zapis. Żaden widok nie posiada niezależnej kopii przeznaczonej do bezwarunkowego zapisu na dysk.
- Wersja 2 dodaje stabilne identyfikatory mapowań i ustawienie odliczania. Przed pierwszym zapisem migracji tworzymy kopię konfiguracji v1, bez nadpisywania wcześniejszej kopii.
- Poprawne wartości klawiszy, kolejność kombinacji, streamer, filtr i presety są zachowane. Obsługujemy co najmniej wszystkie dotychczasowe klawisze; poprawne dodatkowe klawisze PyAutoGUI z istniejącej konfiguracji nie są automatycznie usuwane.
- Nieznane pola zachowujemy przy migracji. Niepoprawny JSON lub niepoprawne mapowania nie są cicho zastępowane domyślną konfiguracją na dysku; panel oferuje naprawę, a Start jest zablokowany do uzyskania poprawnych danych.
- Duplikaty po normalizacji są zgłaszane do poprawy, bez cichego wyboru ostatniego wpisu. To celowa zmiana usuwająca niejednoznaczność starego zachowania.
- Zapis: plik tymczasowy w tym samym katalogu, flush i atomowa zamiana; błąd zapisu nie zmienia zatwierdzonego stanu w pamięci ani rewizji.
- API zwraca config_revision. Zapis zawiera expected_revision; niezgodność daje 409 i możliwość porównania z aktualnym stanem. Druga karta nie może nadpisać zmian po cichu.
- Autosave jest kolejkowany: jeden zapis naraz, po zakończeniu wysyłana najnowsza poprawna wersja. Niepełny wiersz pozostaje lokalnym szkicem i nie usuwa poprzednio zapisanej konfiguracji.
- Zmiany podczas nasłuchu są zapisywane, ale obowiązują od następnego Startu. Panel pokazuje config_revision, active_config_revision i komunikat o wymaganym restarcie nasłuchu.
- Start jest niedostępny przy niezapisanych lub błędnych zmianach; poprawne oczekujące zapisy są kończone przed wysłaniem komendy Start.

## 8. API i zdarzenia

| Endpoint | Kontrakt |
| --- | --- |
| GET /api/health | Minimalna gotowość, bez konfiguracji i sekretów |
| POST /api/session | Wymiana jednorazowego tokenu otwarcia na sesję |
| GET /api/state | Stan listenera, wyjścia, błąd, rewizje, identyfikator instancji |
| GET /api/config | Konfiguracja i rewizja |
| PUT /api/config | Pełna poprawna konfiguracja i expected_revision |
| GET /api/presets | Presety współdzielone z backendem |
| GET /api/keys | Dostępne klawisze i etykiety |
| POST /api/listener/start | Żądanie startu zatwierdzonej rewizji |
| POST /api/listener/stop | Idempotentne zatrzymanie |
| GET /api/events/recent | Ograniczony bufor ostatnich zdarzeń |
| WS /api/events | Status, konfiguracja zmieniona, komentarz, akcja, błąd |

Komendy start/stop zwracają przyjęcie żądania i bieżący stan, nie blokują HTTP przez czas łączenia. Błędy mają stabilny code, polski message oraz opcjonalne field_errors; UI nie parsuje tekstu wyjątków.

Zdarzenie: id, instance_id, timestamp, type, payload. Bufor ostatnich 1000 zdarzeń i maksymalnie 200 zdarzeń oczekujących na jednego klienta. Wolny klient jest rozłączany i odtwarza stan; nie blokuje listenera. Tekst komentarza w logach ograniczamy do 2000 znaków, ale dopasowanie używa oryginalnej pełnej wartości.

Przy połączeniu WebSocket serwer najpierw rejestruje subskrypcję, następnie przekazuje snapshot stanu i bufora ze znacznikiem sekwencji, potem zdarzenia nowsze od znacznika. Front deduplikuje identyfikatory. Po reconnect pobiera nowy snapshot; brakujące stare logi mogą wypaść poza bufor i są oznaczane jako luka.

Przeglądarka rozróżnia „utracono połączenie z TikoPlay” i „TikoPlay utracił połączenie z TikTokiem”. Reconnect panelu nie uruchamia nasłuchu. Opóźnienia ponowienia panelu: 1, 2, 5, maksymalnie 10 s.

## 9. Dostęp wyłącznie lokalny

- Bind tylko do 127.0.0.1, nigdy do 0.0.0.0. Panel i API mają wspólny origin w paczce produkcyjnej.
- Kontrola Host oraz Origin dla operacji zapisu i WebSocket; brak ogólnego CORS '*'.
- Launcher generuje losowy jednorazowy token otwarcia, ważny 60 s. Przekazuje go we fragmencie URL; frontend usuwa fragment z historii i wymienia token przez POST na sesję.
- Sesja w cookie HttpOnly, SameSite=Strict, unikalnie nazwana dla instancji; wygasa przy zakończeniu backendu. Cookie nie jest izolowane portem, dlatego tokeny/identyfikatory są losowe, a Host/Origin nadal są sprawdzane.
- Mutacje wymagają dodatkowego tokenu CSRF w nagłówku; autoryzacja WebSocket sprawdza cookie i dokładny Origin.
- Każde otwarcie z traya może wydać nowy token otwarcia, bez unieważniania już otwartych kart. Sekrety nie trafiają do logów ani trwałego config.json.
- Brak CDN, zewnętrznych fontów i skryptów. Komentarze renderowane jako tekst, bez interpretacji HTML. Polityka CSP ogranicza skrypty i połączenia do własnych zasobów.
- Model ten chroni przed sterowaniem z obcej strony lub sieci; nie obiecuje izolacji od złośliwego procesu działającego jako ten sam użytkownik.

## 10. Interfejs użytkownika

### Pulpit

Streamer, filtr użytkownika, status połączenia, stan wysyłania klawiszy, Start/Stop i opcja odliczania. Ostatnie komentarze oraz wykonane akcje dostępne w podglądzie logów. Błąd i wymagane działanie są widoczne bez otwierania logów.

### Mapowania

Tabela komentarz → kombinacja, stabilne identyfikatory wierszy, dodawanie/usuwanie klawiszy i mapowań, presety. Zastosowanie presetu zastępuje mapowania dopiero po potwierdzeniu, jeżeli usuwa istniejące wpisy. Stan „Zapisywanie / Zapisano / Błąd zapisu / Niezapisany szkic” jest widoczny. Edycja triggera nie nadpisuje kombinacji.

### Ustawienia i logi

Przełącznik widoczności logów, informacja o działaniu po zamknięciu karty, wersja aplikacji i katalog danych. Wyczyść podgląd nie oznacza zmiany konfiguracji. show_logs steruje widocznością; logowanie błędów nie zależy od istnienia widoku. Diagnostyka na dysku jest rotowana: do 3 plików po 1 MB; domyślnie bez pełnych treści komentarzy. Ostatnie komentarze są buforowane w pamięci.

Całość po polsku, ciemny motyw, obsługa klawiaturą, widoczny fokus, statusy opisane tekstem oprócz koloru. Docelowe minimum panelu: 900 × 550; przy mniejszym oknie przewijanie bez zasłaniania Start/Stop.

## 11. Docelowy podział plików

```text
main.py                       start launchera
src/desktop/launcher.py        cykl życia, gotowość, otwieranie panelu
src/desktop/tray.py            menu systemowe i komunikaty
src/desktop/instance.py        blokada, IPC, ponowne otwarcie
src/core/listener_service.py   stan, start/stop, nadzór nad klientem
src/core/keyboard.py           kolejka i adapter PyAutoGUI
src/core/events.py             zdarzenia i ograniczone bufory
src/core/models.py             modele konfiguracji/stanu
src/core/presets.py            istniejące presety niezależne od Qt
src/config.py                 ścieżka i kompatybilny dostęp do ConfigStore
src/core/config_store.py      walidacja, migracja, zapis
src/api/app.py                 FastAPI i lifecycle
src/api/routes.py              komendy i odczyt
src/api/session.py             sesja, origin, CSRF
src/api/events.py              WebSocket
frontend/                     React, TypeScript, Vite, testy UI
frontend/dist/                wynik builda do paczki
tests/                        testy rdzenia, API i launchera
packaging/                    specyfikacje Windows/macOS i instalator
```

Podział wskazuje odpowiedzialności; nie wymaga tworzenia pustych plików na zapas. Dotychczasowe src/views pozostają do czasu uzyskania zgodności nowego panelu. Nie rozwijamy dwóch niezależnych silników.

## 12. Pakowanie i instalacja

- Build frontendu przed PyInstaller; brak frontend/dist powoduje jasny błąd budowania, nie paczkę z pustym panelem.
- Zasoby pobierane względem paczki, z uwzględnieniem frozen/_MEIPASS. Zachowujemy potrzebną konfigurację pluginów Qt, dopóki paczki nie przejdą testów.
- Przypięte zależności Python i lockfile frontendu. Wersja Pythona wybierana po sprawdzeniu wspólnej zgodności TikTokLive, PySide6 i PyInstaller, a nie na podstawie przypadkowego lokalnego venv.
- Windows: osobny spec PyInstaller w trybie onedir/windowed i instalator per-user, proponowany Inno Setup. Instalator tworzy skrót TikoPlay na pulpicie i w menu Start z właściwą ikoną. Aktualizacja zachowuje katalog danych.
- macOS: osobny spec .app i DMG. Instalacja do Applications, uruchomienie także z aliasu na pulpicie; instrukcja instalacji zawiera utworzenie aliasu. Test akceptacyjny obejmuje właśnie alias. Nie tworzymy skrótu do localhost. Stabilny bundle identifier com.tikoplay.app.
- Paczki budujemy i sprawdzamy na odpowiednich systemach; build na macOS nie potwierdza działania Windows.
- Sprawdzamy uprawnienia do sterowania klawiaturą dla gotowej .app/.exe. Panel pokazuje instrukcję, jeśli system blokuje działanie; uprawnień nie obchodzimy.
- Dla wydania publicznego przewidujemy podpisywanie Windows oraz podpis/notaryzację macOS; brak certyfikatów oznacza jawnie oznaczoną paczkę testową. Usuwanie quarantine na komputerze autora nie jest rozwiązaniem dystrybucji.
- Nie dodajemy autostartu z systemem, usługi systemowej ani automatycznego nasłuchu po zalogowaniu.

## 13. Etapy realizacji i warunki przejścia

### Etap 1 — fundament i testy zgodności

Ochronić zastane zmiany użytkownika, wydzielić presety i logikę dopasowania, ustalić modele oraz adaptery klienta/klawiatury/zegara. Dodać izolowane testy faktycznych zachowań z tabeli zgodności. Wynik: rdzeń możliwy do uruchomienia bez Qt, TikToka i prawdziwych klawiszy w testach.

### Etap 2 — konfiguracja i lifecycle

Wdrożyć ConfigStore, kopię v1, migrację, rewizje, stany listenera, anulowanie startu, monitoring zadania klienta i wykonawcę klawiatury. Wynik: start/stop/error zawsze kończą się spójnym stanem, brak akcji ze starej sesji, zachowane dane użytkownika.

### Etap 3 — lokalne API i zdarzenia

Udostępnić kontrakt HTTP/WebSocket, sesje, kontrolę Origin/Host, bufor zdarzeń i resynchronizację. Wynik: testowy klient steruje jednym serwisem, kilka klientów nie tworzy kilku listenerów, niezautoryzowane komendy są odrzucane.

### Etap 4 — pionowy przekrój uruchomienia z ikony

Zbudować launcher, tray, single-instance i minimalny panel statusu. Wykonać wczesne paczki na Windows i macOS. Wynik: kliknięcie skrótu/aliasu przy wyłączonym programie startuje lokalny serwer i otwiera działającą stronę; ponowne kliknięcie nie uruchamia drugiego silnika. Ten etap poprzedza dopracowanie wyglądu, bo dotyczy nadrzędnego wymagania.

### Etap 5 — kompletny panel

Pulpit, mapowania, presety, autosave, konflikty rewizji, logi, błędy i odliczanie. Wynik: wszystkie dotychczasowe funkcje dostępne w przeglądarce; zamknięcie lub odświeżenie panelu nie zakłóca backendu.

### Etap 6 — paczki i odbiór

Instalator Windows ze skrótem, DMG i alias macOS, testy bez środowiska developerskiego, aktualizacja README i PROJECT_CONTEXT. Po odbiorze wycofać stare główne GUI i nieużywane zależności/importy. Wynik: gotowe paczki z udokumentowaną macierzą testów i znanymi ograniczeniami, nie tylko działający tryb developerski.

Każdy etap wymaga własnej weryfikacji przed kolejnym. Szczegółowa rozpiska implementacyjna na małe zadania, konkretne komendy i commity powstanie po przeglądzie tego projektu; ten dokument ustala zachowanie, granice i kolejność.

## 14. Testy i kryteria odbioru

Automatyczne testy izolują katalog danych, klienta TikTok, zegar i klawiaturę. Nie mogą wysyłać rzeczywistych klawiszy ani korzystać z prywatnego config.json.

| Obszar | Wymagane scenariusze |
| --- | --- |
| Reguły | Normalizacja, pełny komentarz, filtr unique_id, cooldown, kolejność hotkey, wszystkie presety |
| Konfiguracja | v1 → v2, backup, uszkodzony JSON, brak praw zapisu, atomowość, rewizje i dwa klienty |
| Lifecycle | Podwójny Start, Stop w trakcie łączenia, offline, wyjątek, koniec taska klienta, restart po błędzie |
| Klawiatura | Szeregowe wykonanie, przepełnienie, przeterminowane akcje, Stop czyści kolejkę, brak starej generacji |
| API | Walidacja, brak sesji, zły Origin/Host, CSRF, zużyty/wygasły token, niedozwolony WebSocket |
| Zdarzenia | Wolny klient, utrata połączenia, snapshot bez luki, deduplikacja i restart instancji |
| Frontend | Edycja triggera zachowuje klawisze, usunięcie właściwego wiersza, autosave, błędy, konflikty kart |
| Launcher | Gotowość przed otwarciem, równoczesne starty, awaria backendu, brak przeglądarki/traya, sprzątanie |

Obowiązkowy ręczny odbiór gotowych paczek na Windows i macOS:

1. Uruchomienie z pulpitu bez konsoli, Pythona, Node i działającego wcześniej backendu.
2. Ponowne uruchomienie, także podczas startu: jeden backend i jeden listener.
3. Panel otwiera się i pozwala edytować ustawienia bez internetu; TikTok pokazuje wtedy czytelny błąd.
4. Wszystkie presety i własna kombinacja działają w kontrolowanym oknie testowym po nadaniu wymaganych uprawnień.
5. Kontrolowana integracja z prawdziwym TikTok LIVE; potwierdzenie zachowania cooldown i filtra.
6. Zamknięcie karty podczas nasłuchu, ponowne otwarcie z ikony/traya i odświeżenie: brak zatrzymania lub duplikowania akcji.
7. Stop z traya podczas aktywnej gry, potem Zakończ: brak osieroconego serwera i dalszych klawiszy.
8. Odłączenie sieci, uśpienie/wznowienie komputera, błąd uprawnień: zgodny rzeczywisty stan, bez pozornego „połączono”.
9. Instalacja aktualizacji zachowuje konfigurację, skrót i ikonę; odinstalowanie nie usuwa danych bez wyraźnej decyzji użytkownika.
10. Panel przy 900 × 550, większe skalowanie systemowe i obsługa klawiaturą: dostępne najważniejsze przyciski i błędy.

Brak dostępu do jednej platformy lub prawdziwej integracji jest oznaczany jako niewykonany test, a nie sukces. Nowy frontend nie trafia do wydania jako pełny zamiennik przed zaliczeniem macierzy zgodności.

## 15. Ryzyka i wycofanie migracji

- Największe ryzyko: cykl życia procesu i paczki systemowe, nie sam HTML. Dlatego wczesny etap 4 sprawdza ikonę i tray na obu platformach.
- Qt i asyncio wymagają ścisłego podziału wątków. Testy symulują wiele żądań i awarie, ale nie zastępują odbioru systemowego.
- PyAutoGUI nadal działa w kontekście zalogowanej sesji i aktywnego okna. Nie ma obietnicy działania jako usługa bez pulpitu.
- Dodanie kolejki, walidacji i migracji zmienia niektóre błędne zachowania starej wersji; komunikaty i testy muszą je wyjaśniać, bez cichej utraty mapowań.
- Stary frontend pozostaje w repo do odbioru nowego. Powrót do poprzedniej paczki wymaga przywrócenia kopii v1, ponieważ edycje zapisane już w v2 nie są automatycznie synchronizowane z backupem.

## 16. Źródła i stan prac

Podstawa: docs/PROJECT_CONTEXT.md, main.py, src/listener.py, src/config.py, src/ui_logger.py, src/views/main_window.py, presety, lista klawiszy i skrypty pakowania. Uwzględniono zastane niezacommitowane zmiany użytkownika; nie zostały zmodyfikowane.

Dokumentacja użyta do potwierdzenia możliwości narzędzi:

- [FastAPI — WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [FastAPI — pliki statyczne](https://fastapi.tiangolo.com/tutorial/static-files/)
- [Qt — QSystemTrayIcon](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html)
- [Uvicorn — ustawienia procesu i serwera](https://www.uvicorn.org/settings/)
- [PyInstaller — działanie i pakowanie](https://pyinstaller.org/en/stable/operating-mode.html)

To projekt docelowy, nie raport z wdrożenia. Nie naprawiono dotychczasowych błędów, nie zainstalowano zależności, nie uruchomiono integracji ani buildów.
