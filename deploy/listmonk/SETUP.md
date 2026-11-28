# Setting up the Chai Weekly mailing list

This runs our own subscribe and send system (listmonk, free and open source) on your VPS.
Readers sign up on chaiweekly.co.ke, confirm by email, and get the latest issue straight away.
Every merged issue is emailed to the list 15 minutes after the merge (you can pause it in that time).

Emails go out through your chaiweekly.co.ke mailbox at StackMail. Its limits (20i, the company
behind StackCP): about 2,000 different recipients a day and 8,000 messages a day per mailbox,
and a **new** mailbox can only send 50 a day for its first 7 days. That is plenty for now.
If the list grows past about 1,500 readers, we switch the sending to a bulk email service
(for example Amazon SES, about $1 per 10,000 emails) in listmonk's settings. Nothing else changes.

It takes about 45 minutes. Each step says where to do it.

---

## 1. Make a mailbox for the newsletter (StackCP, 5 minutes)

1. Log in to StackCP (HostDeal) and open **Email** for chaiweekly.co.ke.
2. Create a mailbox called **newsletter@chaiweekly.co.ke** and give it a strong password.
   Do this first: the 7-day "new mailbox" limit starts counting now.
3. In the same Email area, look for **DKIM** or **Email security**. If it is off, turn it on.
   If it shows a DKIM record to copy, keep that page open for step 2.

## 2. DNS records (StackCP / HostDeal DNS, 5 minutes)

Add these in the DNS settings for chaiweekly.co.ke. Leave the existing GitHub Pages and mail records as they are.

| Type | Name | Value |
|------|------|-------|
| A | `list` | your VPS's IP address |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:newsletter@chaiweekly.co.ke` |
| TXT | (the DKIM name StackCP shows, if any) | (the DKIM value StackCP shows) |

The SPF record you already have for StackMail stays as it is.

## 3. Install on the VPS (15 minutes)

Your VPS already runs Caddy (the `kazora-caddy-1` container) for your other app, and it owns the
web ports. The list runs next to it with its own separate database, and that same Caddy gives
list.chaiweekly.co.ke its address and certificate. Nothing of kazora's is changed except one
short block added at the end of its Caddyfile.

Log in to the VPS as root and paste each block, one at a time.

**a. Find the Caddy network and Caddyfile.**

```sh
docker inspect kazora-caddy-1 --format '{{range $k, $v := .NetworkSettings.Networks}}NETWORK: {{$k}}{{"\n"}}{{end}}'
docker inspect kazora-caddy-1 --format '{{range .Mounts}}{{.Source}}  ->  {{.Destination}}{{"\n"}}{{end}}'
```

Write down:
- the name after `NETWORK:` (for example `kazora_default`);
- the line that ends in `-> /etc/caddy/Caddyfile`. The part before the arrow is the Caddyfile on the VPS.
  (If you only see `-> /etc/caddy`, the Caddyfile is the folder before the arrow plus `/Caddyfile`.)

**b. Get the list's files and make the password file:**

```sh
mkdir -p ~/chai-list && cd ~/chai-list
for f in docker-compose.yml caddy-site-block.txt env.example backup.sh; do
  curl -fsSLO "https://raw.githubusercontent.com/maxndungu/chai-weekly/main/deploy/listmonk/$f"
done
chmod +x backup.sh
cp env.example .env
sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$(openssl rand -hex 24)/" .env
nano .env
```

In `nano`: change `ADMIN_PASSWORD` to your own password, and `PROXY_NETWORK` to the network name
from step a. Save with Ctrl+O, Enter, then Ctrl+X.

**c. Start the list:**

```sh
docker compose up -d
docker compose ps
```

You should see `chai-listmonk` and `listmonk-db`, both "Up" (the first start takes about a minute).

**d. Tell Caddy about the list.**

On Maxwell's VPS the kazora Caddyfile already reads every `*.caddy` file in
`/opt/kazora/deploy/server/sites`, so the list gets its own file there and the main Caddyfile is not edited:

```sh
cp ~/chai-list/caddy-site-block.txt /opt/kazora/deploy/server/sites/chai-list.caddy
docker exec kazora-caddy-1 wget -qO- http://chai-listmonk:9000/health; echo
docker exec kazora-caddy-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -2
docker exec kazora-caddy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile   # only if it said "Valid configuration"
```

