# Trip Planner — Deployment Guide
## Server: home-lab (192.168.0.128) · Cloudflare Tunnel · aalharthi.net

---

## File structure

```
~/docker/trip-planner/
├── docker-compose.yml
├── data/                  ← auto-created, holds trips.db
├── api/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── seed.py
└── web/
    ├── index.html
    └── nginx.conf
```

---

## Step 1 — Copy files to server

From your local machine:
```bash
scp -r trip-planner/ admin@192.168.0.128:~/docker/
```

Or clone/copy manually via Filebrowser at https://files.aalharthi.net

---

## Step 2 — Set a secure SECRET_KEY

Edit docker-compose.yml and replace the SECRET_KEY value:
```bash
nano ~/docker/trip-planner/docker-compose.yml
```

Generate a strong key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Replace `change-this-to-a-random-string-in-production` with the output.

---

## Step 3 — Build and start

```bash
cd ~/docker/trip-planner
docker compose up -d --build
```

Verify both containers are running:
```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Expected output:
```
trip-planner-api    Up X seconds
trip-planner-web    Up X seconds   0.0.0.0:8091->80/tcp
```

Test locally:
```bash
curl http://localhost:8091
curl http://localhost:8091/api/health
```

---

## Step 4 — Seed the Italy trip sample data

```bash
docker exec trip-planner-api python seed.py
```

Default credentials created:
- Username: `admin`
- Password: `tripplanner123`

To use a custom password:
```bash
docker exec trip-planner-api python seed.py --username admin --password YourPassword
```

---

## Step 5 — Cloudflare DNS

1. Go to dash.cloudflare.com → aalharthi.net → DNS
2. Add record:
   - Type: **Tunnel** (NOT CNAME)
   - Name: `trip`
   - Target: `home-server-tunnel`
   - Proxy: Proxied ✓

---

## Step 6 — Cloudflare Tunnel config

```bash
sudo nano /etc/cloudflared/config.yml
```

Add before the final `- service: http_status:404` line:
```yaml
  - hostname: trip.aalharthi.net
    service: http://localhost:8093
```

Restart:
```bash
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
```

---

## Step 7 — Nginx Proxy Manager

1. Go to https://npm.aalharthi.net
2. Hosts → Proxy Hosts → Add Proxy Host
3. Fill in:
   - Domain: `trip.aalharthi.net`
   - Scheme: `http`
   - Forward Hostname: `192.168.0.128`
   - Forward Port: `8093`
   - Websockets: OFF
   - SSL: None (Cloudflare handles it)
4. Save

---

## Verify

Open https://trip.aalharthi.net — you should see the login screen.

---

## Backup

The entire database is a single file. Add to your cron (same pattern as Vaultwarden):

```bash
# Trip Planner backup — 3 AM daily
0 3 * * * sudo cp ~/docker/trip-planner/data/trips.db /mnt/mycloud/trip_planner_bk/trips_$(date +\%Y\%m\%d).db
```

Create the backup folder first:
```bash
mkdir -p /mnt/mycloud/trip_planner_bk
```

---

## Update frontend (no rebuild needed)

The HTML file is mounted as a volume — just replace it and Nginx serves it immediately:

```bash
# Replace the file
cp new-index.html ~/docker/trip-planner/web/index.html
# No restart needed — Nginx reads it on next request
```

## Update backend (rebuild required)

```bash
cd ~/docker/trip-planner
docker compose up -d --build trip-planner-api
```

---

## Useful commands

```bash
# View logs
docker logs trip-planner-api --tail 50
docker logs trip-planner-web --tail 20

# Restart
docker compose -f ~/docker/trip-planner/docker-compose.yml restart

# Stop
docker compose -f ~/docker/trip-planner/docker-compose.yml down

# Check DB directly
docker exec trip-planner-api sqlite3 /data/trips.db "SELECT username FROM users;"
docker exec trip-planner-api sqlite3 /data/trips.db "SELECT title, destination FROM trips;"

# Reset a user's password
docker exec trip-planner-api python3 -c "
from passlib.context import CryptContext
import sqlite3, os
db = sqlite3.connect(os.getenv('DB_PATH','/data/trips.db'))
h = CryptContext(schemes=['bcrypt']).hash('newpassword')
db.execute('UPDATE users SET hashed_password=? WHERE username=?', (h, 'admin'))
db.commit()
print('Password updated')
"
```

---

## Port reference

| Port | Service |
|------|---------|
| 8093 | trip-planner-web (Nginx, public) |
| 8092 | trip-planner-api (FastAPI, internal only) |

The API port 8092 is NOT exposed to the host — only the Nginx container can reach it via the internal `trip-net` Docker network.
