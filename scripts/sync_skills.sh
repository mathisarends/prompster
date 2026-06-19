#!/usr/bin/env bash
#
# sync_skills.sh — synct die kanonischen Agent-Skills für alle Coding-Agents.
#
# Kanonische Quelle: .agents/skills/  (committet)
#   Dieser Pfad ist die ökosystem-weite Konvention und wird von den meisten
#   Tools NATIV gelesen — es muss nichts gesynct werden für:
#     - Codex CLI ........ läuft den Verzeichnisbaum hoch und scannt .agents/skills/
#     - GitHub Copilot ... liest .agents/skills/ (und .claude/skills/) direkt
#     - Cursor / Gemini .. lesen .agents/skills/ direkt
#
# Einziger Ausreißer: Claude Code liest ausschließlich .claude/skills/ und
# kennt keinen konfigurierbaren Pfad. Deshalb ist .claude/skills das einzige
# Sync-Target. (Feature-Request für .agents/-Support: anthropics/claude-code#56193 —
# sobald gemerged, kann dieses Script ersatzlos entfallen.)
#
# Kopieren statt Symlinks, weil:
#   1. Claude Code legt in .claude/skills/ interne Dateien ab; bei Symlinks
#      würde das in die Quelle (.agents/skills) zurückschreiben.
#   2. Symlinks werden in git/CI/cross-platform schlecht unterstützt.
#
# Usage:
#   ./scripts/sync_skills.sh            # synct .agents/skills -> .claude/skills
#   ./scripts/sync_skills.sh --check    # prüft nur, ob das Target aktuell ist (CI)

set -euo pipefail

# Repo-Root bestimmen (egal von wo aufgerufen)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$ROOT"

SRC=".agents/skills"
TARGETS=(".claude/skills")

if [ ! -d "$SRC" ]; then
  echo "error: '$SRC/' nicht gefunden — vom Repo-Root ausführen." >&2
  exit 1
fi

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

# Skill-Ordner einsammeln (alle Unterordner in .agents/skills/)
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

  # Edge-Case: niemals in die Quelle selbst syncen (falls ein Target je auf
  # .agents/skills zeigt). Schützt die committete Source vor Selbst-Überschreiben.
  if [ "$(cd "$target" 2>/dev/null && pwd || echo "$target")" = "$(cd "$SRC" && pwd)" ]; then
    echo "skip: '$target' ist die Quelle selbst — nichts zu tun."
    return 0
  fi

  if [ "$CHECK" -eq 1 ]; then
    local tmp
    tmp="$(mktemp -d)"
    cp -r "$SRC"/*/ "$tmp"/ 2>/dev/null || true
    if [ ! -d "$target" ] || ! diff -rq "$tmp" "$target" >/dev/null 2>&1; then
      echo "out-of-date: $target (scripts/sync_skills.sh ausführen)" >&2
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
