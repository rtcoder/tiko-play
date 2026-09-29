> Stan 2026-09-29: zadanie 1 wdrożone w v0.12; zadanie 2 wdrożone w v0.14. Szczegóły zakresu i zależności: [plan sekwencji](2026-09-29-key-sequences.md). Pozostałe zadania są propozycjami.

# TikoPlay — opis funkcji i plan rozwoju

> **Dla wykonawcy:** dokument zawiera osiem propozycji, a nie zgodę na ich implementację. Po wyborze i zatwierdzeniu zakresu konkretnego zadania użyj `superpowers:executing-plans` albo, jeśli użytkownik wybierze delegowanie, `superpowers:subagent-driven-development`. Kroki mają pola do odznaczania; nie zaczynaj wszystkich ośmiu zadań jednocześnie.

**Cel:** wygodniejsze przygotowanie transmisji oraz bardziej przewidywalne i angażujące sterowanie grą przez widzów.

**Architektura:** zachowujemy lokalny rdzeń Python, adaptery czterech platform, FastAPI na loopback, React i powłokę desktopową. Logika dopasowania, arbitrażu komend i wykonywania klawiszy pozostaje w rdzeniu; panel i nakładka prezentują stan, nie ustalają wyniku gry.

**Technologie:** Python, Pydantic, asyncio, PyAutoGUI, PySide6/AppKit, FastAPI, React i TypeScript; testy pytest oraz Vitest. Nowe zależności systemowe dobieramy dopiero po próbie technicznej obsługi fokusu i skrótów.

**Specyfikacja:** sekcje „Opis i zakres” oraz „Reguły” każdego zadania w tym dokumencie są jego proponowaną specyfikacją. Parametry liczbowe poniżej to propozycje do zatwierdzenia, nie opis obecnej aplikacji. Stan odniesienia: commit `3aabd20`, aplikacja 0.8, 2026-09-28.

## Stan obecny i granice dokumentu

- Działają źródła TikTok, Twitch, YouTube i Kick; aktywne jest jedno źródło naraz. Mapowania są wspólne, kanały i filtry oddzielne.
- Komentarz jest dopasowywany w całości po `strip().lower()`. Jeden klawisz to naciśnięcie, kilka to kombinacja, nie sekwencja.
- `Matcher` ma wspólny cooldown 0,3 s na trigger. `KeyboardExecutor` już ogranicza kolejkę do 100 oczekujących akcji i odrzuca akcje starsze niż 1 s.
- Listener pracuje na konfiguracji ze Startu, a numer generacji odcina zdarzenia wcześniejszych sesji. Nieoczekiwane rozłączenie wyłącza klawisze.
- Panel ma zapis z kontrolą rewizji, historię zdarzeń, presety oraz PL/EN. Nie należy budować tych mechanizmów od nowa.
- Obecne API panelu wymaga sesji i stosuje ochronę host/origin/CSRF. Nakładka nie może osłabić tych zabezpieczeń.
- Dokument nie wdraża funkcji ani nie potwierdza kompatybilności konkretnych gier, systemowych skrótów lub źródła przeglądarkowego OBS.

## Wspólne wymagania

1. Dane zapisujemy w katalogu wyznaczonym przez aplikację, nigdy w repozytoryjnym `config.json`. Migracje muszą zachować oryginał i stare mapowania.
2. Do czasu osobnego projektu zmian na żywo obowiązuje Stop → zapis/wybór konfiguracji → Start. Próba przełączenia profilu w czasie łączenia, pracy albo zatrzymywania zwraca konflikt.
3. `generation` identyfikuje sesję nasłuchu. Osobny `output_epoch` unieważnia oczekujące i wykonywane akcje po pauzie, zmianie fokusu lub sterującego, bez udawania nowego połączenia z czatem.
4. Zegar do limitów i terminów jest monotoniczny. Testy wstrzykują zegar, losowanie, klienta czatu, detekcję fokusu i atrapę klawiatury.
5. Zmiany UI obejmują PL/EN, klawiaturę, stany ładowania, błędy zapisu i konflikt dwóch otwartych kart.
6. Nie ma automatycznego przejęcia fokusu, wysyłania wiadomości do czatu ani sterowania z internetu. Nie dodajemy kont w chmurze.
7. Wersja aplikacji pochodzi wyłącznie z `VERSION`; wersja schematu konfiguracji i format eksportu są odrębne. Numery przyszłych wydań ustalamy przy realizacji, nie rezerwujemy ich w roadmapie.
8. Każde zakończone wdrożenie aktualizuje kontekst projektu, przechodzi właściwe testy i build, otrzymuje opis wydania, commit, rosnący tag `v<major>.<minor>` i push zgodnie z `AGENTS.md`.

## Kolejność i zależności

| Etap | Zadanie | Zależności | Względna złożoność | Rezultat |
| --- | --- | --- | --- | --- |
| A | 1. Profile gier | brak | średnia | konfiguracje dopasowane do gier |
| B | 7. Symulator czatu | 1 zalecane | średnia | sprawdzanie reguł bez transmisji |
| C | 5. Limity i kolejka | 1 zalecane | średnia | kontrola obciążenia i spamowania |
| D | 6. Fokus i awaryjny STOP | próba natywna macOS/Windows | duża | kontrolowana pauza wyjścia |
| E | 2. Przytrzymywanie i sekwencje | 5 i 6 | duża | bogatsze sterowanie |
| F | 3. Głosowanie | 5; korzysta z 6 | średnia/duża | wspólne decyzje czatu |
| G | 4. Nakładka | podstawowa niezależna od 3; głosowanie wymaga 3 | średnia/duża | widoczna informacja dla widzów |
| H | 8. Widz przy sterach | 5 i 6; 4 zalecane | średnia/duża | kolejka uczestników i tury |

