# Custom Match Dashboard

Static League of Legends custom-game dashboard generated from match history data.

## Local generation

```powershell
python data_analysis_customs.py --output prod/index.html
```

Without API environment variables, the generator uses `match_history.json`.

## Netlify

Netlify is configured by `netlify.toml`.

- Build command: `python data_analysis_customs.py --output prod/index.html`
- Publish directory: `prod`
- Functions directory: `netlify/functions`

Set these Netlify environment variables:

- `MATCHES_API_KEY`
- `NETLIFY_BUILD_HOOK_URL`

Optional:

- `MATCHES_API_URL`

The dashboard refresh button triggers the Netlify build hook through a Netlify
Function. After the deploy completes, reload the page for fresh data.
