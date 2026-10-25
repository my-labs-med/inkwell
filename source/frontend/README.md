# frontend

Inkwell's static client: HTML, CSS and vanilla JS modules, no build step.

| Path | Cache at CloudFront |
|---|---|
| `assets/` (fonts, icons, favicon) | 1 year, immutable — these files never change |
| `index.html`, `css/`, `js/` | short TTL |

`js/config.js` holds the API base path, Cognito domain and app client ID. It is generated at deploy
time. Sign-in uses the Cognito Hosted UI with PKCE, and tokens live only in the tab's
`sessionStorage`.

## Preview without AWS

Set `mock: true` in `js/config.js`, then:

```bash
python3 -m http.server -d source/frontend 8000
```

Data is kept in the browser's `localStorage`.

## Test

```bash
node --test "source/frontend/test/"*.test.mjs
```
