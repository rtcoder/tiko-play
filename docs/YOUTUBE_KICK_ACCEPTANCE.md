# Odbiór integracji YouTube i Kick

Stan: 2026-09-27. Zmiany pozostają w bieżącym checkoutcie, bez commitu.

## Zakres

- Cztery źródła: TikTok, Twitch, YouTube, Kick. Jeden aktywny nasłuch, oddzielne kanały/filtry, wspólne mapowania.
- Konfiguracja v4: migracja v1/v2/v3 z kopią oryginalnego JSON; ustawienia i aktywne źródło v3 zachowane.
- YouTube: URL/ID transmisji, klucz YouTube Data API v3 w macOS Keychain/Windows Credential Manager, oficjalny streaming gRPC. API klucza jest write-only i podlega zabezpieczeniom sesji. Zmiana/usunięcie klucza wymaga Stop.
- Filtr YouTube używa ID kanałów UC…; nazwy wyświetlane nie są tożsamością użytkownika. Pierwsza paczka historii, wiadomości starsze od rozpoczęcia połączenia oraz duplikaty nie wykonują akcji. Tylko zwykłe wiadomości tekstowe są komendami.
- Kick: anonimowa integracja nieoficjalna, w całości lokalna. Odczyt kanału + bezpośredni Pusher WSS. Żadnego serwera, webhooka ani tunelu. Opcjonalne ID pokoju omija odczyt loginu, ale musi odpowiadać kanałowi; panel czyści je po zmianie loginu.
- Błędy kończą nasłuch i wyłączają klawisze. Wznowienie wymaga Start.

## Wykonane sprawdzenia

1. `python -m pytest -q --tb=short`: **150 passed, 2 skipped**. Testy używają tymczasowej konfiguracji, atrap magazynu poświadczeń i klawiatury oraz lokalnych transportów. Pominięte testy wymagają natywnej platformy Cocoa, a zestaw działał w trybie offscreen.
2. `npm --prefix frontend test -- --run`: **20 passed**, 9 plików testowych. Sprawdzono m.in. przełączanie źródeł, niezależność ustawień i write-only obsługę klucza.
3. `npm --prefix frontend run build`: TypeScript oraz produkcyjny build Vite zakończone powodzeniem.
4. Ruff nowych plików i `git diff --check`: bez błędów.
5. Rzeczywisty transport gRPC z lokalną atrapą serwera: serializacja, metoda RPC, części odpowiedzi, klucz w metadanych, wiadomości, zakończenie strumienia i bezpieczne tłumaczenie błędów.
6. Krótki **rzeczywisty odbiór publicznego czatu Kick**: odczyt kanału HTTP 200, potwierdzona subskrypcja, odebrana wiadomość, poprawne zatrzymanie adaptera. Nie zapisywano treści/nicków, nie wysyłano wiadomości ani klawiszy.
7. Wizualna kontrola panelu w przeglądarce: YouTube, wybór Kicka, rozwijane ID pokoju. Podgląd używał osobnej tymczasowej konfiguracji, magazynu klucza w pamięci i klawiatury blokującej wysyłanie. Podgląd zamknięto.
8. Niezależny przegląd wykrył wyścig Stop podczas odczytu klucza przed Start. Poprawiony przez licznik Stop sprawdzany przed aktywacją; test regresji najpierw odtworzył błąd, następnie przeszedł. Ponowny przegląd zaakceptował poprawkę.

9. Paczka macOS zbudowana w `dist/youtube-kick/TikoPlay.app` (osobny katalog, poprzednia paczka zachowana). Sprawdzono zawartość archiwum: adaptery, wygenerowany protobuf, grpc i natywna biblioteka cygrpc. Uruchomiono gotowy plik wykonywalny z tymczasowym `--data-dir` i Qt offscreen: `/api/health` oraz panel HTTP 200, konfiguracja v4 z YouTube/Kick. Proces testowy zakończony. To paczka testowa bez podpisu dystrybucyjnego/notaryzacji.
10. `pip check`: brak konfliktów zależności.

## Granice odbioru

- **YouTube nie sprawdzono z prawdziwym kluczem i transmisją.** Test loopback oraz zgodność z dokumentacją nie dowodzą działania na koncie użytkownika. W Google Cloud trzeba włączyć YouTube Data API v3, utworzyć klucz i mieć dostępny limit API.
- Kick korzysta z nieudokumentowanego przez Kick transportu; bieżący test nie gwarantuje odporności na późniejsze zmiany lub blokady.
- Nie wykonano rzeczywistych akcji klawiatury z nowymi źródłami; mechanizm mapowania i sterowania został objęty testami z atrapami.
- Windows i jego paczka nie zostały uruchomione na Windows.
- Poprawki traya/Cocoa zastane przed zadaniem zachowano; test nowych integracji nie jest odbiorem fizycznego menu macOS.

## Źródła protokołu

- [YouTube: Streaming Live Chat, autoryzacja i numery pól proto](https://developers.google.com/youtube/v3/live/streaming-live-chat)
- [YouTube: streamList](https://developers.google.com/youtube/v3/live/docs/liveChatMessages/streamList)
- [Pusher Channels Protocol](https://pusher.com/docs/channels/library_auth_reference/pusher-websockets-protocol/)
- [Nieoficjalny klient kick-wss: obserwowany endpoint i nazwy kanałów](https://github.com/nglmercer/kick-wss/blob/main/src/WebSocketManager.ts)
