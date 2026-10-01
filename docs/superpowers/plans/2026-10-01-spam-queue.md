# Kontrola spamu i kolejki

Realizacja zadania 5 zatwierdzonej roadmapy. Ustawienia per profil: odstęp widza 0–60000 ms (domyślnie 0), komendy 0–60000 ms (300), kolejka 1–100 oczekujących (100), ważność 100–5000 ms (1000). Pełna kolejka odrzuca nową akcję bez zużycia cooldownu. Aktywna akcja nie podlega TTL; dokładny termin nadal jest ważny, zgodnie z dotychczasowym executorem.

1. Testy limitów i wspólny RateLimiter check/commit, ograniczony do 10000 widzów i 120 s pamięci. Tylko zaakceptowane akcje zmieniają cooldown.
2. Konfiguracja v7 z kopią v6; format profilu v3 z limitami, import v1/v2 z domyślnymi wartościami.
3. Executor: pojemność, klasyfikacja odmowy, raport wygasłych/anulowanych akcji. Listener: liczniki sesji i ograniczona próbka ostatnich decyzji, publikacja najwyżej raz na sekundę, reset przy Start. Ochrona generacji i epoki.
4. Symulator korzysta z tego samego limitera i ustawień, z zegarem całkowitym w milisekundach.
5. Zakładka Kontrola spamu: proste odstępy, rozwijana kolejka, liczniki oraz ostatnie decyzje z powodami. PL/EN, zmiany obowiązują od kolejnego Startu.
6. Testy rdzenia/API/UI, niezależny review, podgląd z atrapami, build macOS, dokumentacja, commit, merge main, push i tag.

Bez banów, wykrywania botów i zmiany polityki FIFO. Próbka decyzji jest ograniczona; liczniki obejmują wszystkie zdarzenia. Podsumowania nie zastępują potwierdzenia faktycznego wykonania przez executor.
