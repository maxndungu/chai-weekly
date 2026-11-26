#!/bin/sh
# Sends each new subscriber the latest issue once (the welcome email). Runs on the VPS from cron every 10 minutes:
#   */10 * * * * cd ~/chai-list && ./welcome.sh >> welcome.log 2>&1
# Needs welcome.env next to it with the listmonk API user and token (see SETUP.md, step 8). Never commit that file.
# Each run fetches the latest tools/welcome.py and settings (_config.yml) from the repository, so nothing here needs updating.
set -e
cd "$(dirname "$0")"
[ -f welcome.env ] || { echo "welcome.env is missing: see SETUP.md step 8"; exit 1; }
set -a; . ./welcome.env; set +a
RAW=https://raw.githubusercontent.com/maxndungu/chai-weekly/main
mkdir -p .welcome
curl -fsSL "$RAW/tools/welcome.py" -o .welcome/welcome.py
curl -fsSL "$RAW/_config.yml" -o .welcome/config.yml
cfg() { sed -n "s/^$1:[[:space:]]*\"\{0,1\}\([^\"#]*\).*/\1/p" .welcome/config.yml | head -1 | tr -d ' '; }
LISTMONK_URL=$(cfg listmonk_url) LISTMONK_LIST_ID=$(cfg listmonk_list_id) WELCOME_SINCE=$(cfg welcome_since)
export LISTMONK_URL LISTMONK_LIST_ID WELCOME_SINCE
echo "--- $(date '+%F %T')"
# flock stops two runs overlapping (so nobody is sent the welcome twice).
if command -v python3 >/dev/null 2>&1; then
  exec flock -n .welcome/lock python3 .welcome/welcome.py
else
  exec flock -n .welcome/lock docker run --rm -e LISTMONK_URL -e LISTMONK_LIST_ID -e WELCOME_SINCE -e LISTMONK_API_USER -e LISTMONK_API_TOKEN \
    -v "$PWD/.welcome:/w:ro" python:3.12-alpine python3 /w/welcome.py
fi
