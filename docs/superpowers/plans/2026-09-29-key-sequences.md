# Wdrożenie propozycji 2 — sekwencje klawiszy

Zakres: press, hold 50–3000 ms, wait 10–3000 ms, 1–20 kroków i suma zadeklarowanych czasów do 10 s. Kombinacje są jednoczesne. Bez pętli, myszy i kodu użytkownika.

1. Modele akcji, walidacja i migracja konfiguracji v5 → v6 z kopią oryginału; stary wpis keys staje się jednym press. Eksport profilu v2, import v1/v2.
2. Jeden wykonawca, kolejka i epoka wyjścia; przerywalne oczekiwanie, zwalnianie w finally, trwała blokada po błędzie keyUp. Testy kolejności, błędów i przerwań.
3. Edytor kroków, zmiana kolejności, walidacja czasów i zachowanie niepełnego szkicu; presety, kopiowanie, import i dziennik obsługują akcje.
4. Pełne testy, niezależny przegląd, build macOS, dokumentacja, wersja, commit, merge main oraz push z tagiem.

Ruling: Z zależności zadań 5 i 6 wdrażamy tylko anulowanie, epokę i czyszczenie kolejki niezbędne dla sekwencji. Ochrona fokusu i konfigurowalne limity pozostają poza zakresem; aplikacja nadal wysyła do aktywnego okna.
Ruling: Zachowujemy wejściową zgodność z keys i pomocniczy odczyt pojedynczej kombinacji. Trwały zapis używa wyłącznie action.steps; sekwencje nie mogą zostać po cichu spłaszczone.

Weryfikacja: testy używają atrap klawiatury i izolowanej konfiguracji. Natywna zgodność z grami oraz Windows wymaga osobnego testu na docelowym systemie.

## Wyniki i przegląd
- Modele i migracja: testy RED→GREEN, stare mapowania zachowane, profile v1/v2.
- Wykonawca: testy RED→GREEN kolejności, hold/wait, epoki, awarii down/up; integracja Stop i utraty czatu.
- UI: test RED→GREEN edycji, kolejności i niepełnego czasu; przegląd w przeglądarce potwierdził błąd 25 ms, poprawę do 750 ms, przestawienie i zapis.
- Final: fixed P1 — fail-safe przed keyUp uniemożliwiał cleanup; adapter zwalnia przez __wrapped__ wyłącznie keyUp, zachowując fail-safe dla nowych naciśnięć. Testy cleanup i przerwania hold przez fail-safe RED→GREEN. Oczekiwanie sprawdza fail-safe co najwyżej co 50 ms (bez gwarancji czasu rzeczywistego).
- Final: fixed brak sumy czasów (przegląd oznaczył P3, podniesione do wymagania specyfikacji) — test podsumowania czasu RED→GREEN.
- Końcowy pełny zestaw po poprawkach: 213 testów Python zaliczonych, 1 natywny pominięty (offscreen); 34 testy frontendu zaliczone. Build panelu TypeScript/Vite poprawny. Nie pozostały odłożone uwagi przeglądu.
- Build macOS arm64: aplikacja oraz DMG 0.14 poprawne; codesign --verify --deep --strict i hdiutil verify poprawne. Testy z atrapami nie zastępują próby wejścia w docelowej grze.
