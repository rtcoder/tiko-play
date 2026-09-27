# Nasłuch Twitcha — projekt integracji

Status: zakres zaakceptowany w rozmowie; specyfikacja do przeglądu przed planem wykonawczym. Funkcja nie jest jeszcze wdrożona.

## Cel i zakres

Użytkownik wybiera TikTok albo Twitch. Wiadomości z jednego wybranego kanału sterują aktywnym oknem przez istniejące mapowania PyAutoGUI. Użytkownik potwierdził jedną aktywną platformę naraz. Zachowujemy wspólne mapowania, cooldown 0,3 s na trigger, filtr dozwolonych użytkowników i opcjonalne odliczanie 3 s.

Poza zakresem: równoczesne platformy, wiele kanałów, wysyłanie czatu, Bits, subskrypcje, punkty kanału i automatyczne wznowienie sterowania po nieoczekiwanej utracie połączenia.

## Stan zastany i podział odpowiedzialności

Nowa aplikacja działa jako Qt/tray, backend FastAPI na loopback i panel React. Historycznego GUI w `src/views` nie zmieniamy.

- `src/core/models.py`: konfiguracja v3, ustawienia źródeł, aktywne źródło w stanie listenera.
- `src/core/config_store.py`: migracja v1/v2 i atomowy zapis z kopią.
- `src/core/matching.py`, `src/core/users.py`: reguły dopasowania z polityką normalizacji autora zależną od platformy.
- Nowy `src/adapters/chat.py`: kontrakt adaptera i fabryka źródeł.
- `src/adapters/tiktok.py`: zachowanie aktualnej integracji za wspólnym kontraktem.
- Nowe `src/adapters/twitch_auth.py`, `twitch_credentials.py`, `twitch.py`: osobno OAuth, magazyn poświadczeń i transport czatu.
- `src/core/listener_service.py`: wspólny cykl życia, snapshot konfiguracji, błędy i bramka klawiatury.
- Nowy `src/api/twitch.py`: lokalne endpointy autoryzacji; podłączenie w `src/api/app.py`.
- `src/desktop/backend.py`: składanie zależności i zamykanie zasobów.
- Nowy `frontend/src/components/ChatSourceSettings.tsx`: ustawienia platformy i połączenia konta. Aktualizacja typów, klienta API, pulpitu i logów.

## Konfiguracja v3

Schemat zawiera `version: 3`, `platform: "tiktok" | "twitch"`, sekcje `tiktok` i `twitch` oraz dotychczasowe wspólne `mappings`, `show_logs`, `countdown_enabled`.

Każda sekcja platformy przechowuje `channel` i `target_user`. Początkowo oba pola są puste. `platform` domyślnie wynosi `tiktok`. Lista użytkowników zachowuje format tekstowy: przecinki, średniki i nowe linie; puste pole dopuszcza wszystkich. Same separatory są błędem.

Migracja przenosi stare `streamer_id` do `tiktok.channel`, a stare `target_user` do `tiktok.target_user`; usuwa te dwa pola z korzenia. Mapowania i ich ID zostają zachowane, w v1 brakujące ID dostają UUID. Zachowujemy nieznane rozszerzenia danych tak jak obecny model. Walidacja następuje przed zastąpieniem pliku. Kopia zawiera oryginalne bajty i wersję źródłową w nazwie; istniejącej kopii nie nadpisujemy, w razie kolizji tworzymy nową nazwę z UUID. Błąd kopii blokuje migrację. Nowsza nieobsługiwana wersja pozostaje nietknięta.

Konfiguracja nadal trafia wyłącznie do katalogu użytkownika. Repozytoryjny `config.json` nie jest źródłem ustawień. Tokeny i identyfikator klienta OAuth nie należą do konfiguracji mapowań.

## Autoryzacja i poświadczenia

Integracja korzysta z EventSub WebSocket i User Access Token z jedynym zakresem `user:read:chat`. Publiczny klient OAuth używa Device Code Flow. Nie dystrybuujemy `client_secret`, nie uruchamiamy publicznego serwera ani callbacka OAuth.

Publiczny `client_id` pochodzi z rejestracji aplikacji TikoPlay w Twitch Developer Console. W rozwoju dostarczamy go przez `TIKOPLAY_TWITCH_CLIENT_ID`, w wydaniu jako publiczną stałą w module ustawień integracji. Brak ID wyłącza logowanie Twitcha z czytelnym komunikatem, ale nie blokuje uruchomienia TikoPlay ani TikToka. Uzyskanie ID i zgoda właściciela konta są zależnościami zewnętrznymi, nie wynikami testów na atrapach.

