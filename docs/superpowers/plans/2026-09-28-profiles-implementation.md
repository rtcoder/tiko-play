# Profile gier — wykonanie zadania 1

Zakres zatwierdzony w rozmowie: profile gier oraz dodatkowy preset NumPad 2468. Specyfikacja: zadanie 1 w [roadmapie](2026-09-28-roadmap-rozwoju.md). Pozostałe siedem zadań nie jest częścią wdrożenia.

## Decyzje wykonawcze

- Zestaw startowy: rekomendowane Hugo, Tetris, Pac-Man, Sokoban, Baba Is You i presety ogólne WASD/Strzałki/NumPad 2468. Gry wymagające hold nie są dodawane jako pozornie działające profile.
- CRUD korzysta z istniejącego atomowego PUT konfiguracji z rewizją; nowe endpointy służą katalogowi szablonów, eksportowi i podglądowi importu. Nie powielamy mechanizmu zapisu. Koszt zmiany decyzji: wydzielenie osobnych tras CRUD.
- Jedno źródło danych mapowań i filtrów: `profiles`. Wewnętrzne właściwości `mappings` i `active_source()` rozwiązują wybrany profil; nie zapisujemy drugiej kopii aktywnych mapowań.
- Zmiana aktywnego profilu lub zbioru ID profili jest blokowana podczas łączenia/pracy/zatrzymywania. Edycja mapowań/filtrów zachowuje istniejący snapshot ze Startu i komunikat o ponownym uruchomieniu.
- Start i zapis konfiguracji współdzielą blokadę API; STOP nadal może przerwać oczekujący Start. Profile nie przenoszą kanałów, kont ani kluczy.
- Import ma podgląd i osobny przycisk zatwierdzenia. Eksport używa allowlisty; nie eksportuje filtrów ani dodatkowych pól mapowań. Nazwy i mapowania pozostają treścią użytkownika.

## Plan i zapis postępu

- [x] Czysty punkt wyjścia: 174 testy Python, 1 natywny pominięty.
- [x] RED: migracja, aktywne mapowania/filtry, kolekcje profili, NumPad, import/eksport — 9 porażek przed implementacją.
- [x] GREEN: modele/migracja i rdzeń — 28 testów profili oraz matchera.
- [x] API: limity importu, autoryzacja, blokada aktywnej sesji, rewizje i zapis.
- [x] Panel: wybór, tworzenie z szablonu, zmiana nazwy, duplikowanie, usuwanie, podgląd importu, eksport, obsługa szkicu i błędów.
- [x] PL/EN, regresje, testy pełne i przegląd niezależny: 191 Python, 1 pominięty natywny, 31 frontend; build UI poprawny. Przeglądane dwa P2 poprawione testami RED → GREEN; brak odroczonych uwag.
- [x] Build macOS 0.12, opis wydania, zgodność Info.plist i podpisu ad-hoc; pakiet gotowy do commita, integracji i pushu z tagiem.

## Przegląd

Niezależny reviewer wskazał dwie poprawki: stan `working` po unieważnieniu importu przez zmianę profilu w drugiej karcie oraz zbyt szerokie zastosowanie limitu 500 mapowań do migracji. Obie odtworzono testami RED; poprawka resetuje stan importu i zachowuje limit tylko dla formatu importowanego pliku. Żaden dawny profil nie jest skracany.

Testy API nazwano `tests/api/test_profile_routes.py`, ponieważ powielenie nazwy `test_profiles.py` w dwóch katalogach bez pakietów powoduje kolizję kolekcji pytest. Nie zmienia to zakresu testów.
