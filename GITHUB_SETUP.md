# GitHub Setup Instructions

This document explains how to push this project to GitHub with full version control.

## Prerequisites

- GitHub account (free at https://github.com)
- Git installed (`git --version` to check)
- SSH key configured (or use HTTPS with personal access token)

## Step 1: Create GitHub Repository

### Option A: Using GitHub Web Interface (Easiest)

1. Go to https://github.com/new
2. **Repository name**: `rayban-dataglove-hanoi`
3. **Description**: "Ray-Ban Meta Display + Pressure Data Glove Integration"
4. **Visibility**: Public (for easy sharing)
5. **Initialize with**: Nothing (we'll push existing code)
6. Click **"Create repository"**

### Option B: Using GitHub CLI

```bash
# Install GitHub CLI first (if not installed)
# https://cli.github.com/

gh repo create rayban-dataglove-hanoi \
  --description "Ray-Ban Meta Display + Pressure Data Glove Integration" \
  --public \
  --source=. \
  --remote=origin \
  --push
```

---

## Step 2: Configure Git (First Time Only)

Set your Git identity:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Verify:
```bash
git config --list | grep user
```

---

## Step 3: Connect Local Repository to GitHub

### If you created repo on GitHub:

Go to your repository page on GitHub. You'll see a box that says "Quick setup" with a URL.

Copy the URL (looks like `https://github.com/yourusername/rayban-dataglove-hanoi.git`)

In your terminal:

```bash
cd /home/claude/rayban-dataglove-hanoi

# Add remote
git remote add origin https://github.com/yourusername/rayban-dataglove-hanoi.git

# Verify
git remote -v
# Should show:
# origin  https://github.com/yourusername/rayban-dataglove-hanoi.git (fetch)
# origin  https://github.com/yourusername/rayban-dataglove-hanoi.git (push)
```

---

## Step 4: Stage and Commit Files

```bash
cd /home/claude/rayban-dataglove-hanoi

# See what files exist
ls -la

# Stage all files
git add .

# Verify what's staged
git status

# Commit with message
git commit -m "Initial commit: Ray-Ban Data Glove Integration

- Flask app with Hanoi game logic
- Ray-Ban glasses UI (400x400px)
- Pressure glove UDP receiver
- REST API for real-time state
- Complete documentation
- Network configuration"
```

**Good commit messages** explain what and why:
- ✅ Good: "Add glasses UI with real-time updates"
- ❌ Bad: "update stuff"

---

## Step 5: Push to GitHub

### First Push (Setup Tracking Branch)

```bash
git push -u origin main
```

Or if your default branch is `master`:

```bash
git push -u origin master
```

The `-u` flag sets up tracking so future `git push` is automatic.

### Subsequent Pushes

```bash
git push
```

---

## Step 6: Verify on GitHub

1. Go to https://github.com/yourusername/rayban-dataglove-hanoi
2. Verify all files appear in the repo
3. Check that README.md shows up as project description
4. Confirm the project tree structure is correct

---

## Full Command Sequence (Copy-Paste)

If you want to do everything at once:

```bash
cd /home/claude/rayban-dataglove-hanoi

# Initialize git (already done, but verify)
git status

# Configure user (if not already done)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Add remote (replace with your repo URL from GitHub)
git remote add origin https://github.com/yourusername/rayban-dataglove-hanoi.git

# Stage all files
git add .

# Check what's staged
git status

# Commit
git commit -m "Initial commit: Ray-Ban Data Glove Integration

- Complete Flask application with Hanoi game
- Glasses-optimized 400x400px UI
- UDP receiver for pressure glove
- REST API endpoints
- Full documentation and setup guides"

# Push to GitHub
git push -u origin main
```

If you get an error like "fatal: 'origin' already exists", run:
```bash
git remote remove origin
git remote add origin https://github.com/yourusername/rayban-dataglove-hanoi.git
```

---

## Handling Authentication

### HTTPS (Recommended for Beginners)

When prompted for password, use a **Personal Access Token** instead:

1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (full control of private repositories)
4. Copy the token
5. Use as password when `git push` prompts

### SSH (More Convenient)

If you have SSH key already:
```bash
# Change remote to SSH
git remote set-url origin git@github.com:yourusername/rayban-dataglove-hanoi.git

# Test connection
ssh -T git@github.com
```

If you don't have SSH key yet:
```bash
# Generate key
ssh-keygen -t ed25519 -C "your.email@example.com"

# Add to GitHub: Settings → SSH and GPG keys → New SSH key
# Paste contents of ~/.ssh/id_ed25519.pub
```

---

## After First Push: Version Control Workflow

### Making Changes

```bash
# Edit files
nano app.py
# ... make changes ...

# See what changed
git status

# Stage specific file
git add app.py

# Or stage all changes
git add .

# Commit
git commit -m "Fix hand detection sensitivity"

# Push to GitHub
git push
```

### Creating Branches

For experimental features:

```bash
# Create and switch to new branch
git checkout -b feature/vision-ai

# Make changes...
git add .
git commit -m "WIP: Add vision AI integration"

# Push branch to GitHub
git push -u origin feature/vision-ai

# Create Pull Request on GitHub.com
# Then merge back to main
```

### Pulling Changes

If working from multiple computers:

```bash
# Get latest from GitHub
git pull origin main

# Or just pull (if tracking branch is set)
git pull
```

---

## GitHub Repository Structure

Your repo will look like:

```
rayban-dataglove-hanoi/
├── README.md           (Project overview - auto displays on GitHub)
├── LICENSE             (MIT license)
├── requirements.txt    (Python dependencies)
├── .env.example        (Environment variables template)
├── .gitignore          (Files to ignore)
├── app.py              (Main Flask app)
├── sensor.py           (Glove packet parser)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SETUP_GUIDE.md
│   └── API.md
└── firmware/
    └── old_glove.ino   (ESP32 code)
```

---

## Tips for Good Repository Hygiene

### 1. Meaningful Commits

```bash
# Good
git commit -m "Add ring detection stability

- Increase STABLE_PICK_FRAMES from 2 to 3
- Prevents jitter when touching sensors
- Fixes issue #5"

# Bad
git commit -m "stuff"
```

### 2. Keep .env Out

Your `.env` file should NEVER be committed (it has secrets). It's in `.gitignore` for this reason.

```bash
# This is OK (uses the template)
git add .env.example

# This is NOT OK
git add .env  # DON'T DO THIS
```

### 3. Regular Small Commits

```bash
# Better: Multiple small commits
git add app.py && git commit -m "Fix timeout bug"
git add docs/API.md && git commit -m "Update API docs"

# Less ideal: One huge commit
git add . && git commit -m "Many changes"
```

### 4. Use Tags for Releases

```bash
# Tag a version
git tag -a v1.0.0 -m "Initial release: Glasses UI working"

# Push tags to GitHub
git push origin v1.0.0

# List tags
git tag -l
```

---

## Checking Repository Status

```bash
# See commit history
git log --oneline

# See what changed in last commit
git show HEAD

# See all branches
git branch -a

# See remote status
git remote -v
```

---

## Troubleshooting GitHub Push

### Error: "fatal: 'origin' already exists"

```bash
git remote remove origin
git remote add origin https://github.com/yourusername/rayban-dataglove-hanoi.git
```

### Error: "Please make sure you have the correct access rights"

```bash
# Check SSH key is loaded
ssh-add ~/.ssh/id_ed25519

# Or use HTTPS instead
git remote set-url origin https://github.com/yourusername/rayban-dataglove-hanoi.git
```

### Error: "Your branch is ahead by X commits"

```bash
# Push those commits
git push
```

### Error: "fatal: could not read Username"

```bash
# Use personal access token instead of password
# Generate at: GitHub → Settings → Developer settings → Personal access tokens

# Or use SSH (see SSH section above)
```

---

## Protecting Your Repository

### Set Branch Protection (Recommended)

1. Go to repo Settings
2. Branches → Branch protection rules
3. Click "Add rule"
4. Branch name: `main` (or `master`)
5. Enable:
   - "Require status checks to pass before merging"
   - "Require reviews before merging"
6. Save

This prevents accidental merges of broken code.

---

## Adding Collaborators

If you want others to contribute:

1. Settings → Collaborators and teams
2. Add collaborators with GitHub username
3. They get invited, can clone and push

---

## GitHub Pages (Optional)

Host documentation at `yourusername.github.io/rayban-dataglove-hanoi`:

1. Settings → Pages
2. Source: `main` branch, `/docs` folder
3. Wait for build
4. Docs auto-deploy

---

## Updating README on GitHub

The README.md you created displays automatically on your GitHub repo home page.

**To update**:
```bash
nano README.md
# ... make changes ...
git add README.md
git commit -m "Update README with new information"
git push
```

Changes appear on GitHub within seconds.

---

## Next: GitHub Actions (CI/CD)

Once your repo is on GitHub, you can set up automated testing:

Create `.github/workflows/python-app.yml`:
```yaml
name: Python application

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
    - run: pip install -r requirements.txt
    - run: python -m pytest
```

This runs tests automatically on every push!

---

## Summary

**You're done!** Your project is now on GitHub with:

✅ Full version control history
✅ Easy collaboration  
✅ Automatic backups
✅ Public showcase of your work
✅ Issue tracking
✅ Pull requests for contributions

**Next time you make changes:**
```bash
git add .
git commit -m "Your message"
git push
```

That's it!

---

**Last Updated**: 2025-06-05
