# TikoPlay

Komentarze TikTok LIVE lub wiadomości czatu Twitch uruchamiają klawisze w aktywnym oknie gry. Aplikacja działa lokalnie w Pythonie, a panel otwiera się w przeglądarce.

## Uruchamianie dla użytkownika

- **Windows:** zainstaluj paczkę, kliknij skrót **TikoPlay** na pulpicie. Program sam uruchamia serwer i panel.
- **macOS:** przenieś **TikoPlay.app** do Aplikacji; uruchom aplikację lub jej alias na pulpicie. Instrukcja aliasu: [instalacja macOS](docs/INSTALL_MACOS.txt).
- Wybierz źródło czatu, wpisz login kanału, ustaw mapowania i kliknij **Rozpocznij nasłuch**. Przełącz fokus do gry; opcjonalne odliczanie daje 3 sekundy po połączeniu.
- Zamknięcie karty **nie zatrzymuje nasłuchu**. Ikona w trayu/pasku menu pozwala otworzyć panel, zatrzymać nasłuch lub zakończyć program.
- Ponowne uruchomienie otwiera panel tej samej instancji.

Panel i API są dostępne tylko na `127.0.0.1`. Python/Node.js nie są wymagane u użytkownika z gotową paczką. Internet jest potrzebny do platform czatu, nie do wyświetlania panelu.

## Zachowanie

Cały komentarz dopasowany po usunięciu skrajnych spacji i zmianie liter na małe. Jeden klawisz oznacza `press`, kilka — kombinację `hotkey`. Cooldown: 0,3 s na trigger. Filtr TikToka rozróżnia wielkość liter, Twitcha — nie. Nicki można podać po przecinku, średniku lub w osobnych wierszach, opcjonalnie z @; puste pole dopuszcza wszystkich.

Zmiany konfiguracji zapisują się automatycznie po 500 ms; aktywny listener używa snapshotu ze Startu. Panel informuje o konieczności restartu nasłuchu. Niepełne mapowania pozostają lokalnym szkicem. Konflikt kilku kart nie nadpisuje danych po cichu.

Klawisze trafiają do aktywnego okna. Uprawnienia systemowe i ograniczenia PyAutoGUI nadal obowiązują. Fail-safe PyAutoGUI wyłącza akcje po błędzie. Po nieoczekiwanym zerwaniu połączenia trzeba ponownie kliknąć Start. Kontrolowane przeniesienie sesji EventSub wskazane przez Twitch odbywa się bez nowej subskrypcji. Nie ma autostartu nasłuchu.

## Dane

- macOS: `~/Library/Application Support/TikoPlay/`
- Windows: `%APPDATA%/TikoPlay/`
- Pozostałe systemy (tryb źródłowy): `~/.config/TikoPlay/`

Konfiguracja v1/v2 jest migrowana do v3 z kopią `config.v1.backup.json` lub `config.v2.backup.json`; przy kolizji nazwa dostaje UUID. TikTok pozostaje domyślnym źródłem, a każda platforma zapamiętuje własny kanał i filtr. Mapowania pozostają wspólne. Uszkodzone dane wymagają jawnej naprawy w panelu; oryginał jest zachowany. Nieznana nowsza wersja schematu nie jest nadpisywana. Repozytoryjny `config.json` nie jest wczytywany ani pakowany.

## Development

Python >=3.12, Node.js 22.12+; lokalnie zweryfikowano Python 3.14.7, Node 22.22.3 i macOS arm64. Windows wymaga osobnego odbioru.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
python main.py --data-dir /tmp/tikoplay-dev
```

Na Windows aktywacja: `.venv\Scripts\activate`. Parametr `--data-dir` izoluje dane i blokadę instancji. Bez niego używany jest prawdziwy katalog użytkownika.

```sh
python -m pytest -q
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Testy nie łączą się z TikTokiem i nie wysyłają prawdziwych klawiszy. Test integracyjny uruchamia lokalny HTTP/WebSocket z atrapami integracji.

[Pakowanie](docs/PACKAGING.md) · [Raport odbioru](docs/WEB_UI_ACCEPTANCE.md) · [Architektura](docs/superpowers/specs/2026-09-26-local-web-ui-design.md)

## Twitch

1. W Twitch Developer Console zarejestruj aplikację typu **Public** obsługującą Device Code Flow. Publiczny Client ID identyfikuje aplikację; nie potrzebujesz i nie umieszczaj w TikoPlay client secret.
2. W rozwoju ustaw `TIKOPLAY_TWITCH_CLIENT_ID` przed uruchomieniem. Dla dystrybucji wydawca ustawia publiczną stałą `TWITCH_CLIENT_ID` w `src/twitch_settings.py` przed buildem. Obecna testowa paczka nie zawiera przypisanego Client ID.
3. W panelu wybierz **Twitch**, podaj login kanału i kliknij **Połącz konto Twitch**. Otwórz link aktywacji, zaloguj się na stronie Twitcha i zatwierdź odczyt czatu (`user:read:chat`). Połączone konto i kanał docelowy mogą być różne.
4. Ustaw mapowania i rozpocznij nasłuch. Działa tylko jedna wybrana platforma. Zmiana źródła lub filtra wymaga Stop → Start.

```sh
TIKOPLAY_TWITCH_CLIENT_ID=twoj_publiczny_client_id .venv/bin/python main.py --data-dir /tmp/tikoplay-dev
```

Tokeny pozostają w macOS Keychain lub Windows Credential Manager, poza konfiguracją i panelem. Kod aktywacji nie jest zapisywany w localStorage. Odłączenie konta usuwa lokalną sesję i zatrzymuje nasłuch Twitcha. Brak magazynu systemowego blokuje logowanie Twitcha; nie ma zapisu tokenów jawnym tekstem. Implementacja natywnego magazynu obejmuje macOS i Windows.

Twitch jest obsługiwany przez EventSub WebSocket: bez publicznego serwera, tylko odczyt czatu. Duplikaty są pomijane w ograniczonym cache (10 minut, do 10 000 wpisów); wiadomości Shared Chat pochodzące z innych kanałów nie sterują grą. Nie są obsługiwane Bits, punkty kanału ani wysyłanie wiadomości.

[Raport odbioru Twitcha](docs/TWITCH_ACCEPTANCE.md) rozdziela testy na atrapach od rzeczywistego logowania i odbioru na macOS/Windows.
