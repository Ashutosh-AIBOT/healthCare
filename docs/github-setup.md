# GitHub setup (git + gh)

Repo: **https://github.com/Ashutosh-AIBOT/healthCare.git**

This guide gets you to: clone/fetch/push with git, and create PRs/checks with `gh`.

---

## Current status checklist

Run these locally to see what is already working:

```bash
# Network
curl -I https://github.com
curl -I https://pypi.org

# Git remote
git remote -v
git fetch origin
git branch -a

# GitHub CLI
gh --version
gh auth status

# Python (API)
source .venv/bin/activate
pip install -r apps/api/requirements.txt
python -c "import fastapi; print('fastapi ok')"
```

| Check | Expected |
|---|---|
| `curl github.com` | HTTP 200 |
| `git fetch origin` | succeeds |
| `git push --dry-run origin HEAD` | succeeds (needs auth) |
| `gh auth status` | logged in to github.com |
| `gh repo view` | shows Ashutosh-AIBOT/healthCare |
| `pip install ...` | no NameResolutionError |

---

## 1. Install GitHub CLI (`gh`)

**Arch Linux (recommended):**

```bash
sudo pacman -S github-cli
```

**Or user install (no sudo):**

```bash
mkdir -p ~/.local/bin
cd /tmp
curl -sSL -o gh.tgz "https://github.com/cli/cli/releases/download/v2.63.2/gh_2.63.2_linux_amd64.tar.gz"
tar -xzf gh.tgz
cp gh_2.63.2_linux_amd64/bin/gh ~/.local/bin/gh
chmod +x ~/.local/bin/gh
gh --version
```

Ensure `~/.local/bin` is on your `PATH` (already true if you use Cursor's default shell).

---

## 2. Authenticate `gh` (pick one method)

### Method A — Browser login (easiest, interactive)

```bash
gh auth login
```

Choose:

- GitHub.com
- HTTPS
- **Login with a web browser** (or paste token if you prefer)
- When asked, authenticate git credentials: **Yes**

Verify:

```bash
gh auth status
gh repo view Ashutosh-AIBOT/healthCare
```

### Method B — Personal access token (non-interactive, good for CI/agents)

1. GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Create token for repo `Ashutosh-AIBOT/healthCare` with:
   - Contents: Read and write
   - Pull requests: Read and write
   - Actions: Read (optional)
   - Metadata: Read
3. **Do not commit the token.** Store it only in your password manager or shell profile.

```bash
# One-time login (token not echoed)
gh auth login --with-token <<EOF
YOUR_GITHUB_TOKEN_HERE
EOF

# Or export for this shell session only
export GH_TOKEN="YOUR_GITHUB_TOKEN_HERE"
export GITHUB_TOKEN="$GH_TOKEN"
```

Verify:

```bash
gh auth status
git push --dry-run origin HEAD
```

### Method C — SSH (alternative to HTTPS)

```bash
ssh-keygen -t ed25519 -C "your-email@example.com" -f ~/.ssh/id_ed25519_github
cat ~/.ssh/id_ed25519_github.pub
# Add the public key at GitHub → Settings → SSH and GPG keys

gh auth login   # choose SSH protocol
git remote set-url origin git@github.com:Ashutosh-AIBOT/healthCare.git
ssh -T git@github.com
```

---

## 3. Git identity (should match GitHub)

```bash
git config --global user.name "Ashutosh-AIBOT"
git config --global user.email "Ashutosh-AIBOT@users.noreply.github.com"
```

Repo-local overrides (optional):

```bash
cd /home/creator/Desktop/IDEA/Ai-health-App
git config user.name "Ashutosh-AIBOT"
git config user.email "Ashutosh-AIBOT@users.noreply.github.com"
```

---

## 4. Branch workflow (this project)

```bash
cd /home/creator/Desktop/IDEA/Ai-health-App
git checkout main
git pull origin main

# One feature per branch
git checkout -b feat/m1-auth
# ... work, commit incrementally ...
git push -u origin feat/m1-auth

gh pr create \
  --title "feat(auth): M1 identity and tenancy" \
  --body "$(cat <<'EOF'
## What
JWT auth, OTP, roles, RLS skeleton.

## Why
M1 milestone from PLAN.md.

## Test evidence
- [ ] lint/typecheck
- [ ] docker compose up
EOF
)"
```

Rules: see [CONTRIBUTING.md](../CONTRIBUTING.md). Never force-push `main`. Never commit `.env`.

---

## 5. Python environment (API)

Network must reach PyPI. In the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r apps/api/requirements.txt
```

If you see `NameResolutionError` for `pypi.org`, fix DNS/network first (VPN, firewall, `/etc/resolv.conf`), then retry.

---

## 6. Troubleshooting

### `Could not resolve host: github.com` or `pypi.org`

- Confirm internet: `ping 1.1.1.1`
- Confirm DNS: `ping github.com`
- Cursor/agent sandbox may block network — run commands in your **system terminal** with network enabled
- Retry with VPN off/on if corporate DNS blocks GitHub

### `fatal: could not read Username for 'https://github.com'`

- You are not authenticated for **push**
- Run `gh auth login` and choose to configure git credentials
- Or set `GH_TOKEN` and run `gh auth login --with-token`

### `gh: command not found`

- Install gh (section 1) or add `~/.local/bin` to PATH:
  `export PATH="$HOME/.local/bin:$PATH"`

### Agent sessions vs your terminal

- **Fetch** of a public repo may work without auth
- **Push** and **gh pr create** always need auth
- Complete login in your own terminal once; credentials persist via `gh` and git credential helper

---

## 7. Security

- Never commit tokens, `.env`, or PATs
- Rotate any token that was pasted into chat or committed by mistake
- Use fine-grained tokens scoped to this repo only
- `gitleaks` runs in CI when configured — keep secrets out of history
