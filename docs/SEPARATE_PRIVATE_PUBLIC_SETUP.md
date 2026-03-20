# Private Source + Public Installer Setup

This setup keeps your code private while making only the installer public.

## Target Structure

1. Private repo: main Streamore source code (this repo).
2. Public repo: installer distribution only (for example `younglotushuncho/streamore-downloads`).

## Why This Works

- Users can download `StreamoreSetup.exe` from a public release URL.
- Your full source and internal files stay private.
- CI/CD still runs automatically from your private repo.

## One-Time Setup

1. Create a new public GitHub repo for downloads.
2. In the private repo, create a PAT with `repo` scope (or fine-grained write access to the public repo).
3. Add these GitHub Actions secrets in the private repo:
   - `PUBLIC_RELEASE_TOKEN`: token that can publish releases to the public repo.
   - `PUBLIC_RELEASE_REPO`: target public repo, example `younglotushuncho/streamore-downloads`.
4. Add `NEXT_PUBLIC_DESKTOP_INSTALLER_URL` in Vercel:
   - `https://github.com/<owner>/<public-repo>/releases/latest/download/StreamoreSetup.exe`

## CI/CD Workflow

Use `.github/workflows/publish_public_installer.yml`.

It will:

1. Build `desktop/Output/StreamoreSetup.exe` in the private repo pipeline.
2. Create/update release tag `installer-latest` in the public repo.
3. Upload `StreamoreSetup.exe` as the release asset.

## Test Checklist

1. Run the workflow manually from Actions tab.
2. Confirm public URL works in browser:
   - `https://github.com/<owner>/<public-repo>/releases/latest/download/StreamoreSetup.exe`
3. Open your web app and verify the "Download Manager" button downloads the installer directly.

