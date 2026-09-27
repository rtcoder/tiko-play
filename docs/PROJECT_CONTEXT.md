# TikoPlay — kontekst techniczny

## Wielu dozwolonych użytkowników

Pole „Dozwoleni użytkownicy” obsługuje nicki po przecinku, średniku albo w osobnych wierszach, opcjonalnie z `@`. Puste pole (również same białe znaki) dopuszcza wszystkich; same separatory/znaki `@` są odrzucane. Zachowano tekstowe pole `target_user` w konfiguracji v2, więc pojedynczy wcześniej zapisany nick działa bez migracji. Matcher przygotowuje zbiór nicków, zachowuje dokładne dopasowanie z rozróżnianiem wielkości liter i wspólny cooldown 0,3 s na akcję. Zmiana listy w czasie nasłuchu, tak jak pozostałe ustawienia, wymaga Stop → Start.

## Otwieranie panelu

Każde jawne żądanie otwarcia panelu (kliknięcie traya, „Otwórz panel”, kolejne uruchomienie aplikacji) otwiera nową kartę domyślnej przeglądarki przez `webbrowser.open_new_tab`. Na życzenie użytkownika nie wykrywamy ani nie przywołujemy istniejących kart i nie łączymy równoległych żądań otwarcia.

## Awaria po kolejnych kliknięciach traya (macOS 27)

Raporty `TikoPlay-2026-09-27-114548.ips` i `TikoPlay-2026-09-27-114938.ips` potwierdziły SIGABRT w `libqcocoa.dylib` → `NSEvent.clickCount` podczas natywnego śledzenia menu (Qt 6.11.2, macOS 27.0). To ścieżka opisana w [QTBUG-147449](https://qt-project.atlassian.net/browse/QTBUG-147449). Na macOS `TrayController` nie przypina już QMenu przez `setContextMenu`; lewy klik otwiera panel, prawy pokazuje QMenu przez `popup`. Windows zachowuje natywne przypięte menu. Usunięto otwieranie przeglądarki na każde `ApplicationActivate`; jawne akcje traya i IPC kolejnego uruchomienia nadal otwierają panel. Test regresji sprawdza 20 aktywacji, osobne menu i jawne zakończenie; 46 testów przeszło. Paczka przebudowana. Fizyczne kliknięcia wymagają potwierdzenia użytkownika — narzędzie UI nie uzyskuje dostępu do aplikacji działającej wyłącznie w trayu.

## Ikona traya macOS

`src/desktop/tray_icon.py` tworzy przezroczysty, monochromatyczny kontur wielkiego, pochylonego „T”, zgodny ze znakiem głównej ikony w rozmiarach 18/36/54 px. `QIcon.setIsMask(True)` przekazuje macOS dobór białego/czarnego koloru do wyglądu paska menu, również przy zmianach motywu. Pozostałe platformy zachowują `tiko_play.ico`; ikona Docka/aplikacji pozostaje bez zmian.

## Warianty wyglądu panelu

Nagłówek zawiera przełącznik Klasyczny / Glass. Alternatywny styl jest izolowany w `frontend/src/styles-glass.css`, inspirowany dostarczonym przykładem CodePen Aysenur Turk (ZEpxeYm); tło to lokalne gradienty CSS. Przełączenie nie remontuje aplikacji i nie dotyka API ani listenera. Preferencja w localStorage jest przypisana do originu przeglądarki (zmiana portu po ponownym uruchomieniu może ją zresetować). Oba warianty pozostają do wyboru.

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
