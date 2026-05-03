# Compliance Notes

This version was designed to be safer for public GitHub usage than a full-text scraper.

## Design choices

- Do not download full article bodies.
- Do not republish full publisher articles.
- Keep only title/source/time/link metadata.
- Use RSS/headline feeds where available.
- Link users back to original sources.
- Avoid paywall circumvention and login-gated pages.

## Good future data sources

- SEC EDGAR company filings
- SEDAR+ for Canadian issuers
- FRED / World Bank / OECD macro data
- Official exchange or company investor-relations RSS feeds
- Paid APIs with clear redistribution rights
