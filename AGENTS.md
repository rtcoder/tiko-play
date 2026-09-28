# Kontekst projektu dla kolejnych sesji

Przed pracą przeczytaj [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md): opisuje przeznaczenie TikoPlay, przepływ danych, konfigurację, uruchamianie i problemy zauważone w kodzie.

- Odpowiadaj po polsku, konkretnie i bez zbędnych wstępów.
- To aplikacja desktopowa Python/PySide6: komentarze TikTok LIVE uruchamiają klawisze przez PyAutoGUI.
- Rzeczywista konfiguracja jest w katalogu użytkownika wyznaczanym przez `src/config.py`; repozytoryjny `config.json` nie jest wczytywany przez aplikację.
- Przed zmianami sprawdź `git status` i `git diff`. Nie nadpisuj istniejących zmian użytkownika.
- Przy testach izoluj konfigurację i zastępuj klienta TikTok oraz wywołania klawiatury atrapami, jeżeli test nie wymaga rzeczywistej integracji.
- Po istotnych zmianach aktualizuj dokument kontekstu. Ustalenia z analizy nie oznaczają, że opisane błędy zostały naprawione.
- Po każdym zakończonym zadaniu zapisz jego zmiany w commicie i wykonaj push na zdalne repozytorium. Nie dołączaj niezwiązanych zmian użytkownika.
- Każdy zestaw zmian oznacz unikalnym, rosnącym tagiem Git `v<major>.<minor>` i wypchnij go na zdalne repozytorium. Dobieraj skok numeru do liczby, zakresu i znaczenia zmian od poprzedniego wydania, zamiast automatycznie zwiększać minor o 1 po każdym zadaniu. Większy pakiet niezależnych zmian uzasadnia większy skok minor; przełomowa przebudowa lub zmiany niekompatybilne uzasadniają major i wyzerowanie minor. Uzasadnij wybór w opisie wydania. Nie traktuj wersji jako licznika commitów; nie używaj tagów opisowych ani dat.
- Jedynym źródłem numeru aplikacji jest `VERSION` (bez prefiksu `v`). Przed tagowaniem zaktualizuj go tak, aby tag, UI `.version`, Ustawienia i paczki miały tę samą wersję. Nie wpisuj numeru na sztywno w UI ani skryptach builda.
- Każdy release musi mieć konkretny opis w `releases/v<major>.<minor>.md`: zmiany widoczne dla użytkownika, istotne poprawki, powód zmiany numeru oraz ograniczenia lub uwagi instalacyjne. Sama lista commitów, pusty szablon lub ogólne „poprawki” nie wystarczą. Workflow po pushu tagu sprawdza wersję i obecność opisu, buduje paczki, wykonuje testy i publikuje GitHub Release z tym opisem.
- Po każdych zmianach wykonaj build aplikacji i w odpowiedzi końcowej podaj klikalny link do gotowej aplikacji lub instalatora. Jeśli build się nie powiedzie, zgłoś błąd zamiast przedstawiać starszą paczkę jako aktualną.
