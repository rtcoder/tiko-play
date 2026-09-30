# Wdrożenie symulatora czatu (zadanie 7)

1. Wydzielić czysty resolver MatchDecision i zachować produkcyjne dopasowanie, filtr widza i cooldown 300 ms. Testy równoważności.
2. Dodać izolowane wykonanie na wirtualnym zegarze: 1–1000 wiadomości, offset 0–60000 ms, komentarz do 2000 znaków. Stabilne sortowanie; FIFO 100 oczekujących, ważność 1 s sprawdzana przed rozpoczęciem. Wynik: powód decyzji oraz planowane czasy kroków.
3. Chroniony POST /api/simulation, limit 4 MiB, wybór profilu/platformy z kopii zapisanej konfiguracji i oczekiwanej rewizji. Brak dostępu do listenera, klawiatury i adapterów czatu.
4. Zakładka Symulator: pojedynczy komentarz, osobny wybór profilu/platformy/widza, rozwijany scenariusz, przykład spamu, wyniki i podgląd kroków. Niezapisany szkic nie jest przesyłany; raport oznacza użyty zapis i staje się nieaktualny po zmianie ustawień.
5. Testy rdzenia/API/UI, odbiór w przeglądarce na atrapach, niezależny przegląd, build, dokumentacja, commit i push main/tag.

Ruling: Symulacja przedstawia idealny przebieg czasowy wynikający z zadeklarowanych hold/wait. Naciśnięcia mają zerowy koszt; rzeczywisty OS, gra i wątek mogą wprowadzać opóźnienia. Zdarzenia kończące akcję w tej samej chwili są obsługiwane przed nową wiadomością. Te ograniczenia są widoczne w UI.
Ruling: Zachowujemy obecne zasady produkcyjne (w tym cooldown zużyty przez matcher przed odmową kolejki i granicę ważności now > expires_at). Zmiana limitów i ich semantyki należy do zadania 5; symulator nie może zmieniać zachowania LIVE przy okazji.

Wykonanie inline z TDD. Symulator używa wspólnego resolvera/decydenta i polityki kolejki, ale nigdy KeyboardExecutor ani PyAutoGUI. Nie wymaga kanału ani kluczy konta. Nie dodaje głosowania i tur z kolejnych zadań.

Odbiór: 241 testów Python + 41 frontend poprawnych, jeden test natywny pominięty offscreen. Niezależny review zamknął poprawkę granic float: symulator ma integer ms, Matcher przyjmuje czas cooldownu w jednostce wstrzykniętego zegara; LIVE zachowuje domyślne sekundy. Build macOS arm64 i sprawdzenie podpisu ad-hoc poprawne. Wynik pojedynczego komentarza i wyrównanie pól sprawdzone w przeglądarce na danych tymczasowych; nie uruchamiano rzeczywistego czatu ani gry.
