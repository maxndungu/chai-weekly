#!/usr/bin/env bash
# Builds the redesign from a git commit or branch into preview/, served at
# https://chaiweekly.co.ke/preview/ while the live site keeps its current design.
#   tools/build_preview.sh <commit-or-branch>
# The pages are hidden from search engines, carry a "preview" bar and are not linked from the live site.
# Additions made since the redesign was reverted live in tools/preview-patches/*.patch and are applied on top
# of <commit-or-branch> in order. The data files listed in LIVE_DATA keep their Liquid front matter, so GitHub
# Pages fills them from _data/ on every publish (the dashboard follows the Wednesday collector without a rebuild).
# tools/build_preview2.sh reuses this script for the test copy at /preview2/ by setting PREVIEW_DIR,
# PREVIEW_PATCHES and PREVIEW_BAR; with none of them set it builds the redesign preview as before.
set -euo pipefail
REF="${1:?usage: tools/build_preview.sh <commit-or-branch>}"
ROOT="$(git rev-parse --show-toplevel)"
DIR="${PREVIEW_DIR:-preview}"
PATCHES="${PREVIEW_PATCHES:-$ROOT/tools/preview-patches}"
export PREVIEW_BAR="${PREVIEW_BAR:-Preview of the new design, not yet published.}"
TMP="$(mktemp -d)"
# The live site's base path from _config.yml ("" on chaiweekly.co.ke); the preview sits under it at /preview/.
BASE="$(sed -n 's/^baseurl:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/p' "$ROOT/_config.yml" | head -1)"
BASE="${BASE%/}"
trap 'git -C "$ROOT" worktree remove --force "$TMP/src" >/dev/null 2>&1 || true; rm -rf "$TMP"' EXIT
git -C "$ROOT" worktree add -q --detach "$TMP/src" "$REF"
for p in "$PATCHES"/*.patch; do
  [ -e "$p" ] || continue
  git -C "$TMP/src" apply --whitespace=nowarn "$p" || { echo "could not apply $(basename "$p")" >&2; exit 1; }
done
# Built copies don't nest (preview2/ must not carry preview/ or an older preview2/), and only the live site has the domain.
rm -rf "$TMP/src/preview" "$TMP/src/preview2" "$TMP/src/CNAME"
# Build with the live data files, so pages that embed data at build time (the Auctions page) show current figures.
cp "$ROOT"/_data/*.csv "$ROOT"/_data/*.json "$TMP/src/_data/" 2>/dev/null || true
LIVE_DATA="assets/data/mombasa-sales.json assets/data/tea-trade.json"
[ -f "$ROOT/Gemfile.lock" ] && cp "$ROOT/Gemfile.lock" "$TMP/src/"
(cd "$TMP/src" && LANG=C.UTF-8 LC_ALL=C.UTF-8 bundle exec jekyll build -q --baseurl "$BASE/$DIR" -d "$TMP/out")
rm -f "$TMP/out/feed.xml" "$TMP/out/sitemap.xml" "$TMP/out/robots.txt"
python3 - "$TMP/out" "$BASE" "$DIR" <<'EOF'
import os, pathlib, re, sys
base, folder = sys.argv[2], sys.argv[3]
bar = ('<div style="background:#B98B4B;color:#173E32;font:600 14px/1.4 system-ui,sans-serif;'
       'padding:8px 16px;text-align:center">' + os.environ["PREVIEW_BAR"] + ' '
       '<a style="color:#173E32" href="' + base + '/">Go to the live site</a></div>')
for f in pathlib.Path(sys.argv[1]).rglob("*.html"):
    s = f.read_text(encoding="utf-8")
    s = s.replace("<head>", '<head>\n<meta name="robots" content="noindex, nofollow">', 1)
    s = s.replace(base + "/" + folder + "/feed.xml", base + "/feed.xml")  # the feed stays the live one
    s = re.sub(r"(<body[^>]*>)", r"\1" + bar, s, count=1)
    f.write_text(s, encoding="utf-8")
EOF
for f in $LIVE_DATA; do [ -f "$TMP/src/$f" ] && cp "$TMP/src/$f" "$TMP/out/$f"; done
rm -rf "${ROOT:?}/$DIR"
cp -r "$TMP/out" "$ROOT/$DIR"
echo "$DIR/ rebuilt from $REF ($(git -C "$ROOT" rev-parse --short "$REF"))"
