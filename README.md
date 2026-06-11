# Ertland website

Static website for `ertland.ai.com`.

## Files

- `index.html` — self-contained sky-blue + white landing page.

## Deploy

Upload this folder to any static hosting platform:

- Vercel
- Cloudflare Pages
- Netlify
- Nginx / Apache static server

Then add the custom domain:

```text
ertland.ai.com
```

Configure DNS according to the hosting platform's instruction, usually a CNAME record.

## Note

The Notion URL `https://ertland.notion.site/` currently returns `publicAccessRole: none` from an external unauthenticated environment, so the original Notion body was not retrievable here. The page includes an editable content migration section that can be replaced once the exact Notion body is available.
