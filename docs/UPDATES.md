# Auto-update design and manifest format

Overview
- The desktop client will periodically check a hosted JSON manifest to see if a new
  version is available. The client will download the release artifact, verify its
  checksum and signature, then hand off to the platform's installer/updater.

Manifest (example)
```
{
  "version": "1.2.3",
  "assets": [
    {"name": "MovieApp-1.2.3.zip", "url": "https://cdn.example.com/MovieApp-1.2.3.zip", "sha256": "..."}
  ],
  "signature": "<hex-hmac-or-rsa-signature>"
}
```

Security notes
- Use asymmetric signatures (RSA/ECDSA) in production; HMAC is acceptable for early testing.
- Serve manifests and assets over HTTPS.
- Sign artifacts and the manifest using a private key stored offline or in a secure CI secret.
- On Windows, code-sign installers/executables to reduce Defender/AV problems.

Server-side
- CI should build artifacts, compute SHA256, sign the manifest, and publish both the
  artifact and the signed manifest to a stable URL.

Client-side
- On startup (or periodically) the app downloads the manifest, verifies signature,
  checks version, downloads asset, verifies SHA256, and triggers the installer/update flow.
