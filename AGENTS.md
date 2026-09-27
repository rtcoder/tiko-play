# Kontekst projektu dla kolejnych sesji

Przed pracą przeczytaj [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md): opisuje przeznaczenie TikoPlay, przepływ danych, konfigurację, uruchamianie i problemy zauważone w kodzie.

- Odpowiadaj po polsku, konkretnie i bez zbędnych wstępów.
- To aplikacja desktopowa Python/PySide6: komentarze TikTok LIVE uruchamiają klawisze przez PyAutoGUI.
- Rzeczywista konfiguracja jest w katalogu użytkownika wyznaczanym przez `src/config.py`; repozytoryjny `config.json` nie jest wczytywany przez aplikację.
- Przed zmianami sprawdź `git status` i `git diff`. Nie nadpisuj istniejących zmian użytkownika.
- Przy testach izoluj konfigurację i zastępuj klienta TikTok oraz wywołania klawiatury atrapami, jeżeli test nie wymaga rzeczywistej integracji.
- Po istotnych zmianach aktualizuj dokument kontekstu. Ustalenia z analizy nie oznaczają, że opisane błędy zostały naprawione.
