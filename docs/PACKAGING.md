# Pakowanie TikoPlay 2.0

Build musi powstać na docelowym systemie. Skrypty budują frontend przed PyInstaller i dołączają pliki statyczne oraz ikony. Nie pakują konfiguracji użytkownika. Zależności runtime i developerskie są przypięte w requirements, frontend ma package-lock.json.

## macOS

```sh
bash build-macos.sh
```

Wynik: `dist/TikoPlay.app` oraz `dist/TikoPlay-2.0.0-test.dmg`. DMG zawiera aplikację, odnośnik do Applications oraz instrukcję aliasu na pulpicie. Nie jest to link do adresu HTTP: alias uruchamia pełną .app.

PyInstaller stosuje lokalny podpis ad-hoc; to nie jest podpis dystrybucyjny Developer ID. Do wydania publicznego potrzebny jest certyfikat Apple, podpisanie aplikacji odpowiednimi uprawnieniami, notaryzacja przez `xcrun notarytool` i stapling. Dane konta/certyfikatu przechowuj poza repozytorium. Skrypt nie usuwa quarantine i nie obchodzi Gatekeepera.

## Windows

Potrzebne Python, Node.js oraz Inno Setup 6 z ISCC.exe w PATH:

```bat
build-windows.bat
```

Wynik: `dist\TikoPlay\TikoPlay.exe` i `dist\installer\TikoPlay-2.0.0-test-setup.exe`. Instalacja per-user tworzy skróty na pulpicie i w menu Start. Dane w AppData nie należą do katalogu instalacji i pozostają po odinstalowaniu.

Przed aktualizacją zakończ program z traya. Podpis Authenticode i certyfikat dystrybucyjny muszą zostać dostarczone przez wydawcę; obecny build ma nazwę testową. Nie deklarujemy zweryfikowanego instalatora Windows bez wykonania builda i odbioru na Windows.

## Kontrola gotowej paczki

Uruchom z ikony na komputerze bez środowiska developerskiego. Sprawdź ponowne kliknięcie, otwarcie panelu, restart, zamknięcie z traya, konfigurację po aktualizacji i prawa do wysyłania klawiszy. Na macOS testuj tożsamość gotowej .app, nie tylko interpretera Python, ponieważ uprawnienia Dostępność są przypisane do aplikacji.

Paczki testowe nie powinny zastępować stabilnego wydania przed zakończeniem macierzy w WEB_UI_ACCEPTANCE.md.
