#!/usr/bin/env bash
#
# sync-skills.sh — kopiert die kanonischen Skills aus skills/ in die
# tool-spezifischen Ordner für Claude Code und Codex.
#
# Kopieren statt Symlinks, weil Claude Code in .claude/skills/ interne Dateien
# ablegt; bei Symlinks würde das in die Quelle zurückschreiben.
#
# Usage:
#   ./scripts/sync-skills.sh            # synct nach .claude/skills und .codex/skills
#   ./scripts/sync-skills.sh --check    # prüft nur, ob Targets aktuell sind (CI)

set -euo pipefail

# Repo-Root bestimmen (egal von wo aufgerufen)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$ROOT"

SRC="skills"
TARGETS=(".claude/skills" ".codex/skills")

if [ ! -d "$SRC" ]; then
  echo "error: '$SRC/' nicht gefunden — vom Repo-Root ausführen." >&2
  exit 1
fi

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

# Skill-Ordner einsammeln (alles in skills/ außer README.md auf Top-Level)
shopt -s nullglob
have_skill=0
for entry in "$SRC"/*/; do
  have_skill=1
  break
done
if [ "$have_skill" -eq 0 ]; then
  echo "warn: keine Skills in '$SRC/' gefunden — nichts zu syncen."
  exit 0
fi

sync_one() {
  local target="$1"
  if [ "$CHECK" -eq 1 ]; then
    local tmp
    tmp="$(mktemp -d)"
    cp -r "$SRC"/*/ "$tmp"/ 2>/dev/null || true
    if [ ! -d "$target" ] || ! diff -rq "$tmp" "$target" >/dev/null 2>&1; then
      echo "out-of-date: $target (sync-skills.sh ausführen)" >&2
      rm -rf "$tmp"
      return 1
    fi
    rm -rf "$tmp"
    echo "ok: $target"
    return 0
  fi

  rm -rf "$target"
  mkdir -p "$target"
  cp -r "$SRC"/*/ "$target"/
  echo "synced: $SRC/ -> $target"
}

rc=0
for t in "${TARGETS[@]}"; do
  sync_one "$t" || rc=1
done

exit "$rc"
