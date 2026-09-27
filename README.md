# TikoPlay

Komentarze TikTok LIVE uruchamiają klawisze w aktywnym oknie gry. Aplikacja działa lokalnie w Pythonie, a panel otwiera się w przeglądarce.

## Uruchamianie dla użytkownika

- **Windows:** zainstaluj paczkę, kliknij skrót **TikoPlay** na pulpicie. Program sam uruchamia serwer i panel.
- **macOS:** przenieś **TikoPlay.app** do Aplikacji; uruchom aplikację lub jej alias na pulpicie. Instrukcja aliasu: [instalacja macOS](docs/INSTALL_MACOS.txt).
- Wpisz nick streamera, ustaw mapowania i kliknij **Rozpocznij nasłuch**. Przełącz fokus do gry; opcjonalne odliczanie daje 3 sekundy po połączeniu.
- Zamknięcie karty **nie zatrzymuje nasłuchu**. Ikona w trayu/pasku menu pozwala otworzyć panel, zatrzymać nasłuch lub zakończyć program.
- Ponowne uruchomienie otwiera panel tej samej instancji.

Panel i API są dostępne tylko na `127.0.0.1`. Python/Node.js nie są wymagane u użytkownika z gotową paczką. Internet jest potrzebny do TikToka, nie do wyświetlania panelu.

## Zachowanie

Cały komentarz dopasowany po usunięciu skrajnych spacji i zmianie liter na małe. Jeden klawisz oznacza `press`, kilka — kombinację `hotkey`. Cooldown: 0,3 s na trigger. Filtr komentującego wymaga dokładnego `unique_id` bez @; puste pole dopuszcza wszystkich.

Zmiany konfiguracji zapisują się automatycznie po 500 ms; aktywny listener używa snapshotu ze Startu. Panel informuje o konieczności restartu nasłuchu. Niepełne mapowania pozostają lokalnym szkicem. Konflikt kilku kart nie nadpisuje danych po cichu.

Klawisze trafiają do aktywnego okna. Uprawnienia systemowe i ograniczenia PyAutoGUI nadal obowiązują. Fail-safe PyAutoGUI wyłącza akcje po błędzie. Nie ma automatycznego reconnectu ani autostartu nasłuchu.

## Dane

- macOS: `~/Library/Application Support/TikoPlay/`
- Windows: `%APPDATA%/TikoPlay/`
- Pozostałe systemy (tryb źródłowy): `~/.config/TikoPlay/`

Konfiguracja v1 jest migrowana do v2 z kopią `config.v1.backup.json`. Uszkodzone dane wymagają jawnej naprawy w panelu; oryginał jest zachowany. Nieznana nowsza wersja schematu nie jest nadpisywana. Repozytoryjny `config.json` nie jest wczytywany ani pakowany.

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