Złożoność jest porównawcza, nie jest estymacją dni. Pierwszy sensowny pakiet to profile i symulator. Następnie limity oraz zabezpieczenia, później nowe mechaniki sterowania. Nakładkę można dostarczyć wcześniej w wariancie podstawowym. Każde zadanie ma osobny odbiór; nie wymaga ukończenia całej roadmapy.

## Punkty szczególnej weryfikacji

- Stary plik konfiguracji, nieznana wersja importu i nieudany zapis nie mogą utracić danych — zadanie 1.
- STOP albo utrata fokusu pomiędzy `keyDown` i `keyUp` nie mogą pozostawić klawisza logicznie wciśniętego — zadania 6 i 2.
- Spam, manipulacja zegarem ściennym i zdarzenia starej generacji nie mogą zmienić wyniku bieżącej rundy — zadania 5 i 3.
- Nick lub komentarz zawierający HTML oraz adres nakładki nie mogą dawać dostępu do sterowania — zadanie 4.
- Zakończenie tury równocześnie z komentarzem nie może przekazać starej akcji nowemu sterującemu — zadanie 8.

## Zadanie 1. Profile gier

**Stan: wdrożone w v0.12**, wraz z presetem NumPad 2468 i katalogiem szablonów. Szczegóły realizacji i sprawdzeń: [plan wykonawczy](2026-09-28-profiles-implementation.md). Poniższy opis zachowuje założenia projektu; kolejne zadania nadal nie są wdrożone.

### Opis i zakres

Użytkownik tworzy profil, np. „Hugo” lub „Wyścigi”, i wybiera go przed Startem. Profil przechowuje mapowania, filtry widzów dla poszczególnych platform oraz późniejsze ustawienia trybu i limitów. Konta, klucze API, kanały transmisji i język pozostają ustawieniami aplikacji. Profil można duplikować, przemianować, eksportować i importować.

### Reguły

- Nowa instalacja ma profil „Domyślny”. Migracja v4 przenosi dotychczasowe mapowania i filtry dokładnie do tego profilu; pierwsza migracja profili podnosi schemat do v5.
- Profil ma UUID, nazwę długości 1–80 znaków po przycięciu oraz własną rewizję danych wynikającą z zapisu całej konfiguracji. Nazwy nie muszą być unikalne; UI rozróżnia rekordy po UUID.
- Musi pozostać co najmniej jeden profil. Usunięcie aktywnego wymaga wskazania innego, a usunięcie ostatniego jest niedozwolone.
- Import tworzy nowy profil i nowe identyfikatory mapowań, pokazuje podgląd oraz nie nadpisuje bieżącego profilu. Maksymalny plik: 1 MiB i 500 mapowań.
- Eksport `format_version: 1` jest budowany z jawnej listy pól. Pomija kanały, filtry z nickami/ID, konta, klucze i ustawienia lokalnego procesu docelowego; podgląd wyjaśnia pominięcia. Mapowania i neutralne parametry gry pozostają przenośne.
- Nowsza, nieobsługiwana wersja importu jest odrzucana bez zapisu. Powrót do aplikacji sprzed migracji wymaga odtworzenia backupu; nie obiecujemy automatycznego downgrade.

### Pliki i interfejsy

- Zmienić `src/core/models.py`, `src/core/config_store.py`, `src/core/listener_service.py`, `src/api/app.py`, `frontend/src/api/types.ts`, `frontend/src/state/configController.ts`, `frontend/src/App.tsx`.
- Dodać `src/core/profiles.py`, `src/api/profiles.py`, `frontend/src/components/ProfileManager.tsx`.
- Proponowany kontrakt: `resolve_profile(config: AppConfig) -> RuntimeProfile`, gdzie `RuntimeProfile` jest niezmiennym snapshotem mapowań, filtrów i parametrów wybranego profilu.
- `export_profile(profile: GameProfile) -> dict` i `import_profile(payload: dict) -> GameProfile` realizują oddzielny format wymiany. API mutujące korzysta z rewizji całej konfiguracji i istniejącej ochrony sesji.

### Plan

- [ ] 1. Dodać `tests/core/test_profiles.py`: migracja zachowuje wszystkie mapowania/filtry, konto i kanał; eksport nie zawiera tych danych; nowszy format i plik ponad limit są odrzucane. Uruchomić testy i potwierdzić brak implementacji.
- [ ] 2. Wdrożyć modele profilu, migrację z backupem i resolver snapshotu w rdzeniu. Zachować migracje v1–v4 jako drogę do aktualnego formatu.
- [ ] 3. Wdrożyć CRUD oraz import/eksport z kontrolą rewizji. W `tests/api/test_profiles.py` sprawdzić konflikt dwóch kart, blokadę zmiany podczas nasłuchu i brak zmiany danych po błędzie zapisu.
- [ ] 4. Dodać wybór profilu, duplikowanie i podgląd importu. W `ProfileManager.test.tsx` sprawdzić klawiaturę, ostatni profil, błędy importu i oznaczenie aktywnego profilu.
- [ ] 5. Uruchomić `python -m pytest tests/core/test_profiles.py tests/core/test_config_store.py tests/api/test_profiles.py -q` oraz `npm --prefix frontend test -- --run`. Wynik: wszystkie testy zielone; restart odtwarza wybór.
- [ ] 6. Wykonać wspólny odbiór i wydanie opisane na końcu dokumentu.

