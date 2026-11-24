# Setting up the Chai Weekly mailing list

This runs our own subscribe and send system (listmonk, free and open source) on your VPS.
Readers sign up on chaiweekly.co.ke, confirm by email, and every merged issue becomes an
email draft that you check and send yourself. Nothing is ever sent without you pressing Start.

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

Log in to the VPS (for example `ssh root@YOUR-VPS-IP`) and paste these lines one block at a time.

**a. Check nothing else is using the web ports.** If this prints anything, stop and send me the output:

```sh
sudo ss -tlnp | grep -E ':80 |:443 '
```

**b. Install Docker** (skip if `docker --version` already works):

```sh
curl -fsSL https://get.docker.com | sudo sh
```

**c. Get the files and set your passwords:**

```sh
mkdir -p ~/chai-list && cd ~/chai-list
for f in docker-compose.yml Caddyfile env.example backup.sh; do
  curl -fsSLO "https://raw.githubusercontent.com/maxndungu/chai-weekly/main/deploy/listmonk/$f"
done
chmod +x backup.sh
cp env.example .env
sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$(openssl rand -hex 24)/" .env
nano .env
```

In `nano`, change `ADMIN_PASSWORD` to your own password, then press
Ctrl+O, Enter, Ctrl+X.

**d. Start it:**

```sh
docker compose up -d
```

Wait a minute, then open **https://list.chaiweekly.co.ke/admin** and log in with the
`ADMIN_USER` and `ADMIN_PASSWORD` from `.env`. (If the page doesn't load, the DNS record from
step 2 may need up to an hour.)

**e. Nightly backup of the subscriber list:** run `crontab -e` and add this line:

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

## 6. A key for the weekly email drafts (5 minutes)

1. **Users > User roles > + New**: name it `Drafts`. Tick the permissions for
   **campaigns** (get and manage) and **lists** (get). Save.
2. **Users > + New**: type **API**, name `drafts`, role `Drafts`. Save, then copy the token it shows
   (it is shown once).
3. In GitHub: **maxndungu/chai-weekly > Settings > Secrets and variables > Actions > New repository secret**:
   - `LISTMONK_API_USER` = `drafts`
   - `LISTMONK_API_TOKEN` = the token you copied

Never paste the token into a chat, an issue or a file in the repository.

## 7. Each Wednesday

1. Merge the issue's pull request as usual (that publishes it on the site).
2. A minute later, open **https://list.chaiweekly.co.ke/admin > Campaigns**. The issue is there as a draft.
3. Open it, press **Send test** to your own address, look at it on your phone.
4. Press **Start campaign**. Done.

## Bringing in readers you already have

Only add people who agreed to receive Chai Weekly. **Subscribers > Import**, upload a CSV with
columns `email,name`, choose the Chai Weekly list, and pick **Subscribe** (or **Double opt-in**
to have each of them confirm first).

## If something goes wrong

- Restart: `cd ~/chai-list && docker compose restart`
- See what it says: `cd ~/chai-list && docker compose logs --tail 50 app`
- Update to a newer listmonk: change the version in `docker-compose.yml`, then `docker compose pull && docker compose up -d`
