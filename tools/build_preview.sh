#!/usr/bin/env bash
# Builds the redesign from a git commit or branch into preview/, served at
# https://maxndungu.github.io/chai-weekly/preview/ while the live site keeps its current design.
#   tools/build_preview.sh <commit-or-branch>
# The pages are hidden from search engines, carry a "preview" bar and are not linked from the live site.
set -euo pipefail
REF="${1:?usage: tools/build_preview.sh <commit-or-branch>}"
ROOT="$(git rev-parse --show-toplevel)"
TMP="$(mktemp -d)"
trap 'git -C "$ROOT" worktree remove --force "$TMP/src" >/dev/null 2>&1 || true; rm -rf "$TMP"' EXIT
git -C "$ROOT" worktree add -q --detach "$TMP/src" "$REF"
[ -f "$ROOT/Gemfile.lock" ] && cp "$ROOT/Gemfile.lock" "$TMP/src/"
(cd "$TMP/src" && LANG=C.UTF-8 LC_ALL=C.UTF-8 bundle exec jekyll build -q --baseurl /chai-weekly/preview -d "$TMP/out")
rm -f "$TMP/out/feed.xml" "$TMP/out/sitemap.xml" "$TMP/out/robots.txt"
python3 - "$TMP/out" <<'EOF'
import pathlib, re, sys
bar = ('<div style="background:#B98B4B;color:#173E32;font:600 14px/1.4 system-ui,sans-serif;'
       'padding:8px 16px;text-align:center">Preview of the new design, not yet published. '
       '<a style="color:#173E32" href="/chai-weekly/">Go to the live site</a></div>')
for f in pathlib.Path(sys.argv[1]).rglob("*.html"):
    s = f.read_text(encoding="utf-8")
    s = s.replace("<head>", '<head>\n<meta name="robots" content="noindex, nofollow">', 1)
    s = s.replace("/chai-weekly/preview/feed.xml", "/chai-weekly/feed.xml")  # the feed stays the live one
    s = re.sub(r"(<body[^>]*>)", r"\1" + bar, s, count=1)
    f.write_text(s, encoding="utf-8")
EOF
rm -rf "$ROOT/preview"
cp -r "$TMP/out" "$ROOT/preview"
echo "preview/ rebuilt from $REF ($(git -C "$ROOT" rev-parse --short "$REF"))"
