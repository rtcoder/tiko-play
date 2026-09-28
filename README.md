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

Konfiguracja v1/v2/v3 jest migrowana do v4 z kopią `config.v1.backup.json` `config.v2.backup.json` lub `config.v3.backup.json`; przy kolizji nazwa dostaje UUID. TikTok pozostaje domyślnym źródłem, a każda platforma zapamiętuje własny kanał i filtr. Mapowania pozostają wspólne. Uszkodzone dane wymagają jawnej naprawy w panelu; oryginał jest zachowany. Nieznana nowsza wersja schematu nie jest nadpisywana. Repozytoryjny `config.json` nie jest wczytywany ani pakowany.

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


## YouTube Live — lokalny odbiór czatu

1. W [Google Cloud](https://console.cloud.google.com/apis/library/youtube.googleapis.com) włącz **YouTube Data API v3** i utwórz klucz API. Ogranicz go do tej usługi. Restrykcja typu HTTP referrer (dla stron WWW) nie pasuje do klienta desktopowego.
2. Wybierz **YouTube Live**, wklej link do trwającej transmisji (`watch?v=…`, `youtu.be/…`, `/live/…`) lub 11-znakowe ID filmu. Sam nick kanału nie wystarcza.
3. W polu **Klucz YouTube Data API** wpisz klucz i kliknij **Zapisz klucz**. Trafia wyłącznie do natywnego magazynu systemu (macOS Keychain / Windows Credential Manager); API panelu zwraca tylko informację o jego obecności. Nie zapisujemy klucza w konfiguracji, logu zdarzeń ani URL żądania. Zmiana/usunięcie klucza wymaga zatrzymania nasłuchu YouTube.
4. Rozpocznij nasłuch. `videos.list` znajduje aktywny czat, a `liveChatMessages.streamList` dostarcza wiadomości przez bezpośrednie połączenie gRPC. Nie uruchamiasz serwera ani tunelu. Projekt Google Cloud musi mieć dostępny limit API.
5. Opcjonalny filtr widzów przyjmuje **ID ich kanałów (`UC…`)**, z rozróżnianiem wielkości liter. Te identyfikatory są widoczne przy komentarzach w panelu aktywności; nazwy wyświetlane nie są unikalne i nie służą do autoryzacji.

Pierwsza paczka historii, starsze wiadomości i duplikaty nie uruchamiają klawiszy. Obsługiwane są zwykłe wiadomości tekstowe; prezenty, Super Chat i inne zdarzenia nie są komendami. Po zakończeniu czatu, utracie połączenia lub wyczerpaniu limitu nasłuch zatrzymuje się z komunikatem — ponowne połączenie wymaga Start.

## Kick — lokalnie, bez serwera i tunelu

Wybierz **Kick**, wpisz login kanału (bez URL) i rozpocznij nasłuch. Aplikacja anonimowo odczytuje publiczne `kick.com/api/v2/channels/LOGIN`, a potem subskrybuje czat przez Pusher WebSocket. Konto, token OAuth, publiczny webhook i serwer pośredniczący nie są potrzebne. To **nieoficjalna integracja**; zmiana wewnętrznego protokołu lub blokada ze strony Kicka może wymagać aktualizacji TikoPlay.

Jeśli automatyczny odczyt kanału zostanie zablokowany, rozwiń **Zaawansowane: ID pokoju czatu**. W swojej przeglądarce otwórz `https://kick.com/api/v2/channels/LOGIN` i przepisz `chatroom.id` (nie ID użytkownika). Pole określa faktycznie odbierany czat i musi odpowiadać wpisanemu kanałowi. Zmiana loginu w panelu czyści ręczne ID. Ten wariant nadal łączy się bezpośrednio z Kickiem i nie gwarantuje działania, jeśli zablokowane jest również połączenie WebSocket.

Filtr widzów Kicka ignoruje wielkość liter. Duplikaty odebrane przez starszą i nowszą wersję protokołu wywołują komendę tylko raz. Po utracie połączenia należy ponownie uruchomić nasłuch.

### Protokół YouTube i testy nowych źródeł

Minimalny schemat odczytu znajduje się w `src/adapters/proto/youtube_chat.proto`, a wygenerowany moduł Python jest częścią repozytorium. Zwykły build aplikacji nie wymaga generowania go ponownie. Po zmianie schematu:

```sh
python -m grpc_tools.protoc -I. --python_out=. src/adapters/proto/youtube_chat.proto
```

Opis sprawdzeń i ograniczeń: [YOUTUBE_KICK_ACCEPTANCE.md](docs/YOUTUBE_KICK_ACCEPTANCE.md).

### Język aplikacji

Przy pierwszym uruchomieniu wybierz **Polski** lub **English**. Domyślnie zaznaczony jest język interfejsu systemu: polski dla `pl`, angielski dla `en` i wszystkich pozostałych języków. Wybór jest zapamiętywany w `preferences.json` w katalogu danych użytkownika. Istniejąca instalacja zapyta raz po aktualizacji. Anulowanie okna kończy uruchomienie bez zapisu.

Język można później zmienić w **Ustawienia → Język / Settings → Language**. Panel i tray aktualizują się bez restartu; komentarze i mapowania pozostają bez zmian.
