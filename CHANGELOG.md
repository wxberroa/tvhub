# Changelog

All notable changes to TVHub. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/). The text of each version is what its GitHub Release shows.

Write new entries under **Unreleased**. To release: rename that heading to `## [X.Y.Z] - YYYY-MM-DD`, bump the version
in `custom_components/tvhub/manifest.json` and `tvhub_addon/config.yaml`, and push the tag `vX.Y.Z`. CI checks that those versions, the CHANGELOG and the tag agree (`.github/scripts/check-versions.sh`).

## [Unreleased]

### Added
- LG webOS: play a media URL on the TV (`POST /api/tvs/{id}/play`). The Home Assistant integration now supports `media_player.play_media` for LG TVs (URLs and media-source ids). It opens the TV's media viewer, with the browser as a fallback; what plays depends on the TV model. Experimental.

### Changed
- Users list: accounts that sign in through Home Assistant (`ha_login`) are tagged "Home Assistant" and have no "reset password" button, since they have no TVHub password.

## [0.9.0] - 2026-11-15

### Added
- Add-on option `ha_login` (off by default): sign in on the direct port with a Home Assistant username and password, checked by the Supervisor. Role `user` only; never matches an existing TVHub account.

### Changed
- Direct port of the add-on: the first-run screen now explains that users can be created from the sidebar panel (or with the code in the add-on's Log tab) instead of mentioning `docker compose`; with `ha_login` on it shows the sign-in form, because Home Assistant accounts work before any local admin exists.
- Home Assistant brand: `logo.png` now has dark lettering for light themes, and `dark_logo.png` keeps the white one for dark themes.
- CI: `docker/setup-qemu-action` v4.

## [0.8.5] - 2026-11-14

### Added
- Automated tests (pytest) for password rules, security headers, PWA routes and the first-run setup/login flow, run in CI.

### Changed
- The "TVHub detected" card in Home Assistant now says what it is adding: the add-on address and the list of TVs that will become media players.
- Dependencies: `aiowebostv` 1.x (LG webOS, verified on a real TV), minimum `aiohttp` 3.14.5, `paho-mqtt` 2.2.0 and `argon2-cffi` 25.1; CI actions (`checkout`, `docker/*`) updated.

## [0.8.4] - 2026-11-14

### Added
- Installable web app (PWA): manifest, icons and a service worker, so TVHub can be added to a phone's home screen and opens full screen. The service worker caches nothing; it only shows a "Retry" page when the server is unreachable. The favicon now follows the new logo.
- Add-on watchdog: the Supervisor restarts TVHub if it stops answering.
- The add-on's Configuration tab shows readable names and descriptions (English and Spanish) for its options.
- CI guard: a pull request fails if `manifest.json`, the add-on `config.yaml` and the newest CHANGELOG section differ, and a release tag that does not match them stops before building the image.
- `SECURITY.md` (private vulnerability reporting), issue templates and Dependabot updates.

## [0.8.3] - 2026-11-13

### Changed
- The project moved from the GitHub account `xavilitoh` to `wxberroa`. The container image is now `ghcr.io/wxberroa/tvhub` (the old name does not redirect), and the repository, add-on, HACS and website links point to the new account. See the README for how to update.

### Changed
- New logo and icons ("the wall": four screens, one active) in coral, with a light-background variant; favicon and touch icon for the landing.
- Accent colour is now coral `#f5654a` (was blue) in the web app and the landing page; new demo GIF.

### Added
- Landing page (`docs/index.html`, English / Español) for GitHub Pages.

## [0.8.2] - 2026-11-13

### Fixed
- Add-on: the integration could not connect through the direct port ("requires a valid API token") while no TVHub administrator existed, which is always the case when you only use Ingress. A valid API token now works even before the first administrator is created; everything else still waits for it.

## [0.8.1] - 2026-11-13

### Fixed
- The integration now offers **TVHub discovered** even when another TVHub server is already configured (e.g. one in a separate Docker); it is only skipped when that same server is already set up.

## [0.8.0] - 2026-11-13

### Added
- Add-on: announces itself to Home Assistant (Supervisor discovery) with an API token, so the TVHub integration shows **TVHub discovered** and needs no IP or token typed by hand. The integration accepts that discovery (`async_step_hassio`).
- Add-on option **install_integration** (off by default): copies the integration, bundled in the image, to `/config/custom_components/tvhub`; never overwrites a HACS or manual install.

## [0.7.3] - 2026-11-12

### Added
- Add-on: when the Mosquitto broker add-on is installed, TVHub reads its login from the Supervisor on the first start and connects to MQTT by itself. A new **Usar el broker de Home Assistant** button in the Home Assistant dialog does the same later. An external broker is still filled in by hand; settings you saved always win.

## [0.7.2] - 2026-11-12

### Fixed
- Inside Home Assistant (Ingress) the sign-in and status calls ignored the Ingress path prefix, so the page showed the login form with "No se pudo contactar con el servidor" instead of opening. They now use the prefix like every other request.

## [0.7.1] - 2026-11-12

### Added
- CI publishes `ghcr.io/wxberroa/tvhub:dev` on every push to `dev` (never `latest`), and a hidden **TVHub (dev)** add-on (Advanced mode) runs it next to the stable one.
- Add-on option **port** (Configuration tab) to choose the port for direct access instead of the fixed 8080. Ingress now uses its own fixed port (8099), so it keeps working whatever you choose.

### Changed
- The log now states whether Ingress mode is on at startup and, once, why an Ingress request was not trusted (peer address).
- README and add-on docs: one-click button to add the add-on repository to Home Assistant.

## [0.7.0] - 2026-11-12

### Added
- **Home Assistant add-on** (HA OS / Supervised): add `https://github.com/wxberroa/tvhub` as a repository and TVHub opens from the sidebar through Ingress. Home Assistant signs you in, so there is no TVHub login there; direct access on port 8080 keeps the normal login.
- `TVHUB_AUTH=ingress` mode: the login is skipped only for connections from the Supervisor (`172.30.32.2`) carrying `X-Ingress-Path`, and only when the Supervisor also provided `SUPERVISOR_TOKEN`. Browser writes are checked against the Home Assistant origin.
- Release notes are now taken from this file.
- `docs/demo-src`: scripts that regenerate the README demo against simulated TVs.

### Changed
- The UI works under a path prefix (Ingress), including the WebSockets, app icons and screenshot download.
- Security headers allow framing by the same origin only in Ingress mode; the standalone image keeps `X-Frame-Options: DENY`.
- New README demo GIF showing the current interface.

## [0.6.1] - 2026-11-03

### Changed
- More robust Home Assistant remote card.
- Warning about VIDAA keys that the TV ignores.
- Agent folders are ignored by git.

## [0.6.0] - 2026-11-02

### Added
- CI creates the GitHub Release when a tag is pushed (HACS only reads Releases, not bare tags).

## [0.5.0] - 2026-11-02

### Added
- Roku, Samsung Tizen and Sony Bravia drivers (experimental: tested against simulators only).
- Settings in the top bar and on each wall tile; add and search TVs from the wall.
- Android TV opens apps with `am start`.

### Changed
- Apple-style design with a slide-out menu; menu and GitHub button always visible.

## [0.4.0] - 2026-11-02

### Added
- **Security**: user accounts (Argon2id), server-side sessions, CSRF protection, brute-force lockouts, API tokens for integrations and an audit log.
- Languages: English, Español, Português, Français, Deutsch.
- The wall of TVs is the home page.

## [0.3.0] - 2026-11-01

### Added
- Wall view: all TVs at once, with a screenshot for each Android TV.
- Docker image published to GHCR (amd64 and arm64).
- Demo animation in the README.

## [0.2.0] - 2026-11-01

### Added
- Remote card for Home Assistant dashboards and the `tvhub.send_key` service.

## [0.1.1] - 2026-11-01

### Changed
- Brand icons.

## [0.1.0] - 2026-11-01

### Added
- First release: control Android TV / Fire TV (live screen over ADB), LG webOS and Hisense VIDAA from the browser, with a Home Assistant bridge over MQTT.

[Unreleased]: https://github.com/wxberroa/tvhub/compare/v0.8.3...HEAD
[0.8.3]: https://github.com/wxberroa/tvhub/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/wxberroa/tvhub/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/wxberroa/tvhub/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/wxberroa/tvhub/compare/v0.7.3...v0.8.0
[0.7.3]: https://github.com/wxberroa/tvhub/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/wxberroa/tvhub/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/wxberroa/tvhub/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/wxberroa/tvhub/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/wxberroa/tvhub/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/wxberroa/tvhub/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/wxberroa/tvhub/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/wxberroa/tvhub/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/wxberroa/tvhub/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/wxberroa/tvhub/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/wxberroa/tvhub/compare/v0.1.0...v0.1.1
