# Nakładka OBS — plan wdrożenia

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Implementacja inline, niezależny review przed scaleniem.

**Goal:** Przezroczysta nakładka pokazuje komendy, ostatni wykonany ruch i opcjonalnego autora bez dostępu do panelu sterowania.

**Architecture:** Osobny serwer loopback o trwałym porcie (domyślnie 18765), włączany w zakładce Nakładka OBS. Token i ustawienia prezentacji w oddzielnym pliku 0600. WebSocket uwierzytelnia pierwszą wiadomość; przesyła wyłącznie projekcję publicznego stanu. Panel zachowuje losowy port i obecne zabezpieczenia.

**Tech Stack:** Python/FastAPI/uvicorn, React/TypeScript, istniejące modele i executor.

**Spec:** Zadanie 4 w `2026-09-28-roadmap-rozwoju.md`, zatwierdzone wyborem „nr 4”.

## Global Constraints

- Nick domyślnie ukryty. Brak surowego czatu, filtrów, kanałów kont, tokenów i błędów integracji w publicznym stanie.
- Last action wyłącznie z potwierdzenia executora, wraz z autorem/komentarzem przenoszonymi przez KeyAction. Nowa generacja czyści ostatnią akcję.
- Token trwały w pliku 0600, możliwość obrotu odcina istniejące połączenia. Fragment URL nie trafia do logów. Osobny port nie udostępnia żadnego `/api` panelu.
- Domyślnie nakładka wyłączona; port 18765, zakres 1024–65535. Kolizja portu zgłasza błąd, bez losowego fallbacku. Aktualizacja ustawień rezerwuje nowy port przed zamknięciem starego.
- Auth WS do 5 s, Host/Origin dokładnie własnego serwera. Tylko auth i ping, ograniczone rozmiary. Wolny odbiorca rozłączany; aktualizacje maksymalnie 5/s z pełnym snapshotem, bez surowej kolejki eventów.
- Rozmiar fontu 16–48, akcent #RRGGBB, widoczność komend/ostatniej akcji/autora/statusu. Tekst React bez HTML. PL/EN.
- OBS nie znaleziono na lokalnym macOS; Windows niedostępny. Nie udajemy odbioru OBS: przeglądarka i testy sprawdzą protokół/przezroczystość/reconnect, instrukcja zaznaczy ograniczenie.

## Review Focus

1. Autor/komentarz musi odpowiadać wykonanej akcji, mimo nowszego czatu i zmian konfiguracji.
2. Rotacja odcina stare tokeny i już otwarte połączenia; token nie autoryzuje panelu.
3. Zajęty port i błąd zapisu nie zatrzymują LIVE ani działającego poprzedniego adresu.
4. Reconnect/reset usuwa nieaktualny ruch i nie pokazuje pustego stanu jako LIVE.
5. Ukryty nick nie opuszcza backendu; komentarze są zwykłym tekstem.

## Zadania

- [x] 1. Testy RED → GREEN publicznej projekcji, trwałości tokenu i danych wykonanej akcji: `tests/core/test_overlay.py`; pliki `src/core/overlay.py`, `listener_service.py`, `keyboard.py`.
- [x] 2. Testy RED → GREEN serwera tylko do odczytu, auth/rotacji/reconnect/kolizji i obsługi ustawień. `src/api/overlay.py`, `src/desktop/overlay_server.py`, integracja backend/app, testy API/desktop. Główne API GET/PUT `/api/overlay`, POST `/api/overlay/rotate` pozostają pod sesją i CSRF.
- [x] 3. Komponenty `overlay/Overlay.tsx`, klient WS, CSS przezroczysty i `OverlaySettings.tsx`; routing `/overlay`, nawigacja. Testy XSS/ukryty nick/pauza/stara odpowiedź/rozłączenie oraz formularza.
- [x] 4. Pełne testy, przeglądarka na atrapach, niezależny review. Dokumentacja instalacji źródła OBS i ograniczeń odbioru.
- [x] 5. VERSION i release notes, build macOS, kontrola paczki, commit/scalenie main/push/tag.

Wynik: 257 testów Python + 47 frontend, 1 natywny pominięty offscreen. Niezależny review odtworzył i zatwierdził poprawkę backpressure (send 2 s, close 0,2 s). Przeglądarka: tokenrotacja odcina stary link, przezroczysty HTML/body, font aktualizuje się w otwartym widoku, tryb pauza/LIVE odpowiada atrapie nasłuchu. Build macOS i kontrola podpisu ad-hoc/DMG; odbiór w OBS/Windows jawnie pozostaje niewykonany. Zamykanie nakładki następuje po zatrzymaniu listenera i klawiatury.
