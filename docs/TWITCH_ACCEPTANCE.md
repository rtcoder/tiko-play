# Odbiór integracji Twitch — 2026-09-27

Implementacja w izolowanym checkoutcie `twitch-chat`, przed połączeniem z main. Zakres: jedna wybrana platforma, EventSub, DCF, natywny magazyn tokenów, konfiguracja v3 i panel React.

| Sprawdzenie | Wynik |
| --- | --- |
| Testy bazowe przed zmianami | 58 Python, 12 frontend — PASS |
| Regresja po implementacji panelu | 102 Python, 17 frontend — PASS |
| Dodatkowe testy speców pakowania | 3 — PASS |
| Build frontend (TypeScript + Vite) | PASS |
| Panel Klasyczny i Glass w przeglądarce | Sprawdzono z atrapą konta, kanału i klawiatury; nowe pola i przyciski widoczne, bez nakładania elementów |
| Build macOS | PASS; finalna przebudowa po poprawkach z przeglądu i ponowny smoke test gotowej paczki |
| Uruchomienie gotowej paczki macOS | PASS: osobny tymczasowy katalog, panel/API, konfiguracja v3, brak Client ID nie blokuje startu; bez fizycznych kliknięć traya i bez odczytu prawdziwych tokenów |
| Windows | Niewykonane: brak hosta Windows |
| Rzeczywisty OAuth/EventSub/sterowanie grą | Niewykonane: brak Client ID oraz autoryzacji konta Twitch |
| Niezależny przegląd | Wykonany: 4 Important poprawione przez regresje RED → GREEN, 1 Minor odłożony |

Testy nie używają prawdziwego konta Twitch, nie czytają systemowych tokenów i nie wysyłają prawdziwych klawiszy. Podgląd używał osobnego katalogu w `/tmp`. Konfiguracja użytkownika poza repozytorium nie została zmieniona.

Przed wydaniem: ustawić publiczny Client ID aplikacji typu Public; zalogować się poprzez DCF; potwierdzić odczyt komentarza i akcję w kontrolowanym oknie; sprawdzić Stop, restart aplikacji, utratę sieci, odświeżenie i cofnięcie autoryzacji. Powtórzyć odbiór z gotowej paczki na Windows. Paczka testowa jest podpisana ad-hoc, bez notaryzacji dystrybucyjnej.

Decyzje wykonawcze: osobne środowiska zależności w worktree (poprzednie nie zawierały test runnerów), techniczne nagłówki Task w planie na potrzeby narzędzi (bez zmiany zakresu); dodatkowy publiczny numer próby logowania pozwala usuwać przestarzały kod aktywacji w wielu panelach. Pozostałe reguły zgodne ze specyfikacją. Ograniczony cache deduplikacji nie zapewnia globalnego exactly-once poza sesją/limitem cache.

## Końcowa regresja po przeglądzie

111 testów Pythona i 17 testów frontendu — PASS. TypeScript/Vite build — PASS. Dodano także test kontrolowanego reconnect na prawdziwych lokalnych WebSocketach: dziesięć różnych wiadomości starego połączenia dociera do callbacka bez utraty, przy jednej subskrypcji EventSub. Test nie łączy się z Twitchem.

Poprawki przeglądu:
- Po udanej rotacji i błędzie walidacji lub anulowaniu operacji zużyty refresh token nie jest ponawiany; wymagana może być nowa autoryzacja.
- Każda próba DCF zachowuje własny numer sprzed pierwszego await; spóźnione żądanie nie zastępuje nowszego.
- Kontrolowane zamknięcie starego socketu opróżnia odebrane wiadomości z ograniczeniem czasu i wspólną deduplikacją.
- Przejściowy błąd walidacji przy starcie zachowuje niewalidowane poświadczenia do ponowienia przez monitor; nie wznawia automatycznie sterowania.

Odłożony Minor: revocation EventSub lub Helix 401 zatrzymuje listener i klawiaturę, lecz stan konta może pozostać „połączone” do następnej walidacji OAuth (do godziny). Ponowny Start może ponownie zgłosić błąd. Można ręcznie połączyć konto ponownie. `version_removed` również obecnie otrzymuje ogólny komunikat ponownego połączenia konta, zamiast komunikatu zmiany protokołu.

Granice przeglądu: reviewer nie wykonywał odbioru prawdziwego Twitcha, interaktywnych monitów magazynu OS ani Windows. Oględziny obu motywów wykonał implementer. Nie deklarujemy odbioru tych integracji na podstawie zielonych testów.
