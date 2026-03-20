Adding repository secrets (recommended):

1) GitHub UI
- Go to your repository → Settings → Secrets and variables → Actions → New repository secret
- Name: `MANIFEST_HMAC_KEY`
- Value: (64-char hex) — generate locally with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

2) gh CLI (recommended for automation)
- Install GitHub CLI and authenticate (`gh auth login`)
- Run:

```powershell
# Windows PowerShell
$k = python -c "import secrets; print(secrets.token_hex(32))"; gh secret set MANIFEST_HMAC_KEY --body $k

# Bash
k=$(python -c 'import secrets; print(secrets.token_hex(32))'); gh secret set MANIFEST_HMAC_KEY --body "$k"
```

Notes:
- Keep the secret private. Anyone with it can sign update manifests.
- After adding the secret, re-run your workflow (recreate tag) to proceed with signing and release.