**Kryterium odbioru:** dwa profile wywołują różne mapowania po Stop → wybór → Start; eksport/import przenosi ustawienia gry bez danych konta i bez utraty dotychczasowej konfiguracji.

**Poza zakresem:** biblioteka społecznościowa, synchronizacja w chmurze i automatyczne rozpoznawanie gry.

## Zadanie 2. Przytrzymywanie klawiszy i sekwencje

### Opis i zakres

Mapowanie może wykonać naciśnięcie, kombinację, przytrzymanie albo sekwencję tych czynności z pauzami. Przykład: przytrzymaj `w` przez 500 ms, odczekaj 100 ms, naciśnij `space`. Edytor ma czytelną listę kroków; nie wymaga pisania skryptów.

### Reguły

- Typy kroków: `press(keys)`, `hold(keys, duration_ms)` i `wait(duration_ms)`. Wiele klawiszy w `press` nadal oznacza kombinację. Jeden krok `hold` może trzymać kilka klawiszy jednocześnie.
- Od 1 do 20 kroków; hold 50–3000 ms, wait 10–3000 ms; suma zadeklarowanych hold/wait maksymalnie 10 s. To limit czasów zadeklarowanych, nie gwarancja czasu rzeczywistego na obciążonym systemie.
- Jedno wyjście klawiatury wykonuje jedną sekwencję naraz. Nie ma nakładania makr, pętli, shell commands ani dowolnego kodu.
- STOP, rozłączenie, zmiana `output_epoch` lub błąd przerywają pozostałe kroki, opróżniają kolejkę i podejmują zwolnienie wszystkich klawiszy naciśniętych przez aplikację w `finally`.
- System może odmówić wysłania `keyUp`; wtedy aplikacja utrzymuje wyjście wyłączone i pokazuje błąd, zamiast twierdzić, że klawisze zwolniono. Twarde zabicie procesu nie daje gwarancji wykonania sprzątania.
- Stare `keys` migrują do jednego kroku `press` bez zmiany zachowania. Eksport profilu otrzymuje nową wersję formatu, jeśli poprzedni importer nie rozumie akcji.

### Pliki i interfejsy

- Dodać `src/core/actions.py` i `frontend/src/components/ActionEditor.tsx`.
- Zmienić `src/core/models.py`, `src/core/keyboard.py`, `src/adapters/pyautogui_keyboard.py`, `src/core/listener_service.py`, edytor mapowań, typy API i migracje.
- `ActionStep` jest sumą modeli `PressStep`, `HoldStep`, `WaitStep`; `ActionDefinition.steps` to ich niezmienna krotka.
- Rozszerzyć `KeyAction` o definicję akcji, `mapping_id`, `actor_id`, `output_epoch` i `expires_at`. Adapter udostępnia `press(keys)`, `key_down(key)` i `key_up(key)`; executor kontroluje anulowanie i zbiór przytrzymanych klawiszy.

### Plan

- [ ] 1. W `tests/core/test_actions.py` zapisać oczekiwane limity i migrację; w `tests/core/test_keyboard.py` sekwencję `down(w) → up(w) → press(space)` z atrapą zegara i portu. Potwierdzić niepowodzenie przed wdrożeniem.
- [ ] 2. Wdrożyć walidowane modele i migrację; odrzucać nieobsługiwane klawisze i przekroczenia limitów przed uruchomieniem.
- [ ] 3. Rozszerzyć executor o przerywalne oczekiwanie i zwalnianie klawiszy. Testować STOP podczas hold/wait, błąd drugiego `keyDown`, błąd `keyUp`, zmianę fokusu i starą epokę.
- [ ] 4. Dodać edytor kroków, zmianę kolejności i podsumowanie czasu. Test `ActionEditor.test.tsx` ma sprawdzać zachowanie szkicu po błędzie i brak automatycznego wysłania klawiszy.
- [ ] 5. Uruchomić `python -m pytest tests/core/test_actions.py tests/core/test_keyboard.py tests/core/test_listener_races.py -q` i frontend. Po zielonych testach sprawdzić rzeczywiste zwalnianie klawiszy w izolowanej aplikacji testowej na obu systemach.
- [ ] 6. Wykonać wspólny odbiór i wydanie.

**Kryterium odbioru:** prawidłowa kolejność kroków i anulowanie bez następnych kroków; błąd sprzątania jest jawny i blokuje dalsze sterowanie. Wyniki natywne opisane oddzielnie od testów atrap.

**Poza zakresem:** mysz, kontrolery, nagrywanie makr i równoległe sekwencje.

## Zadanie 3. Tryb głosowania

### Opis i zakres

W trybie „Głosowanie” wiadomości stają się głosami. Po zakończeniu okna rdzeń wysyła jedną zwycięską akcję do tej samej kolejki co tryb bezpośredni. Podgląd pokazuje licznik, wyniki i rozstrzygnięcie. Tryby bezpośredni, głosowanie i widz przy sterach są wzajemnie wykluczające.

### Reguły

