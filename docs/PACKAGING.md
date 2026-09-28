# Pakowanie TikoPlay

Build musi powstać na docelowym systemie. Skrypty budują frontend przed PyInstaller i dołączają pliki statyczne oraz ikony. Nie pakują konfiguracji użytkownika. Zależności runtime i developerskie są przypięte w requirements, frontend ma package-lock.json.

## macOS

```sh
bash build-macos.sh
```

Wynik: `dist/TikoPlay.app` oraz `dist/TikoPlay-<VERSION>-macos-<arch>.dmg` (`arm64` lub `x86_64`). Numer pochodzi z pliku `VERSION`. DMG zawiera aplikację, odnośnik do Applications oraz instrukcję aliasu na pulpicie. Nie jest to link do adresu HTTP: alias uruchamia pełną .app. Opcjonalne `PYTHON_BUILD=/ścieżka/do/python` pozwala wykorzystać istniejące środowisko zamiast `.venv`.

PyInstaller stosuje lokalny podpis ad-hoc; to nie jest podpis dystrybucyjny Developer ID. Do wydania publicznego potrzebny jest certyfikat Apple, podpisanie aplikacji odpowiednimi uprawnieniami, notaryzacja przez `xcrun notarytool` i stapling. Dane konta/certyfikatu przechowuj poza repozytorium. Skrypt nie usuwa quarantine i nie obchodzi Gatekeepera.

## Windows

Potrzebne Python, Node.js oraz Inno Setup 6 z ISCC.exe w PATH:

```bat
build-windows.bat
```

Wynik: `dist\TikoPlay\TikoPlay.exe` i `dist\installer\TikoPlay-<VERSION>-windows-x64-setup.exe`. Buduj Pythonem x64. Instalacja per-user tworzy skróty na pulpicie i w menu Start. Dane w AppData nie należą do katalogu instalacji i pozostają po odinstalowaniu.

Przed aktualizacją zakończ program z traya. Podpis Authenticode i certyfikat dystrybucyjny muszą zostać dostarczone przez wydawcę. Automatyczny build i testy nie zastępują odbioru instalatora na Windows.

## Wydanie z tagu

1. Dobierz rosnącą wersję `major.minor` do zakresu zmian zgodnie z `AGENTS.md` i zapisz ją w `VERSION` (bez `v`). Frontend wczytuje ten plik podczas builda, a paczki używają go w metadanych i nazwach.
2. Napisz `releases/v<major>.<minor>.md` z opisem zmian, uzasadnieniem numeru i ograniczeniami wydania.
3. Sprawdź `python release_support.py v<major>.<minor>`, testy i lokalny build, zapisz zmiany w commicie i wypchnij commit.
4. Utwórz tag tego commita i wypchnij go: `git tag -a v<major>.<minor> -m 'TikoPlay ...'`, `git push origin v<major>.<minor>`.

`.github/workflows/release.yml` weryfikuje tag i opis, buduje DMG na macOS arm64/Intel oraz instalator Windows x64, wykonuje testy Python i frontend na każdej platformie. Po sukcesie wszystkich zadań publikuje GitHub Release z zapisanym opisem, trzema paczkami i `SHA256SUMS.txt`. Błąd któregokolwiek zadania blokuje publikację. Numeracja jest dwuczłonowa; np. `v0.7-test` i `v0.7.1` są odrzucane. Numer schematu konfiguracji jest niezależny od wersji aplikacji.

Workflow korzysta wyłącznie z oficjalnych akcji GitHub i wbudowanego `GITHUB_TOKEN` z prawem `contents: write` tylko w zadaniu publikacji. GitHub Actions musi być włączone w repozytorium. Paczki pozostają bez podpisów dystrybucyjnych i notaryzacji.

## Kontrola gotowej paczki

Uruchom z ikony na komputerze bez środowiska developerskiego. Sprawdź ponowne kliknięcie, otwarcie panelu, restart, zamknięcie z traya, konfigurację po aktualizacji i prawa do wysyłania klawiszy. Na macOS testuj tożsamość gotowej .app, nie tylko interpretera Python, ponieważ uprawnienia Dostępność są przypisane do aplikacji.

Paczki testowe nie powinny zastępować stabilnego wydania przed zakończeniem macierzy w WEB_UI_ACCEPTANCE.md.
