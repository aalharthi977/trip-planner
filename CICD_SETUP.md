# CI/CD Setup Guide
## GitHub Actions → Cloudflare Tunnel SSH → home-lab

---

## Overview

Every push to `main` triggers GitHub Actions, which SSHes into your server
through your existing Cloudflare Tunnel and deploys only what changed.

---

## Step 1 — Generate a dedicated deploy SSH key (on your Mac)

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/trip_planner_deploy -N ""
```

This creates two files:
- `~/.ssh/trip_planner_deploy`      ← private key (goes to GitHub)
- `~/.ssh/trip_planner_deploy.pub`  ← public key (goes to server)

---

## Step 2 — Add public key to your server

```bash
# Copy the public key to the server
ssh-copy-id -i ~/.ssh/trip_planner_deploy.pub admin@192.168.0.128

# Verify it works
ssh -i ~/.ssh/trip_planner_deploy admin@192.168.0.128 "echo connected"
```

---

## Step 3 — Add SSH hostname to Cloudflare Tunnel

On your server, edit the tunnel config:

```bash
sudo nano /etc/cloudflared/config.yml
```

Add this entry before the final `- service: http_status:404`:

```yaml
  - hostname: ssh.aalharthi.net
    service: ssh://localhost:22
```

Restart cloudflared:

```bash
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
```

Add the DNS record in Cloudflare dashboard:
- Type: Tunnel
- Name: ssh
- Target: home-server-tunnel
- Proxy: Proxied ✓

Test the tunnel SSH from your Mac:

```bash
# Install cloudflared on Mac if not already installed
brew install cloudflare/cloudflare/cloudflared

# Test SSH through tunnel
ssh -i ~/.ssh/trip_planner_deploy \
  -o ProxyCommand="cloudflared access ssh --hostname %h" \
  admin@ssh.aalharthi.net "echo tunnel works"
```

---

## Step 4 — Add GitHub repository to server

The server needs to be able to pull from your GitHub repo:

```bash
# On the server — clone your repo into the existing location
cd ~/docker
git clone https://github.com/YOUR_USERNAME/trip-planner.git trip-planner-git

# Or if already set up, just add git remote
cd ~/docker/trip-planner
git init
git remote add origin https://github.com/YOUR_USERNAME/trip-planner.git
git pull origin main
```

> The workflow does `git pull origin main` on every deploy.
> Make sure the repo is public (or add a GitHub PAT for private).

---

## Step 5 — Add GitHub Actions Secrets

Go to: github.com/YOUR_USERNAME/trip-planner → Settings → Secrets and variables → Actions → New repository secret

Add this secret:

| Name | Value |
|------|-------|
| `SSH_PRIVATE_KEY` | Contents of `~/.ssh/trip_planner_deploy` (the private key file) |

To get the private key value:
```bash
cat ~/.ssh/trip_planner_deploy
```

Copy everything including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`.

---

## Step 6 — Push your code to GitHub

```bash
cd ~/Downloads/trip-planner   # or wherever your local copy is
git init
git add .
git commit -m "Initial commit — Trip Planner"
git remote add origin https://github.com/YOUR_USERNAME/trip-planner.git
git push -u origin main
```

This first push will trigger the workflow. Watch it run at:
github.com/YOUR_USERNAME/trip-planner/actions

---

## Step 7 — Verify the pipeline

After the push, the Actions tab should show:
1. ✓ Checkout code
2. ✓ Detect what changed
3. ✓ Setup SSH via Cloudflare Tunnel
4. ✓ Deploy to server
5. ✓ Verify deployment (hits /api/health and checks for 200)

---

## Day-to-day workflow after setup

```bash
# Edit frontend
nano web/index.html
git add web/index.html
git commit -m "feat: improve trip card UI"
git push
# → GitHub Actions copies index.html to container instantly (no rebuild)

# Edit backend
nano api/main.py
git add api/main.py
git commit -m "feat: add trip sharing endpoint"
git push
# → GitHub Actions rebuilds trip-planner-api container (~45 seconds)

# Change both
git add .
git commit -m "feat: add notes count to trip card"
git push
# → GitHub Actions rebuilds API + refreshes frontend
```

---

## Troubleshooting

```bash
# Check Actions logs
# github.com/YOUR_USERNAME/trip-planner/actions → click the failed run

# Test SSH tunnel manually from Mac
ssh -i ~/.ssh/trip_planner_deploy \
  -o ProxyCommand="cloudflared access ssh --hostname %h" \
  admin@ssh.aalharthi.net

# Check cloudflared on server
sudo systemctl status cloudflared
sudo journalctl -u cloudflared --since "10 minutes ago"

# Check containers after deploy
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep trip
docker logs trip-planner-api --tail 20
```

---

## File structure in your repo

```
trip-planner/
├── .github/
│   └── workflows/
│       └── deploy.yml        ← CI/CD pipeline
├── api/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── seed.py
├── web/
│   ├── index.html
│   └── nginx.conf
├── docker-compose.yml
└── DEPLOY.md
```

---

## Security notes

- The deploy SSH key has access only to the `admin` user — no root
- The private key lives only in GitHub Secrets (encrypted at rest)
- SSH traffic goes through Cloudflare Tunnel — no port 22 exposed to internet
- The `ssh.aalharthi.net` hostname only exists inside the Cloudflare Tunnel