- Okno domyślnie 2000 ms, zakres 500–10000 ms. Jedna osoba ma jeden ważny głos w rundzie; kolejny poprawny komentarz zmienia jej wybór, nie zwiększa liczby głosujących.
- Tożsamość bazuje na identyfikatorze platformy używanym przez adapter i jej obecnych regułach normalizacji, nigdy na samej nazwie wyświetlanej.
- Filtr widzów działa przed liczeniem. Limit per widz ogranicza częstotliwość zmiany głosu. Wspólny cooldown akcji nie może odrzucać głosów różnych osób; działa dopiero przy wysłaniu wyniku.
- Remis oznacza brak akcji. Pusta runda również nie wykonuje ruchu. Panel wyjaśnia oba przypadki.
- Okno jest półotwarte `[start, deadline)`. Głos dokładnie w terminie końca trafia do następnej rundy. Pauza anuluje rundę; wznowienie zaczyna nową, bez przenoszenia głosów.
- Maksymalnie 10000 unikalnych głosujących na rundę; nadmiar nowych osób jest odrzucany z licznikiem, a obecni mogą zmieniać głos. Wynik nie rośnie bez ograniczeń w pamięci.

### Pliki i interfejsy

- Dodać `src/core/voting.py` i `frontend/src/components/VotingPanel.tsx`; zmienić listener, modele, zdarzenia i ustawienia profilu.
- `VotingEngine.cast(actor_id: str, mapping_id: str, now: float) -> VoteResult` aktualizuje bieżącą rundę; `finish(now: float) -> RoundResult | None` zwraca wynik dokładnie raz.
- `RoundResult` zawiera `round_id`, `generation`, `output_epoch`, `winner_mapping_id | None`, liczby głosów oraz powód `winner`, `tie` lub `empty`. Listener wykonuje wynik, silnik głosowania nie dotyka klawiatury.

### Plan

- [ ] 1. Dodać `tests/core/test_voting.py`: zmiana głosu nie zwiększa liczby uczestników, remis/pustka nie wybierają akcji, termin graniczny trafia do nowej rundy. Potwierdzić niepowodzenie testów.
- [ ] 2. Wdrożyć silnik z wstrzykiwanym zegarem, limitem uczestników i idempotentnym zamknięciem rundy.
- [ ] 3. Podłączyć arbitraż po dopasowaniu, przed wysłaniem akcji. Dodać testy spamu, starej generacji, pauzy tuż przed wynikiem oraz braku wpływu zegara ściennego w `tests/core/test_voting_listener.py`.
- [ ] 4. Dodać panel wyników i publikację snapshotu rundy. UI odlicza względem przekazanego czasu pozostałego; autorytatywny termin i wynik są w backendzie.
- [ ] 5. Uruchomić `python -m pytest tests/core/test_voting.py tests/core/test_voting_listener.py -q` i testy frontend. Scenariusz z 10000 uczestników musi zakończyć się jednym wynikiem i ograniczonym stanem.
- [ ] 6. Wykonać wspólny odbiór i wydanie.

**Kryterium odbioru:** ten sam uporządkowany zestaw wiadomości i czasów daje ten sam wynik; żadna runda nie wysyła dwóch akcji.

**Poza zakresem:** ważenie płatnych głosów, automatyczne wykrywanie wielu kont jednej osoby i równoczesne głosowanie z kilku platform.

## Zadanie 4. Nakładka do transmisji

### Opis i zakres

Oddzielny, przezroczysty widok do źródła przeglądarkowego OBS pokazuje dostępne komendy, ostatnią faktycznie wykonaną akcję, opcjonalny nick autora i stan pauzy. Po zadaniu 3 dochodzą wyniki głosowania; po zadaniu 8 osoba przy sterach i czas tury. Panel operatora pozwala wybrać widoczne elementy, rozmiar tekstu i kolor akcentu.

### Reguły

- Wersja podstawowa nie zależy od głosowania. Nie pokazuje całej konfiguracji, surowego czatu, tokenów, filtrów widzów ani prywatnych błędów integracji.
- Nick autora jest domyślnie ukryty; włączenie jest świadomym ustawieniem. Treści są renderowane jako tekst, nigdy przez HTML z komentarza.
- Nakładka działa na loopback i ma osobne, losowe uprawnienie wyłącznie do odczytu. Nie używa tokenu uruchamiającego panel ani jego cookie jako sposobu autoryzacji OBS.
- Propozycja URL: `/overlay#token=...`; fragment nie trafia do logów HTTP. Klient uwierzytelnia osobny WebSocket pierwszą wiadomością w ciągu 5 s. Ten kanał przyjmuje wyłącznie uwierzytelnienie i heartbeat, nigdy komendy sterujące.
- Token można unieważnić i wygenerować ponownie; ma przetrwać restart w oddzielnym pliku danych o ograniczonych uprawnieniach. Nie trafia do eksportu profilu ani diagnostyki. Nie wyłączamy sprawdzania host/origin w istniejącym API.
- Po ponownym połączeniu klient dostaje pełny publiczny snapshot. „Wykonana akcja” pochodzi z potwierdzenia executora, nie z samego przyjęcia komentarza do kolejki.
- Pierwszy etap musi sprawdzić zachowanie źródła przeglądarkowego OBS, tokenu i zmiennego portu backendu. Jeśli adres nie może być trwały, dodać dedykowany port loopback wyłącznie dla nakładki: domyślnie 18765, konfigurowalny; zajęcie portu zgłasza błąd, nie zmienia go po cichu. Port panelu pozostaje bez zmian.

### Pliki i interfejsy

