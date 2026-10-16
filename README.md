# YaTorrent releases

Public installers for YaTorrent, the AIM2 desktop worker for macOS 13+ on Apple Silicon.

Download the latest DMG from [Releases](https://github.com/RudenkoAD/YaTorrent-releases/releases/latest), copy YaTorrent to Applications, and import the `.aim2` connection profile supplied by your administrator. Profiles and credentials are not distributed here.

From version 0.2.8 onward, updates are available inside **Worker → Обновление приложения**. Downloading an update does not stop work. Stop the worker before installing and relaunching the app.

The app uses an ad-hoc signature and is not Apple-notarized. macOS may require **System Settings → Privacy & Security → Open Anyway** for a trusted first installation, and may ask again for Keychain access after an update. Do not disable Gatekeeper.

Each release includes `SHA256SUMS.txt`. The updater also checks the GitHub asset digest, archive structure, bundle identity, architecture, and signature integrity.

This repository contains installers and release information. Source development, task data, connection profiles, and secrets are maintained separately.


## Agent skills for AIM2

The [`skills/`](skills/) directory contains skills for using AIM2 through its
HTTP API. They work without the private AIM2 source tree, SSH, database access,
or a broker connection. They do not configure the GUS/YaTorrent desktop worker.
Instructions are in Russian; the API helper requires Python 3.10+ and has no
third-party dependencies.

| Skill | Use it for |
| --- | --- |
| [aim2-api](skills/aim2-api/SKILL.md) | Connection, authentication, API client and workflow routing |
| [aim2-api-baskets](skills/aim2-api-baskets/SKILL.md) | Query baskets, revision-safe edits, import/export |
| [aim2-api-experiments](skills/aim2-api-experiments/SKILL.md) | Experiment definitions, explicit launches and progress |
| [aim2-api-crons](skills/aim2-api-crons/SKILL.md) | Schedules, activation, manual runs and history |
| [aim2-api-results](skills/aim2-api-results/SKILL.md) | SERPset downloads, organic URLs and available HTML artifacts |

Install all five folders together into your agent's skills directory, preserving
the folder names and their relative layout. For Codex, this is typically
`~/.codex/skills/`; for a project installation, `.agents/skills/`. Restart or
reload the agent after installation. Existing development skills named
`aim2-baskets` and similar can coexist with this `aim2-api-*` package. Review an
existing folder before replacing it.

For Codex with the built-in skill installer, ask:

> Install all five skills from RudenkoAD/YaTorrent-releases under skills/:
> aim2-api, aim2-api-baskets, aim2-api-experiments, aim2-api-crons, aim2-api-results.

Supply your own installation URL and a private local token file; credentials and
connection profiles are never included in this repository. Start with
[connection setup](skills/aim2-api/SKILL.md). Then ask naturally, for example:

- «Создай корзину из этого списка, сохрани повторы и регионы».
- «На корзине 123 запусти сравнение этих двух конфигов и скачай результаты».
- «Собирай эту корзину по будням в 09:00 Europe/Moscow, без параллельных запусков».
- «Скачай JSON и органические ссылки запуска 456, отдельно укажи ошибки».

Creating an experiment definition does not start a capture. Enabling a cron
allows future scheduled runs. Downloads may contain partial results; the skills
require reporting capture errors and postprocessing status separately. HTML
availability depends on artifact storage access and retention.

The API contracts were checked against AIM2 source on 2026-10-16; deployed
installations may differ. Check the selected installation's runtime and schema.
Local helper checks (fake loopback HTTP only, no AIM2 requests):

```sh
python3 -m unittest discover -s tests -v
```
