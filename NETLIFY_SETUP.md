# Netlify Setup

This dashboard is still generated as static HTML, but Netlify can rebuild it from
the live matches API.

## Required Netlify environment variables

Set these in Netlify under Site configuration -> Environment variables:

- `MATCHES_API_KEY`: the API key for `GET /v1/matches`
- `NETLIFY_BUILD_HOOK_URL`: a Netlify build hook URL for this site

Optional:

- `MATCHES_API_URL`: override the default `http://193.123.187.108/v1/matches`

Do not put the API key in any HTML or JavaScript file.

## Build settings

The included `netlify.toml` uses:

- Build command: `python data_analysis_customs.py --output prod/index.html`
- Publish directory: `prod`
- Functions directory: `netlify/functions`

## Refresh button

The dashboard button calls `/.netlify/functions/refresh-data`. That function
does not call the matches API directly. It triggers the Netlify build hook, and
the next Netlify build fetches fresh match data with `MATCHES_API_KEY`.

After clicking refresh, wait for the Netlify deploy to finish, then reload the
page.
