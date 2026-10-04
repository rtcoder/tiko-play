# Ochrona wyjścia i awaryjny STOP

Realizacja wybranej propozycji 2 i zadania 6 roadmapy. Cel: ograniczyć wysyłanie klawiszy do wybranej instancji aplikacji oraz umożliwić STOP bez panelu.

- Tożsamość: ścieżka aplikacji, PID, czas uruchomienia. Wybrany proces wyłącznie w pamięci; po restarcie TikoPlay wybór ponowny. Domyślnie ochrona wyłączona, bez zmiany profili/formatów wymiany.
- NSWorkspace na macOS; GetForegroundWindow/EnumWindows + QueryFullProcessImageName/GetProcessTimes na Windows. Nie identyfikujemy po samym tytule.
- Kontrola przed klawiszem/krokiem i co około 50 ms w hold/wait oraz podczas bezczynności. Utrata fokusu lub błąd odczytu wyłącza executor, opróżnia kolejkę, pauzuje wyjście. Powrót nie wznawia. Wznów: oczekiwanie na cel i 3 sekundy stabilnego fokusu.
- Globalny STOP Ctrl+Alt+Shift+F10; wybór F9/F10/F11. F12 odrzucono zgodnie z dokumentacją RegisterHotKey Microsoft. Carbon RegisterEventHotKey na macOS, RegisterHotKey na Windows; rejestracja na głównym wątku Qt, błędy i konflikty widoczne. Skrót tylko zatrzymuje.
- Osobna zakładka Ochrona gry, czytelny wybór procesu i status skrótu. Wybór celu i zmiana skrótu tylko przy zatrzymanej sesji. Chronione API panelu; brak danych celu w publicznym OBS.
- Testy tożsamości, PID reuse, błędu odczytu, hold cleanup, STOP/odliczanie, jawne wznowienie, rejestracja/konflikt i API. Przegląd niezależny, testy pełne, build i tag.

Próba macOS: NSWorkspace daje procesy z PID/czasem uruchomienia/bundle URL; symbole Carbon dostępne. Windows niedostępny do natywnego odbioru. Odczyt fokusu i wejście OS nie są transakcją: pozostaje minimalny wyścig; 50 ms to cel, nie gwarancja real-time. Nie przenosimy fokusu ani nie wysyłamy do tła. W obrębie tej samej aplikacji ochrona nie odróżnia jej okien/dialogów.
