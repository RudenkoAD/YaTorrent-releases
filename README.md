# YaTorrent releases

Public installers for YaTorrent, the AIM2 desktop worker for macOS 13+ on Apple Silicon.

Download the latest DMG from [Releases](https://github.com/RudenkoAD/YaTorrent-releases/releases/latest), copy YaTorrent to Applications, and import the `.aim2` connection profile supplied by your administrator. Profiles and credentials are not distributed here.

From version 0.2.8 onward, updates are available inside **Worker → Обновление приложения**. Downloading an update does not stop work. Stop the worker before installing and relaunching the app.

The app uses an ad-hoc signature and is not Apple-notarized. macOS may require **System Settings → Privacy & Security → Open Anyway** for a trusted first installation, and may ask again for Keychain access after an update. Do not disable Gatekeeper.

Each release includes `SHA256SUMS.txt`. The updater also checks the GitHub asset digest, archive structure, bundle identity, architecture, and signature integrity.

This repository contains installers and release information. Source development, task data, connection profiles, and secrets are maintained separately.
