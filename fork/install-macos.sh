#!/usr/bin/env bash
# Installs the latest successful Fork Build of fork-main into /Applications.
# Files fetched by gh carry no quarantine flag, so the ad-hoc signed app opens without a
# Gatekeeper prompt; a browser download of the same dmg would be blocked.
set -euo pipefail

repo=lovefleuret/clash-verge-fork
app="/Applications/Clash Verge.app"

case "$(uname -m)" in
  arm64) artifact=clash-verge-macos_arm64 ;;
  *) artifact=clash-verge-macos_x64 ;;
esac

run_id=$(gh run list --repo "$repo" --workflow fork-build.yml --branch fork-main \
  --status success --limit 1 --json databaseId --jq '.[0].databaseId')
if [ -z "$run_id" ]; then
  echo "No successful Fork Build on fork-main" >&2
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
gh run download "$run_id" --repo "$repo" --name "$artifact" --dir "$tmp"

mount="$tmp/mount"
hdiutil attach "$tmp"/*.dmg -nobrowse -readonly -mountpoint "$mount" >/dev/null
trap 'hdiutil detach "$mount" -quiet || true; rm -rf "$tmp"' EXIT

osascript -e 'quit app "Clash Verge"' >/dev/null 2>&1 || true
for _ in {1..15}; do
  pgrep -x clash-verge >/dev/null || break
  sleep 1
done
if pgrep -x clash-verge >/dev/null; then
  echo "Clash Verge is still running; quit it and run this script again" >&2
  exit 1
fi

rm -rf "$app"
ditto "$mount/Clash Verge.app" "$app"
open "$app"
echo "Installed Fork Build run $run_id"
