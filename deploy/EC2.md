# Deploying to EC2

One server runs two containers: **app** (Flask + gunicorn) and **Caddy** in front of it on ports 80/443.
Caddy gets a free HTTPS certificate on its own once a domain points at the server.

## 1. The instance

- **Ubuntu 24.04**, **t3.small** or bigger (2 GB RAM; the data tables live in memory). 20 GB disk.
- Security group inbound: **22** (your IP only), **80** and **443** (anywhere).
- Give it an **Elastic IP**, so the address survives a stop/start.

## 2. Install Docker

```bash
ssh ubuntu@<server-ip>
curl -fsSL https://get.docker.com | sudo sh        # Docker + the compose plugin
sudo usermod -aG docker ubuntu && exit             # log back in for the group to apply
```

## 3. Code, data and secrets

```bash
git clone https://github.com/ImanuelChatur/bonker-banker.git && cd bonker-banker
```

`data/processed/` (about 8 MB of Parquet) is gitignored, so copy it from a machine that has it.
From your own computer, in the repo folder:

```bash
scp data/processed/*.parquet ubuntu@<server-ip>:~/bonker-banker/data/processed/
```

Then on the server create `.env` from the example:

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # paste as BB_SECRET_KEY
nano .env                                                   # GEMINI_API_KEY, BB_SECRET_KEY
```

## 4. Start it

```bash
docker compose up -d --build
docker compose ps            # app should say "healthy" after about 20 seconds
```

Open `http://<server-ip>`. Containers restart on their own after a crash or reboot.

## 5. HTTPS (once you have a domain)

1. Point an **A record** for the domain at the Elastic IP.
2. In `.env`: `SITE_ADDRESS=your.domain` and `BB_COOKIE_SECURE=1`.
3. `docker compose up -d`. Caddy fetches the certificate; `https://your.domain` works within a minute.

Until then the site is plain HTTP, so passwords cross the network unencrypted. Fine for a demo, not beyond.

## Everyday commands

| Task | Command |
| --- | --- |
| Update to the latest code | `git pull && docker compose up -d --build` |
| Logs | `docker compose logs -f app` |
| Add an account | `docker compose exec app python ../scripts/create_user.py add <username>` |
| Close sign-up | `BB_REGISTRATION=off` in `.env`, then `docker compose up -d` |
| Stop | `docker compose down` (accounts and saved scenarios are kept) |
| Back up accounts and saved data | `docker compose cp app:/app/uploads ./uploads-backup` |

Accounts, saved scenarios and uploaded statements live in the `uploads` Docker volume.
`docker compose down -v` deletes it.