- Dodać `src/core/overlay.py`, `src/api/overlay.py`, `frontend/src/overlay/Overlay.tsx` i `frontend/src/components/OverlaySettings.tsx`.
- Zmienić routing frontendu, backend desktopowy w razie potrzeby osobnego portu, zdarzenia akcji i schemat ustawień prezentacji.
- `public_snapshot(state) -> OverlaySnapshot` jawnie wybiera dozwolone pola; `OverlaySnapshot` ma `schema_version`, `sequence`, `mode`, `paused`, `commands`, `last_action` i opcjonalne `voting`/`turn`.
- Jeśli podstawowa nakładka powstaje przed zadaniem 2, dodać przekazywanie `mapping_id` i `actor_id` przez `KeyAction` już tutaj; nie zgadywać autora na podstawie ostatniego komentarza.

### Plan

- [ ] 1. Wykonać ograniczoną próbę w OBS na macOS i Windows: przezroczystość, fragment URL, ponowne połączenie i trwałość adresu po restarcie. Zapisać wynik przed wyborem wariantu portu.
- [ ] 2. Dodać `tests/api/test_overlay.py`: token nakładki nie autoryzuje Start/Stop ani odczytu konfiguracji; brak tokenu i zły origin są odrzucane; obrócony token traci ważność. Potwierdzić niepowodzenie testów.
- [ ] 3. Wdrożyć projekcję stanu, osobne uwierzytelnienie odczytu i pełny snapshot po reconnect. Testować zerwanie połączenia wolnego klienta bez blokowania rdzenia.
- [ ] 4. Dodać widok i ustawienia. W `frontend/src/overlay/Overlay.test.tsx` sprawdzić tekst `<script>`, ukryty nick, brak głosowania, pauzę i dane ostatniej wykonanej akcji.
- [ ] 5. Uruchomić `python -m pytest tests/api/test_overlay.py tests/api/test_session.py -q` oraz frontend. Powtórzyć odbiór w OBS po buildzie, w tym restart aplikacji i unieważnienie adresu.
- [ ] 6. Wykonać wspólny odbiór i wydanie z instrukcją dodania źródła OBS.

**Kryterium odbioru:** nakładka odtwarza stan po restarcie i nie daje uprawnień panelu; działa w rzeczywistym źródle OBS, a nie tylko w zwykłej przeglądarce.

**Poza zakresem:** sterowanie OBS, scenami i transmisją; dostęp z innego komputera oraz własny edytor CSS/HTML.

## Zadanie 5. Kontrola spamu i kolejki

### Opis i zakres

Rozszerzamy istniejące zabezpieczenia o ustawienia profilu i informację, dlaczego wiadomość nie wywołała ruchu. Użytkownik ustawia cooldown akcji, limit na widza, pojemność kolejki i ważność oczekujących poleceń. Panel pokazuje liczniki odrzuceń zamiast zasypywać log osobnym wpisem za każdą wiadomość.

### Reguły

- Wartości migracyjne zachowują obecne zachowanie: cooldown akcji 300 ms, cooldown widza 0 ms, kolejka 100, ważność 1000 ms.
- Proponowane zakresy: cooldown akcji/widza 0–60000 ms, kolejka 1–100, ważność 100–5000 ms. Pojemność liczy oczekujące akcje, nie aktualnie wykonywaną.
- Pełna kolejka odrzuca nową akcję; nie przerywa wykonania i nie nadpisuje starszych. Wiek sprawdzamy przed rozpoczęciem wykonania, nie po ukończeniu hold.
- Odrzucona z powodu pełnej kolejki akcja nie zużywa cooldownu wykonania. W trybie bezpośrednim cooldown zużywamy po przyjęciu do kolejki, w głosowaniu po przyjęciu wyniku.
- Rozdzielić dopasowanie od limitowania. Powody decyzji: `user_filtered`, `no_mapping`, `user_cooldown`, `action_cooldown`, `queue_full`, `expired`, `output_disabled`, `stale_epoch`.
- Stan per widz: TTL 120 s i maksymalnie 10000 wpisów LRU. To ograniczenie pamięci, nie ochrona przed wieloma kontami. Agregaty do UI najwyżej raz na sekundę.

### Pliki i interfejsy

- Dodać `src/core/rate_limits.py`, `frontend/src/components/ControlLimits.tsx`; zmienić matcher, executor, listener i modele profilu.
- `Matcher.resolve(user_id: str, comment: str) -> MatchDecision` zwraca dopasowanie/powód bez zmiany cooldownu; `MatchDecision` zawiera `mapping_id`, znormalizowane `actor_id` i `reason`.
- `RateLimiter.check(actor_id: str, mapping_id: str, now: float) -> LimitDecision` jest sprawdzeniem; `commit(actor_id: str, mapping_id: str, now: float) -> None` zapisuje przyjęcie. Check → submit → commit wykonuje jeden właściciel w pętli listenera.
- Do `KeyAction` dodać termin `expires_at`; w zadaniu 2 rozszerzyć ten sam obiekt, bez drugiej niezależnej kolejki.

### Plan

- [ ] 1. Dodać `tests/core/test_rate_limits.py`: domyślne 300 ms, osobny widz, granica czasu, brak zużycia po odmowie, TTL/LRU. Potwierdzić niepowodzenie nowych testów.
- [ ] 2. Oddzielić resolver od limitera i zachować dotychczasowe zasady nicków wszystkich czterech platform. Rozszerzyć testy dopasowania o jawne powody decyzji.
- [ ] 3. Parametryzować istniejącą kolejkę. Testować pojemność 1 i 100, dokładny termin ważności (ważne dla `now < expires_at`), spóźniony callback i STOP podczas przepełnienia.
- [ ] 4. Dodać ustawienia profilu i agregaty diagnostyczne. Testować reset liczników nowej sesji i brak wzrostu logu o każde odrzucenie przy dużym ruchu.
- [ ] 5. Uruchomić `python -m pytest tests/core/test_rate_limits.py tests/core/test_matching.py tests/core/test_keyboard.py tests/core/test_listener_races.py -q` i frontend. Test 10000 komentarzy potwierdza limity stanu; nie ustalać arbitralnego czasu wykonania zależnego od CI.
- [ ] 6. Wykonać wspólny odbiór i wydanie.

