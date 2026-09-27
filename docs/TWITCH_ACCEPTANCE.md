# Odbiór integracji Twitch — 2026-09-27

Implementacja w izolowanym checkoutcie `twitch-chat`, przed połączeniem z main. Zakres: jedna wybrana platforma, EventSub, DCF, natywny magazyn tokenów, konfiguracja v3 i panel React.

| Sprawdzenie | Wynik |
| --- | --- |
| Testy bazowe przed zmianami | 58 Python, 12 frontend — PASS |
| Regresja po implementacji panelu | 102 Python, 17 frontend — PASS |
| Dodatkowe testy speców pakowania | 3 — PASS |
| Build frontend (TypeScript + Vite) | PASS |
| Panel Klasyczny i Glass w przeglądarce | Sprawdzono z atrapą konta, kanału i klawiatury; nowe pola i przyciski widoczne, bez nakładania elementów |
| Build macOS | W trakcie weryfikacji |
| Uruchomienie gotowej paczki macOS | Oczekuje na build |
| Windows | Niewykonane: brak hosta Windows |
| Rzeczywisty OAuth/EventSub/sterowanie grą | Niewykonane: brak Client ID oraz autoryzacji konta Twitch |
| Niezależny przegląd | Oczekuje |

Testy nie używają prawdziwego konta Twitch, nie czytają systemowych tokenów i nie wysyłają prawdziwych klawiszy. Podgląd używał osobnego katalogu w `/tmp`. Konfiguracja użytkownika poza repozytorium nie została zmieniona.

Przed wydaniem: ustawić publiczny Client ID aplikacji typu Public; zalogować się poprzez DCF; potwierdzić odczyt komentarza i akcję w kontrolowanym oknie; sprawdzić Stop, restart aplikacji, utratę sieci, odświeżenie i cofnięcie autoryzacji. Powtórzyć odbiór z gotowej paczki na Windows. Paczka testowa jest podpisana ad-hoc, bez notaryzacji dystrybucyjnej.

Decyzje wykonawcze: osobne środowiska zależności w worktree; dodatkowy publiczny numer próby logowania pozwala usuwać przestarzały kod aktywacji w wielu panelach. Pozostałe reguły zgodne ze specyfikacją. Ograniczony cache deduplikacji nie zapewnia globalnego exactly-once poza sesją/limitem cache.
