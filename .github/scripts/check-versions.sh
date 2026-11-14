#!/usr/bin/env bash
# The three places a release number lives must agree, and a pushed tag must match them:
#   custom_components/tvhub/manifest.json, tvhub_addon/config.yaml and the newest "## [x.y.z]" in CHANGELOG.md.
# (A mismatch means the add-on pulls an old image, or the Release has no notes.)
set -euo pipefail
cd "$(dirname "$0")/../.."
M=$(python3 -c 'import json;print(json.load(open("custom_components/tvhub/manifest.json"))["version"])')
A=$(sed -n 's/^version: *"\{0,1\}\([^" ]*\)"\{0,1\} *$/\1/p' tvhub_addon/config.yaml | head -1)
C=$(sed -n 's/^## \[\([0-9][0-9.]*\)\].*/\1/p' CHANGELOG.md | head -1)
echo "manifest.json=$M  add-on config.yaml=$A  CHANGELOG(newest)=$C"
ok=1
[ "$M" = "$A" ] || { echo "::error::manifest.json ($M) and tvhub_addon/config.yaml ($A) differ"; ok=0; }
[ "$M" = "$C" ] || { echo "::error::CHANGELOG.md's newest section ($C) is not the manifest version ($M)"; ok=0; }
if [ "${GITHUB_REF_TYPE:-}" = "tag" ]; then
  T="${GITHUB_REF_NAME#v}"; echo "tag=$T"
  [ "$T" = "$M" ] || { echo "::error::tag v$T does not match the version in manifest.json ($M)"; ok=0; }
fi
[ "$ok" = 1 ] || exit 1
echo "versions OK"
