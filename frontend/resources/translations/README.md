Place translation .qm files here for runtime loading.

How to generate .qm files (requires Qt's `lrelease` tool):

Windows (PowerShell):
```
cd frontend\resources\translations
lrelease es.ts
lrelease fr.ts
```

Unix/macOS:
```
cd frontend/resources/translations
lrelease es.ts
lrelease fr.ts
```

This will produce `es.qm`, `fr.qm` which the app will load automatically at startup when the user selects the corresponding language in Settings.

If you don't have `lrelease` installed, install the Qt tools (or use the `lrelease` bundled with your PyQt installation). Alternatively, use the provided `scripts/compile_translations.py` helper which calls `lrelease` if available.
