#!/usr/bin/env bash
# Builds the test copy of the live site into preview2/, served at https://chaiweekly.co.ke/preview2/.
# This is where new features (first: detailed auction statistics behind a free sign-up) are tried
# before they reach the live site. It is a copy of the live site as it is on main, plus the changes in
# tools/preview2-patches/*.patch applied in order. Hidden from search engines, not linked from the
# live site, carries a "test copy" bar, and visits to it are not counted in the reader stats.
#   tools/build_preview2.sh            # from main
#   tools/build_preview2.sh <commit>   # from another commit or branch
# Rebuild after a patch changes, or when the live site has changed and the copy should catch up.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
PREVIEW_DIR=preview2 \
PREVIEW_PATCHES="$ROOT/tools/preview2-patches" \
PREVIEW_BAR="Test copy of Chai Weekly for new features, not public." \
  exec "$ROOT/tools/build_preview.sh" "${1:-main}"
