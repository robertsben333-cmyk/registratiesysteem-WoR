# WoR Registratie

Lokale Windows-app voor registratie binnen Welzijn op Recept.

## Updates via GitHub

De app controleert standaard deze manifest-URL:

`https://raw.githubusercontent.com/robertsben333-cmyk/registratiesysteem-WoR/master/latest.json`

Als die URL niet bereikbaar is, valt de app terug op de lokale of meegebundelde `latest.json`.

In de verpakte Windows-app krijgt de gebruiker bij een nieuwe versie een melding in de app. Met `Update installeren` downloadt de app de release zelf, sluit kort af en start daarna opnieuw op. Er is dus geen handmatige browserdownload meer nodig.

## Releaseflow

1. Verhoog `APP_VERSION` in `app/version.py`.
2. Werk `latest.json` bij:
   - `version`
   - `min_supported_version`
   - `published_at`
   - `notes`
   - eventueel `windows.url`
3. Bouw een nieuwe Windows-release met PyInstaller.
4. Upload de build naar GitHub Releases in:
   `https://github.com/robertsben333-cmyk/registratiesysteem-WoR/releases`
5. Zorg dat `latest.json` verwijst naar het nieuwe releasebestand (`.zip` of `.exe`).
6. Commit en push de code inclusief `latest.json`.

## Aanbevolen releasebestand

Gebruik bij voorkeur een zip-bestand met de nieuwe `WoR Registratie.exe`, bijvoorbeeld:

`WoR-Registratie-0.1.0-windows.zip`

Als je een versie-specifieke downloadlink wilt gebruiken in `latest.json`, gebruik dan dit patroon:

`https://github.com/robertsben333-cmyk/registratiesysteem-WoR/releases/download/v0.1.0/WoR-Registratie-0.1.0-windows.zip`
