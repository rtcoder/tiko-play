# Nakładka TikoPlay w OBS

1. Uruchom TikoPlay, wejdź w **Nakładka OBS** i zaznacz **Włącz nakładkę**.
2. Kliknij **Zapisz i zastosuj**, następnie **Kopiuj adres**.
3. W OBS dodaj źródło **Przeglądarka / Browser** i wklej cały adres, łącznie z fragmentem `#token=…`.
4. Na początek ustaw **900 × 600**. Umieść źródło ponad obrazem gry. Przy wielu komendach zwiększ wysokość lub ukryj listę w ustawieniach nakładki.
5. Rozpocznij nasłuch w TikoPlay. Nakładka pokaże dostępne komendy, stan sterowania i ostatnią zakończoną akcję.

Tło poza kartami jest przezroczyste. Podgląd w panelu używa przykładowych danych; sam nie wywołuje klawiszy i nie oznacza trwającego LIVE. Nakładka pokazuje tylko rzeczywiste zakończenia akcji z executora; nie pokazuje komentarzy odrzuconych przez mapowania ani wyników symulatora. Przy długiej sekwencji wynik pojawia się po ostatnim kroku.

## Wygląd i nicki

Rozwiń **Dostosuj wygląd**. Możesz pokazać lub ukryć komendy, ostatni ruch, nick autora i stan sterowania. Rozmiar tekstu: 16–48 px; akcent wybiera się próbnikiem koloru. Zmiany zastosujesz przyciskiem **Zapisz i zastosuj**; działają w otwartej nakładce bez odświeżania. Nick autora jest domyślnie ukryty i w tym trybie nie jest wysyłany do źródła OBS.

## Adres i restart

Nakładka działa na tym samym komputerze co TikoPlay. Ma oddzielny stały port loopback, domyślnie **18765**. Adres panelu operatora nadal zmienia się przy uruchamianiu — nie należy wklejać go do OBS.

Zapisany adres nakładki przetrwa restart TikoPlay. Już załadowana strona automatycznie ponawia połączenie i pobiera pełny stan; nie pokazuje starej akcji jako aktualnej przy zerwanym połączeniu. Sam nasłuch LIVE nie uruchamia się automatycznie po restarcie.

Jeżeli OBS otwarto przed TikoPlay i źródło pokazało błąd ładowania strony, po uruchomieniu TikoPlay odśwież źródło przeglądarkowe. Kod ponawiania połączenia może działać dopiero po załadowaniu strony.

Jeśli port jest zajęty, wybierz inny w panelu i zapisz. TikoPlay nie wybiera innego portu po cichu. Nieudana zmiana nie wyłącza poprzedniego działającego adresu. Po udanej zmianie portu wklej nowy adres do OBS.

**Zmień adres nakładki → Wygeneruj nowy adres** unieważnia poprzednie uprawnienie i rozłącza korzystające z niego źródła. Skopiuj nowy link do każdego źródła. Link daje tylko odczyt nakładki — nie pozwala uruchamiać nasłuchu ani czytać konfiguracji panelu.

Ustawienia prezentacji i token zapisują się w oddzielnym `overlay.json` w katalogu danych TikoPlay, bez zmiany schematu konfiguracji v6. Plik jest tworzony atomowo z uprawnieniami 0600 na systemach POSIX. Nie wchodzi do eksportów profili.

## Zakres weryfikacji wydania 0.21

Testy automatyczne obejmują potwierdzenia wykonania, oddzielenie autorów, ukrywanie nicku, auth/origin/CSRF, rotację, reconnect, restart rzeczywistego serwera HTTP/WebSocket, kolizję portu, błąd zapisu oraz zablokowanego odbiorcę. Przeglądarka potwierdziła przezroczysty CSS, włączenie źródła, zmianę fontu i stan testowego nasłuchu.

OBS nie był zainstalowany w środowisku macOS użytym do wdrożenia; źródła w prawdziwym OBS i działania na Windows nie zweryfikowano. Nie jest to deklaracja zaliczonego odbioru w OBS. Po instalacji pozostaje sprawdzić kompozycję obrazu, restart aplikacji z aktywnym źródłem i unieważnienie adresu w używanej wersji OBS.