Backend inicjuje DCF, zwraca panelowi kod, adres aktywacji i czas ważności. Odpytuje token endpoint zgodnie z interwałem odpowiedzi; obsługuje oczekiwanie, ograniczenie częstotliwości, odmowę, wygaśnięcie i anulowanie. Jedna aplikacja może mieć tylko jedną bieżącą próbę logowania. Kolejna próba unieważnia lokalnie poprzednią; spóźniona odpowiedź nie może zapisać poświadczeń po anulowaniu lub wylogowaniu.

Access token i refresh token zapisujemy jako jeden rekord przez `keyring`, wyłącznie w natywnym magazynie systemowym (Keychain/macOS, Credential Manager/Windows). Nie dopuszczamy zapisu jawnym tekstem przez zastępczy backend. Operacje magazynu wykonujemy poza pętlą asyncio. Brak dostępnego magazynu daje błąd połączenia konta, nie zapis do JSON. Testy wstrzykują magazyn w pamięci.

Odświeżanie tokena jest serializowane; rotowany refresh token zastępuje poprzedni. Nie ponawiamy w ciemno wymiany jednorazowego refresh tokena po niejednoznacznym wyniku sieciowym. Gdy odzyskanie sesji nie jest możliwe, wymagamy ponownego logowania. Token walidujemy przy przywracaniu sesji i co godzinę, sprawdzając także client ID, user ID i zakres. Cofnięcie autoryzacji kończy nasłuch Twitcha i wyłącza klawiaturę.

Odłączenie konta zatrzymuje aktywny nasłuch Twitcha, anuluje logowanie i odświeżanie, próbuje unieważnić token w Twitchu i usuwa lokalne poświadczenia niezależnie od wyniku sieciowego. Nasłuch TikToka nie zależy od sesji Twitcha.

## Lokalny interfejs autoryzacji

- `GET /api/twitch/auth`: bezpieczny stan sesji — skonfigurowana integracja, stan autoryzacji, login konta i komunikat błędu.
- `POST /api/twitch/auth/start`: rozpoczęcie próby, kod i URL aktywacji oraz czas ważności.
- `POST /api/twitch/auth/cancel`: anulowanie próby bez kasowania wcześniej połączonego konta.
- `DELETE /api/twitch/auth`: odłączenie konta.

Endpointy korzystają z obecnej kontroli hosta, originu, sesji i CSRF. Zmiany stanu autoryzacji publikujemy jako `twitch_auth`; po ponownym połączeniu panel pobiera aktualny stan. Access token, refresh token i device code nigdy nie trafiają do odpowiedzi API, localStorage, zdarzeń ani diagnostyki. Kod aktywacji użytkownika jest pokazywany tylko podczas próby logowania. Otwarcie adresu aktywacji wymaga kliknięcia użytkownika; URL musi wskazywać HTTPS Twitcha.

## Transport czatu

Adaptery zachowują `connect(on_comment)` zwracające monitorowane zadanie asyncio oraz idempotentne `disconnect()`. Fabryka dostaje snapshot ustawień aktywnego źródła zamiast samego nicku. Sekrety są wstrzykiwane przez usługę autoryzacji, nie przez konfigurację ani matcher.

Adapter Twitcha rozwiązuje login kanału przez Helix, otrzymuje sesję EventSub i tworzy subskrypcję `channel.chat.message` w czasie dozwolonym przez serwer. `connected` oznacza zaakceptowaną subskrypcję, nie samo otwarcie WebSocket. Używa ID zalogowanego użytkownika jako `user_id`, a ID wybranego kanału jako `broadcaster_user_id`.

Do callbacka trafiają `chatter_user_login` i `message.text`. Loginy Twitcha są normalizowane do małych liter po usunięciu białych znaków i opcjonalnego `@`; pole kanału przyjmuje login, nie pełny URL. Nie zmieniamy rozróżniania wielkości liter w filtrze TikToka. Dopasowanie komentarza nadal dotyczy całego `strip().lower()`.

Wiadomości Shared Chat pochodzące z innego kanału ignorujemy: jeśli `source_broadcaster_user_id` jest obecne i różni się od wybranego kanału, nie mogą sterować grą. Nie uzależniamy odczytu czatu Twitcha od statusu transmisji LIVE.