On a server whose Caddyfile has no `import .../sites/*.caddy` line, add the block to the Caddyfile itself.
Put your Caddyfile path from step a in the first line, then paste:

```sh
CADDYFILE=/the/path/from/step/a/Caddyfile
cp "$CADDYFILE" "$CADDYFILE.before-list"
cat ~/chai-list/caddy-site-block.txt >> "$CADDYFILE"
docker exec kazora-caddy-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

If the last line ends with "Valid configuration", reload Caddy. Kazora keeps running:

```sh
docker exec kazora-caddy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

If it shows an error instead, put the old file back with `cp "$CADDYFILE.before-list" "$CADDYFILE"`
and send me the error. Kazora is unaffected because nothing was reloaded.

**e. Open the list.** Go to **https://list.chaiweekly.co.ke/admin** and log in with `ADMIN_USER` and
`ADMIN_PASSWORD` from `.env`. If the page doesn't load yet, the DNS record from step 2 may need
up to an hour. Caddy gets the certificate on its own once the DNS record works.

**f. Nightly backup of the subscriber list:** run `crontab -e` and add this line at the bottom:

```
30 2 * * * cd ~/chai-list && ./backup.sh
```

## 4. Settings inside listmonk (10 minutes)

Go to **Settings**:

- **General**
  - Root URL: `https://list.chaiweekly.co.ke`
  - Default 'from' email: `Chai Weekly <newsletter@chaiweekly.co.ke>`
  - Tick **Enable public subscription page**
- **SMTP**: edit the first server (delete any others)
  - Host `smtp.stackmail.com`, Port `465`, TLS: **TLS**, Auth protocol: **login**
  - Username `newsletter@chaiweekly.co.ke`, Password: the mailbox password
  - Max. connections `2`
  - Press **Test connection**, then Save
