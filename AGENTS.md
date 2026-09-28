# Kontekst projektu dla kolejnych sesji

Przed pracą przeczytaj [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md): opisuje przeznaczenie TikoPlay, przepływ danych, konfigurację, uruchamianie i problemy zauważone w kodzie.

- Odpowiadaj po polsku, konkretnie i bez zbędnych wstępów.
- To aplikacja desktopowa Python/PySide6: komentarze TikTok LIVE uruchamiają klawisze przez PyAutoGUI.
- Rzeczywista konfiguracja jest w katalogu użytkownika wyznaczanym przez `src/config.py`; repozytoryjny `config.json` nie jest wczytywany przez aplikację.
- Przed zmianami sprawdź `git status` i `git diff`. Nie nadpisuj istniejących zmian użytkownika.
- Przy testach izoluj konfigurację i zastępuj klienta TikTok oraz wywołania klawiatury atrapami, jeżeli test nie wymaga rzeczywistej integracji.
- Po istotnych zmianach aktualizuj dokument kontekstu. Ustalenia z analizy nie oznaczają, że opisane błędy zostały naprawione.
- Po każdym zakończonym zadaniu zapisz jego zmiany w commicie i wykonaj push na zdalne repozytorium. Nie dołączaj niezwiązanych zmian użytkownika.
- Każdy zestaw zmian oznacz unikalnym tagiem Git w formacie `v<major>.<minor>`, np. `v0.1`, `v0.2`, `v0.3`, i wypchnij ten tag na zdalne repozytorium. Zwiększaj numer kolejnej wersji; nie używaj tagów opisowych ani dat w nazwach tagów.
- Po każdych zmianach wykonaj build aplikacji i w odpowiedzi końcowej podaj klikalny link do gotowej aplikacji lub instalatora. Jeśli build się nie powiedzie, zgłoś błąd zamiast przedstawiać starszą paczkę jako aktualną.