**Kryterium odbioru:** ustawienia są respektowane, odrzucenia mają jednoznaczny powód, a niezmieniony stary profil zachowuje dotychczasowe wartości limitów.

**Poza zakresem:** wykrywanie botów, bany na platformie i priorytet płatnych wiadomości.

## Zadanie 6. Blokada sterowania poza grą i awaryjny STOP

### Opis i zakres

Użytkownik wybiera uruchomioną aplikację docelową. TikoPlay wysyła wejście tylko, gdy ta aplikacja jest na pierwszym planie. Utrata fokusu pauzuje sterowanie, ale może pozostawić odczyt czatu. Niezależny systemowy skrót zatrzymuje całą sesję, także gdy panel jest schowany.

### Reguły

- Cel identyfikujemy przez tożsamość aplikacji/procesu, nie sam tytuł okna i nie sam PID możliwy do ponownego użycia. Po restarcie gry konieczna jest ponowna weryfikacja jej procesu.
- Kontrola fokusu przed rozpoczęciem akcji i każdym krokiem; dla hold dodatkowo okresowa kontrola z docelowym interwałem 50 ms. To cel pomiarowy, nie gwarancja twardego czasu rzeczywistego.
- Utrata fokusu lub brak możliwości jego odczytu wyłącza wyjście, zwiększa `output_epoch`, czyści kolejkę i wywołuje przerwanie executora. Powrót fokusu sam nie wznawia sterowania.
- Wznowienie inicjowane w panelu przechodzi w stan oczekiwania na fokus gry, potem odlicza 3 s z ciągłym sprawdzaniem fokusu. Dzięki temu kliknięcie panelu nie uniemożliwia wznowienia.
- Skrót proponowany domyślnie: `Ctrl+Alt+Shift+F12`, z możliwością zmiany. Błąd rejestracji lub konflikt jest widoczny; nie prezentujemy nieaktywnego skrótu jako działającego.
- Awaryjny skrót zawsze zatrzymuje, nigdy nie przełącza Stop/Start. Korzysta z tej samej ścieżki zatrzymania co tray i API.
- Wybór celu jest opcjonalny dla zgodności z obecną aplikacją. Włączona ochrona bez działającego adaptera blokuje wyjście. PyAutoGUI nadal wysyła do aktywnego okna; minimalny wyścig pomiędzy odczytem fokusu a zdarzeniem wejścia pozostaje i musi być opisany.

### Pliki i interfejsy

- Dodać `src/core/output_guard.py`, `src/adapters/focus_macos.py`, `src/adapters/focus_windows.py`, `src/desktop/emergency_hotkey.py` i `frontend/src/components/OutputSafety.tsx`.
- Zmienić launcher, listener, stan wyjścia, executor i adapter klawiatury; nie dodawać detekcji systemowej do Reacta.
- `FocusPort.current_target() -> TargetIdentity | None`, `OutputGuard.can_execute(target: TargetIdentity) -> bool`, `EmergencyHotkey.register(chord, callback) -> None` / `unregister() -> None`.
- `TargetIdentity` opisuje tożsamość aplikacji, PID i znacznik uruchomienia procesu. `KeyboardExecutor.cancel(epoch: int) -> None` anuluje wykonanie i kolejkę; mechanizm zwalniania klawiszy jest uzupełniany wraz z hold w zadaniu 2.

### Plan

- [ ] 1. Przeprowadzić próbę natywną macOS/Windows: odczyt procesu pierwszoplanowego, rejestracja skrótu i uprawnienia w spakowanej aplikacji. Zapisać ograniczenia i wybrać bibliotekę/API dopiero na podstawie wyniku.
- [ ] 2. W `tests/core/test_output_guard.py` dodać brak uprawnień, zmianę PID, ponowne użycie PID, utratę fokusu i starą epokę; w `tests/desktop/test_emergency_hotkey.py` konflikt rejestracji. Potwierdzić brak implementacji.
- [ ] 3. Wdrożyć adaptery i strażnika, unieważnianie epoki oraz stan `paused_focus`. Zdarzenia systemowe kierować do właściciela stanu listenera, bez mutowania go z obcego wątku.
- [ ] 4. Podłączyć skrót do istniejącego Stop; wdrożyć oczekiwanie na grę po żądaniu wznowienia. Testować STOP podczas łączenia, odliczania i wielokrotne naciśnięcie skrótu.
- [ ] 5. Uruchomić `python -m pytest tests/core/test_output_guard.py tests/core/test_listener_races.py tests/desktop/test_emergency_hotkey.py -q` i frontend. Po buildzie sprawdzić Alt-Tab, dialog systemowy i utratę uprawnień na obu systemach; zmierzyć opóźnienie wykrycia.
- [ ] 6. Wykonać wspólny odbiór i wydanie z rzeczywistymi wynikami pomiarów.

**Kryterium odbioru:** po wykryciu utraty fokusu nie zaczyna się następna akcja, powrót do gry nie wznawia sam sterowania, a skrót STOP działa z ukrytym panelem.

**Poza zakresem:** wstrzykiwanie wejścia do okna w tle, omijanie anti-cheat i automatyczne przenoszenie fokusu.

