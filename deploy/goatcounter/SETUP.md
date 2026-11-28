# Website stats for chaiweekly.co.ke (about 10 minutes)

This counts readers on the website: how many people visit, which pages and issues they read, where they came
from (email, WhatsApp, Facebook, Google...), their country and device. It runs on your VPS next to the mailing
list, so the numbers stay yours and only you can see them. No cookies and no personal data are collected.

## 1. DNS (HostDeal, 2 minutes)

Add an **A** record: name `stats`, value: your VPS's IP address (the same one as `list`).

## 2. Start it on the VPS (5 minutes)

Log in to the VPS as root and paste:

```sh
mkdir -p ~/chai-stats && cd ~/chai-stats
for f in docker-compose.yml caddy-site-block.txt; do
  curl -fsSLO "https://raw.githubusercontent.com/maxndungu/chai-weekly/main/deploy/goatcounter/$f"
done
docker compose up -d
cp caddy-site-block.txt /opt/kazora/deploy/server/sites/chai-stats.caddy
docker exec kazora-caddy-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -1
```

If the last line says "Valid configuration", reload Caddy (kazora keeps running):

```sh
docker exec kazora-caddy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

## 3. Make your login (1 minute)

Put your own email address in place of `you@example.com`, paste, and type a password when it asks (twice):

```sh
docker exec -it chai-stats goatcounter db create site -vhost stats.chaiweekly.co.ke \
  -user.email you@example.com -db sqlite3+/home/goatcounter/goatcounter-data/goatcounter.sqlite3
```

## 4. Open it

Go to **https://stats.chaiweekly.co.ke** and log in. Counting starts as soon as the site update is merged
(`goatcounter_url` in `_config.yml`). Visits from the weekly email, WhatsApp and the social posts show up
under "Referrers" by name, because their links are tagged.

To back it up, add to the nightly cron (`crontab -e`):
`45 2 * * * docker run --rm -v chai-stats_stats-data:/d -v ~/chai-stats:/b alpine cp /d/goatcounter.sqlite3 /b/backup.sqlite3`