Deduplikacja używa ID wiadomości czatu i ID koperty EventSub; utrzymuje ograniczony cache w obrębie sesji nasłuchu, także przez kontrolowane przełączenie transportu. Proponowane granice: 10 minut i maksymalnie 10 000 wpisów na cache. Pomijamy nieznane typy zdarzeń; błędne wymagane dane protokołu powodują kontrolowany błąd, bez wykonywania akcji.

Obsługujemy Welcome, keepalive/watchdog, revocation i `session_reconnect`. Kontrolowane przeniesienie sesji według adresu Twitcha zachowuje subskrypcję i deduplikację; nie zakłada nowej subskrypcji. Akceptowane adresy reconnect muszą używać `wss`, domeny Twitcha i nie zawierać danych logowania. Stare połączenie pozostaje do czasu Welcome na nowym, potem jest zamykane. Nieoczekiwane zerwanie, przekroczony watchdog lub nieudany transfer kończą nasłuch i wymagają ponownego Startu.

## Cykl życia i panel

Start zapisuje platformę, kanał i rewizję jako aktywny snapshot. Zapis nowych ustawień podczas działania nie zmienia bieżącego połączenia. Pulpit pokazuje aktywne źródło ze stanu backendu oraz komunikat o potrzebie Stop → Start, gdy zapisano nowe ustawienia.

Po udanym połączeniu pozostaje opcjonalne odliczanie 3 s. Komentarze w trakcie odliczania mogą być widoczne w logu, ale nie są odkładane do późniejszego wykonania. Stop oraz wykryta awaria wyłączają przyjmowanie akcji i czyszczą kolejkę przed asynchronicznym sprzątaniem transportu. Już rozpoczęte wywołanie PyAutoGUI może się zakończyć. Stare callbacki i wyniki klawiatury nie wpływają na nową generację nasłuchu.

Panel oferuje selektor platformy, osobne zapamiętywane ustawienia kanału/użytkowników oraz stan konta Twitch. Start jest niedostępny przy braku kanału, błędzie zapisu lub braku autoryzacji Twitcha; backend wykonuje te same kontrole niezależnie od UI. Rozróżniamy brak kanału, kanał nieistniejący, brak uprawnień, błąd sieci, wygasłą sesję i niedostępny magazyn poświadczeń. Nie pokazujemy surowych odpowiedzi zawierających sekrety. Oba motywy panelu pozostają funkcjonalne.

## Odbiór i wdrożenie

1. Migracje v1 i v2 zachowują reguły, ID, ustawienia i kopie; błąd zapisu nie uszkadza oryginału. Przełączanie platform zachowuje niezależne filtry.
2. Testy OAuth obejmują sukces, odmowę, timeout, anulowanie, równoległe panele, rotację, błędy magazynu i brak sekretów w API/logach.
3. Testy transportu obejmują subskrypcję, keepalive, reconnect, revocation, duplikaty, Shared Chat i błędne dane. Wszystkie używają atrap HTTP/WebSocket.
4. Testy silnika sprawdzają całą ścieżkę komentarz → filtr → cooldown → jedna akcja, Stop podczas łączenia, awarię podczas odliczania, stare callbacki oraz brak regresji TikToka.
5. Testy API i React obejmują autoryzację endpointów, zmianę platformy, autosave, walidację Startu, aktywny snapshot i odzyskanie stanu po przeładowaniu panelu.
6. Uruchomić pełne testy Python, testy frontendu i jego build. Sprawdzić pakowanie natywnego backendu keyring oraz bezpośrednie deklaracje zależności HTTP/WebSocket.
7. Ręczny odbiór na rzeczywistym koncie: logowanie, odczyt, klawisz, Stop, restart aplikacji, odświeżenie/utrata autoryzacji. Paczki macOS i Windows wymagają osobnych wyników odbioru; brak dostępu do systemu lub konta pozostaje jawnym ograniczeniem.
8. Zaktualizować README, PROJECT_CONTEXT i dokument odbioru, rozdzielając wynik testów na atrapach od sprawdzenia rzeczywistej integracji.

## Źródła zweryfikowane podczas planowania

- [Autoryzacja czatu i EventSub](https://dev.twitch.tv/docs/chat/authenticating/)
- [Device Code Flow](https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/#device-code-grant-flow)
- [Walidacja tokenów](https://dev.twitch.tv/docs/authentication/validate-tokens/)
- [Cykl życia EventSub WebSocket](https://dev.twitch.tv/docs/eventsub/handling-websocket-events/)
- [Wiadomości czatu](https://dev.twitch.tv/docs/chat/send-receive-messages/)