## Zadanie 7. Symulator czatu

### Opis i zakres

Oddzielna zakładka pozwala wybrać profil, wpisać identyfikator widza i komentarz oraz zobaczyć wynik dopasowania, filtrów, limitów i planowanej akcji. Scenariusz wielu wiadomości pokazuje zachowanie przy spamie, a później wyniki rund głosowania i tur. Symulator ma własny stan i nigdy nie wysyła klawiszy.

### Reguły

- Symulacja używa kopii zapisanej konfiguracji wraz z numerem rewizji; szkic niezapisany w edytorze nie trafia do niej bez jawnego zapisu.
- Scenariusz to lista `(offset_ms, user_id, comment)` uporządkowana według czasu; przy remisie zachowuje kolejność wejścia. Maksimum 1000 wiadomości, 60 s czasu wirtualnego, komentarz do 2000 znaków.
- Czas jest wirtualny; scenariusz 60 s nie wymaga czekania minuty. Wyjście to lista decyzji i planowanych akcji, nigdy twierdzenie o rzeczywistym naciśnięciu.
- Każde uruchomienie ma własny limiter, kolejkę i silnik trybu. Nie zmienia cooldownów, głosów, historii ani konfiguracji aktywnej sesji LIVE.
- Symulator może działać obok LIVE; nie jest wstrzykiwaniem fikcyjnych komentarzy do prawdziwego listenera. Wynik jasno oznaczony jako „Symulacja — bez klawiszy”.
- Powstając przed zadaniem 5, wydziela resolver i strukturalne decyzje `MatchDecision` zgodne z jego kontraktem. Później podpina ten sam limiter i silniki trybów; nie kopiuje reguł na frontend.

### Pliki i interfejsy

- Dodać `src/core/simulation.py`, `src/api/simulation.py`, `frontend/src/components/ChatSimulator.tsx`.
- Wydzielić wspólne rozpatrywanie komentarza z matchera/listenera tylko w zakresie koniecznym do użycia produkcyjnego i symulacyjnego.
- `SimulationMessage(offset_ms: int, user_id: str, comment: str)` i `simulate(snapshot: ConfigSnapshot, messages: tuple[SimulationMessage, ...]) -> SimulationReport`.
- `SimulationReport` zawiera rewizję konfiguracji, decyzje, czasy wirtualne, identyfikatory mapowań i planowane akcje. Funkcja przyjmuje atrapę wyjścia konstrukcyjnie; nie tworzy adaptera PyAutoGUI.

### Plan

- [ ] 1. Dodać `tests/core/test_simulation.py`: poprawna komenda, obcy widz, brak mapowania, cooldown, identyczne czasy i przekroczenie limitów. Atrapa prawdziwego adaptera ma zgłaszać błąd, jeśli zostanie skonstruowana lub wywołana.
- [ ] 2. Wydzielić wspólne dopasowanie i wdrożyć izolowany wirtualny przebieg. Potwierdzić równoważność decyzji symulatora i produkcyjnej ścieżki z tym samym zegarem.
- [ ] 3. Dodać chroniony endpoint oraz test `tests/api/test_simulation.py`: wymagane uwierzytelnienie, walidacja rozmiaru, brak zmiany rewizji konfiguracji i brak zmiany stanu LIVE.
- [ ] 4. Zbudować panel pojedynczej wiadomości oraz tabelę scenariusza z gotowym przykładem spamu. Test `ChatSimulator.test.tsx` sprawdza powody odrzuceń i oznaczenie trybu bez klawiszy.
- [ ] 5. Uruchomić `python -m pytest tests/core/test_simulation.py tests/api/test_simulation.py -q` i frontend. Przy późniejszym wdrażaniu zadań 2, 3, 5 i 8 rozszerzyć symulator w tym samym zestawie zmian.
- [ ] 6. Wykonać wspólny odbiór i wydanie.

**Kryterium odbioru:** użytkownik wyjaśnia z wyniku, dlaczego komenda zadziałałaby lub została odrzucona; symulacja nie powoduje żadnego wywołania klawiatury ani integracji sieciowej.

**Poza zakresem:** nagrywanie całych rzeczywistych transmisji i automatyczne testowanie gry.

## Zadanie 8. Widz przy sterach

### Opis i zakres

Widz zgłasza się komendą `!gram`. Operator rozpoczyna turę osoby z kolejki albo losuje uczestnika. Tylko ta osoba może sterować przez określony czas; po zakończeniu następuje przekazanie kontroli. Panel pokazuje aktywnego gracza, czas i kolejkę, a nakładka może pokazać te same publiczne informacje.

### Reguły

- Domyślna tura 45 s, zakres 15–180 s. Tryb wyboru FIFO albo losowanie spośród zapisanych; generator losowy wstrzykiwany w testach.
- `!gram` i `!rezygnuje` są konfigurowalnymi komendami administrującymi uczestnictwem. Walidator zabrania kolizji z triggerami mapowań.
- Jedno miejsce na tożsamość widza, limit 1000 oczekujących. Filtr dozwolonych widzów działa również przy zapisach; spam nie zwiększa szansy w losowaniu.
- Operator może zakończyć turę, usunąć osobę z kolejki i zablokować jej uczestnictwo do końca sesji. Blokada lokalna nie jest banem na platformie.
- Zmiana sterującego zwiększa `output_epoch`, anuluje niedokończoną akcję i kolejkę poprzednika. Dopiero potwierdzenie zakończenia sprzątania pozwala rozpocząć odliczanie następnej osoby.
- Koniec tury jest nadrzędny wobec komendy z tym samym czasem: stary uczestnik nie dostaje dodatkowego ruchu. Przy pauzie fokusu licznik tury zatrzymuje się; przy Stop lub rozłączeniu sesja uczestników jest czyszczona.
- Brak uczestników oznacza brak sterowania, nie powrót do „wszyscy mogą”. Brak aktywności widza nie jest uznawany za jego rozłączenie; operator może go pominąć.
- Wariant drużynowy jest osobnym rozszerzeniem po odbiorze MVP, nie częścią pierwszego wdrożenia.

