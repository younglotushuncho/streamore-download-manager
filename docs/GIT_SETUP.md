# Git Setup for Publishing

Your repository is currently local-only. Follow these steps to push to GitHub:

## Steps

### 1. Create a GitHub Repository

Go to https://github.com/new and create a new repository (e.g., `movie-downloader-app`).

**Don't initialize** with README, .gitignore, or license (you already have these locally).

### 2. Add Remote Origin

After creating the repo, GitHub will show you commands. Use these:

```powershell
# Add the remote (replace YOUR_USERNAME and YOUR_REPO)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Verify it was added
git remote -v
```

### 3. Push Your Code

Since you're on the `master` branch (not `main`):

```powershell
# Push master branch
git push -u origin master
```

Or if you want to rename to `main` first:

```powershell
# Rename branch to main
git branch -M main

# Push to main
git push -u origin main
```

### 4. Set Default Branch on GitHub

If you renamed to `main`:
- Go to **Settings → Branches** in your GitHub repo
- Set `main` as the default branch

### 5. Update Deployment Guide

After pushing, update `UPDATE_MANIFEST_URL` in [backend/config.py](../backend/config.py):

```python
UPDATE_MANIFEST_URL = os.getenv('UPDATE_MANIFEST_URL', 
    'https://github.com/YOUR_USERNAME/YOUR_REPO/releases/latest/download/manifest.signed.json')
```

Replace `YOUR_USERNAME` and `YOUR_REPO` with your actual GitHub username and repository name.

---

## Quick Commands Reference

**Check current branch:**
```powershell
git branch
```

**Check remote:**
```powershell
git remote -v
```

**Add remote:**
```powershell
git remote add origin https://github.com/USERNAME/REPO.git
```

**Rename branch to main:**
```powershell
git branch -M main
```

**Push (first time):**
```powershell
git push -u origin main
```

**Push (subsequent):**
```powershell
git push
```

---

## What's Next?

After pushing your code:

1. **Add GitHub Secret**: Go to **Settings → Secrets → Actions** and add `MANIFEST_HMAC_KEY`
2. **Create a release tag**: `git tag v1.0.0 && git push origin v1.0.0`
3. **Watch CI build**: Check the **Actions** tab in your GitHub repo
4. **Download and test**: Get the built app from **Releases**
