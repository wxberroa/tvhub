# Security policy

TVHub controls devices on your home network and ships a login system, so security reports are welcome.

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private reporting instead:
<https://github.com/wxberroa/tvhub/security/advisories/new>

Include the version (see `CHANGELOG.md`), how you run it (Docker, Home Assistant add-on, native) and steps to reproduce.
You will get a first answer within a few days; fixes ship as a patch release with a note in the CHANGELOG.

## Supported versions

Only the latest release receives fixes.

## Scope notes

- TVHub is meant for a trusted LAN. If you expose it to the internet, put it behind HTTPS and keep login enabled.
- Inside the Home Assistant add-on, access is delegated to Home Assistant (Ingress); the direct port still requires TVHub's own login.