### Pliki i interfejsy

- Dodać `src/core/turns.py`, `src/api/turns.py`, `frontend/src/components/TurnPanel.tsx`; zmienić arbitraż w listenerze i projekcję nakładki.
- `TurnManager.join(actor_id: str) -> JoinResult`, `leave(actor_id: str) -> None`, `next_turn(now: float) -> TurnState`, `can_control(actor_id: str, now: float) -> bool`, `pause(now: float) -> None`, `resume(now: float) -> None`.
- `TurnState` zawiera `turn_id`, `actor_id | None`, `remaining_ms`, `paused` i liczbę oczekujących. Listener pozostaje właścicielem epoki i anulowania klawiatury.

### Plan

- [ ] 1. Dodać `tests/core/test_turns.py`: duplikat zapisu, pełna kolejka, FIFO, kontrolowane losowanie, kolizja komend, blokada i filtr widzów. Potwierdzić niepowodzenie testów.
- [ ] 2. Wdrożyć manager tur i zapisy przez komentarze, bez zależności od klawiatury i API platformy.
- [ ] 3. W `tests/core/test_turns_listener.py` odtworzyć koniec tury równocześnie z komentarzem, trwające hold, pauzę fokusu, pustą kolejkę i rozłączenie. Podłączyć anulowanie epoki i czekanie na zwolnienie wyjścia.
- [ ] 4. Dodać chronione akcje operatora, panel i opcjonalną projekcję nakładki. W `tests/api/test_turns.py` sprawdzić wymaganą sesję oraz odrzucenie działania na starym `turn_id` kodem 409.
- [ ] 5. Rozszerzyć symulator o zapisy i tury; uruchomić `python -m pytest tests/core/test_turns.py tests/core/test_turns_listener.py tests/api/test_turns.py -q` oraz frontend. Użyć deterministycznego scenariusza trzech osób i dwóch przekazań kontroli.
- [ ] 6. Wykonać wspólny odbiór i wydanie.

**Kryterium odbioru:** w danym momencie steruje najwyżej jedna uprawniona osoba; żadne oczekujące polecenie poprzednika nie przechodzi do nowej tury.

### Późniejszy wariant: dwie drużyny

Oddzielny projekt wymaga ustalenia zapisów do drużyn, balansu liczebności i konfliktów akcji. Proponowany pierwszy wariant: dwie rozłączne grupy mapowań, jedna kolejka wyjściowa, rotacyjna obsługa przy jednoczesnym napływie. Przed realizacją zaprojektować testy sprawiedliwości i dokładne zasady zwycięstwa; nie łączyć tego milcząco z MVP pojedynczego sterującego.

## Wspólny odbiór każdego wdrożenia

- [ ] Zweryfikować `git status` i `git diff`, wybrać jeden zatwierdzony zakres i zachować cudze zmiany. W razie zmiany kodu od czasu roadmapy dopasować plan do aktualnego stanu.
- [ ] Uruchomić wskazane testy jednostkowe/API i UI. Następnie pełne `python -m pytest -q`, `npm --prefix frontend test -- --run` oraz `npm --prefix frontend run build`; brak błędów jest warunkiem wydania.
- [ ] Sprawdzić migrację na tymczasowej kopii starej konfiguracji, restart oraz dwa równoległe panele. Użyć atrap czatu i klawiatury poza jawnym odbiorem natywnym.
- [ ] Sprawdzić PL/EN i stany błędów. Udokumentować testy rzeczywiste osobno od symulowanych; nie przedstawiać atrap jako potwierdzenia działania platform LIVE.
- [ ] Uaktualnić `docs/PROJECT_CONTEXT.md`, dobrać `VERSION` do faktycznie dostarczonego zakresu i napisać `releases/v<major>.<minor>.md`. Niewdrożone punkty roadmapy nadal pozostają nieodznaczone.
- [ ] Uruchomić walidator `python release_support.py v<major>.<minor>` i build macOS `bash build-macos.sh`; Windows budować na Windows przez `build-windows.bat`. Zweryfikować numer w UI i gotowej paczce.
- [ ] Commit obejmuje tylko wykonane zadanie. Wypchnąć commit i unikalny rosnący tag; sprawdzić wynik workflow wydania. Linkować wyłącznie nową, istniejącą paczkę; błąd builda zgłaszać wprost.

## Decyzje przed rozpoczęciem implementacji

Użytkownik wybiera pierwsze zadanie i zatwierdza jego reguły, w tym proponowane limity. Rekomendowany start: zadanie 1, potem 7. Dla fokusu i nakładki najpierw zatwierdzić zakres próby natywnej; jej wynik może zmienić dobór adaptera lub portu, ale nie może osłabić wymagań bezpieczeństwa wyjścia i izolacji API.

Ten dokument jest kompletną propozycją kolejnych prac. Zapisanie go nie oznacza uruchomienia implementacji, rezerwacji numerów przyszłych wersji ani wykonania któregokolwiek punktu odbioru.