- **Performance**
  - Sliding window: on, Duration `1h`, Rate `300`
    (keeps us well inside StackMail's limits; for the first 7 days of the new mailbox use Rate `40`)
- **Security**
  - Trusted URLs: add `https://chaiweekly.co.ke/subscribe/thanks/`
    (this sends new readers back to our "check your email" page)
  - Leave captcha off (the site form has its own spam trap, and every sign-up must be confirmed by email)

## 5. Make the list (2 minutes)

**Lists > + New**:
- Name: `Chai Weekly`
- Type: **Public**
- Optin: **Double** (each reader confirms by email, so nobody is added without agreeing)

Open the new list and note two things: its **number** (e.g. `#3`, shown as ID) and its long
**UUID**. Send both to me, or put them in `_config.yml` as `listmonk_list_id` and
`listmonk_list_uuid`. The Subscribe box on the site switches on as soon as the UUID is in.

## 6. A key for the weekly emails (5 minutes)

1. **Users > User roles > + New**: name it `Drafts`. Tick the permissions for
   **campaigns** (get, manage and send), **lists** (get), **templates** (get and manage),
   **subscribers** (get and manage) and **tx** (send). Save.
   (Templates lets each issue use the Chai Weekly newspaper design; send lets a merged issue go out
   on its own; subscribers and tx let new readers get the welcome email.)
2. **Users > User roles > List roles > + New**: name it `Chai list`, add the **Chai Weekly** list and
   tick **get** and **manage**. Save. (Needed to note on each reader that they had the welcome email.)
3. **Users > + New**: type **API**, name `drafts`, user role `Drafts`, list role `Chai list`. Save, then copy
   the token it shows (it is shown once). If the `drafts` user already exists, just edit it and set the
   list role; the token stays the same.
4. In GitHub: **maxndungu/chai-weekly > Settings > Secrets and variables > Actions > New repository secret**:
   - `LISTMONK_API_USER` = `drafts`
   - `LISTMONK_API_TOKEN` = the token you copied

Never paste the token into a chat, an issue or a file in the repository.

## 7. Each Wednesday

1. Merge the issue's pull request as usual. That publishes it on the site, and that is your approval.
2. A minute later the issue is in **https://list.chaiweekly.co.ke/admin > Campaigns**, scheduled to send
   15 minutes after the merge (`listmonk_autosend_minutes` in `_config.yml`).
3. Nothing else to do. If you spot a problem in those 15 minutes, open the campaign and press **Pause**.
   To go back to pressing Start yourself every week, empty `listmonk_autosend_minutes`.

The same merge also puts the issue into the **welcome email**. Every 10 minutes (step 8), anyone who has
confirmed their subscription since `welcome_since` (in `_config.yml`) and has not had it yet is sent the
latest issue once, with a short welcome note at the top. The reader gets a note in listmonk
(attribute `chai_welcomed` with the date), so nobody gets it twice. To turn welcomes off, empty `welcome_since`.

## 8. Welcome emails on time (VPS, 3 minutes)

New readers get the latest issue from a small job on the VPS that runs every 10 minutes.
Log in to the VPS as root and paste:

```sh
cd ~/chai-list
curl -fsSLO https://raw.githubusercontent.com/maxndungu/chai-weekly/main/deploy/listmonk/welcome.sh
chmod +x welcome.sh
printf 'LISTMONK_API_USER=drafts\nLISTMONK_API_TOKEN=\n' > welcome.env
chmod 600 welcome.env
nano welcome.env
```

In `nano`, put the `drafts` token after `LISTMONK_API_TOKEN=` (the same token that is in GitHub's secrets; if you no longer
have it, open **Users > drafts** in listmonk and make a new one, then put the new one in GitHub too).
Save with Ctrl+O, Enter, then Ctrl+X. Then check it works and switch it on:

```sh
./welcome.sh
(crontab -l 2>/dev/null; echo '*/10 * * * * cd ~/chai-list && ./welcome.sh >> welcome.log 2>&1') | crontab -
```

The first command should end with "Welcome email sent to 0 new reader(s)." (or a number). To see later runs:
`tail -20 ~/chai-list/welcome.log`.

## 9. Sign-ups for the detailed auction statistics (15 minutes)

The detailed statistics (on the test copy at /preview2/auctions/ for now) open to readers who give their name,
email, company and what they do in tea. A small helper on the VPS puts them on their own list in listmonk.

1. **Lists > + New**: name `Auction data`, type **Private**, optin **Double**. Note its number (e.g. `#5`).
2. **Users > User roles > List roles**: open `Chai list` and add the **Auction data** list with **get** and **manage**.
3. On the VPS as root:

```sh
cd ~/chai-list
RAW=https://raw.githubusercontent.com/maxndungu/chai-weekly/main/deploy/datasignup
curl -fsSL $RAW/signup.py -o signup.py
curl -fsSL $RAW/docker-compose.yml -o datasignup-compose.yml
printf 'LISTMONK_API_USER=drafts\nLISTMONK_API_TOKEN=\nDATA_LIST_ID=\nNEWS_LIST_ID=3\n' > datasignup.env
chmod 600 datasignup.env
nano datasignup.env     # paste the drafts token and the Auction data list number
docker compose -p chai-datasignup -f datasignup-compose.yml --env-file .env up -d
```

4. In the Caddy site file for the list (`/opt/kazora/deploy/server/sites/chai-list.caddy`), replace the
   `reverse_proxy chai-listmonk:9000` line with:

```
	reverse_proxy /data-signup chai-datasignup:8080
	reverse_proxy chai-listmonk:9000
```

   then reload Caddy as in step 3. Each sign-up shows in listmonk under the Auction data list, with the company
   and role on the reader's record (attributes `data_company`, `data_role`). `docker logs chai-datasignup` shows
   only "sign-up: ok/bad/error", never names or emails.

## Bringing in readers you already have

Only add people who agreed to receive Chai Weekly. **Subscribers > Import**, upload a CSV with
columns `email,name`, choose the Chai Weekly list, and pick **Subscribe** (or **Double opt-in**
to have each of them confirm first).

## If something goes wrong

- Restart the list: `cd ~/chai-list && docker compose restart`
- See what it says: `cd ~/chai-list && docker compose logs --tail 50 app`
- Update to a newer listmonk: change the version in `docker-compose.yml`, then `docker compose pull && docker compose up -d`
