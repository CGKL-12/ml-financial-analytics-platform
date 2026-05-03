"""AI-powered global + A-share + optional US equity research automation system.

English-output, single-file version.

Design goals:
- Generate a professional English HTML equity research dashboard.
- Cover global market headlines, A-share watchlist, and optional US equities.
- Reduce copyright / ToS risk by storing headline metadata and source links only.
- Avoid full article scraping and article-body redistribution.

Before running:
1) Install dependencies:
   pip install yfinance feedparser ollama pytz
2) Start Ollama and pull the model, for example:
   ollama pull qwen2.5:14b
3) Run:
   python main.py
"""

from __future__ import annotations

import html
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import ollama
import pytz
import yfinance as yf

# =========================
# Configuration
# =========================

OUTPUT_DIR = "./reports"
EXAMPLES_DIR = "./examples"
KEEP_DAYS = 14
TIMEZONE = "America/Toronto"

# Local LLM configuration
MODEL = "qwen2.5:14b"
LLM_OPTIONS = {
    "temperature": 0.45,
    "num_ctx": 16384,
    "num_gpu": 35,
}

# Toggle US stock coverage
ENABLE_US_STOCKS = True

# Headline limits
MAX_GLOBAL_HEADLINES_PER_TOPIC = 5
MAX_STOCK_HEADLINES = 6

# Global macro / market dashboard tickers through Yahoo Finance
MACRO_TICKERS = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "NASDAQ Composite"),
    ("^DJI", "Dow Jones Industrial Average"),
    ("000001.SS", "Shanghai Composite"),
    ("399001.SZ", "Shenzhen Component"),
    ("^HSI", "Hang Seng Index"),
    ("GC=F", "Gold Futures"),
    ("CL=F", "WTI Crude Oil"),
    ("CNY=X", "USD/CNY"),
]

def pretty_symbol(sym):
    mapping = {
        "^GSPC": "SPX",
        "^IXIC": "IXIC",
        "^DJI": "DJI",
        "^HSI": "HSI",
        "000001.SS": "SSE",
        "399001.SZ": "SZSE",
        "399006.SZ": "ChiNext",
        "GC=F": "Gold",
        "CL=F": "WTI",
        "USDCNY=X": "USD/CNY",
        "CNY=X": "USD/CNY",
    }
    return mapping.get(sym, sym)

# Global news topics via Google News RSS metadata
GLOBAL_NEWS_TOPICS = [
    ("Global Markets", "global stock market economy inflation interest rates"),
    ("Federal Reserve", "Federal Reserve rate cuts inflation markets"),
    ("China Economy", "China economy A-shares yuan policy stimulus"),
    ("AI and Semiconductors", "AI semiconductor Nvidia chips demand market"),
    ("Energy and Commodities", "oil gold commodities market macro risk"),
]

# A-share watchlist. Yahoo symbols are used for market data.
A_SHARE_WATCHLIST = [
    ("600519", "600519.SS", "Kweichow Moutai", "Consumer Staples / Liquor"),
    ("000858", "000858.SZ", "Wuliangye Yibin", "Consumer Staples / Liquor"),
    ("000977", "000977.SZ", "Inspur Electronic Information", "AI Infrastructure / Servers"),
    ("000938", "000938.SZ", "Unisplendour", "Technology / Cloud Infrastructure"),
    ("300750", "300750.SZ", "CATL", "EV Batteries / Clean Energy"),
    ("601318", "601318.SS", "Ping An Insurance", "Financials / Insurance"),
    ("600036", "600036.SS", "China Merchants Bank", "Financials / Banking"),
    ("688041", "688041.SS", "Hygon Information", "Semiconductors / Domestic Chips"),
    ("518880", "518880.SS", "Gold ETF", "Precious Metals"),
]

# Optional US watchlist
US_WATCHLIST = [
    ("AAPL", "Apple", "Mega-cap Technology"),
    ("MSFT", "Microsoft", "Cloud / AI Software"),
    ("NVDA", "NVIDIA", "AI Semiconductors"),
    ("TSLA", "Tesla", "EV / Clean Energy"),
    ("GOOGL", "Alphabet", "Digital Advertising / AI"),
]

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EXAMPLES_DIR, exist_ok=True)


# =========================
# Data models
# =========================

@dataclass
class NewsItem:
    title: str
    source: str
    topic: str
    published: str = ""
    url: str = ""
    summary: str = ""
    lang: str = "en"


@dataclass
class StockInfo:
    symbol: str
    name: str
    market: str
    sector: str
    price: str = "N/A"
    change_pct: str = "N/A"
    pe: str = "N/A"
    pb: str = "N/A"
    high52: str = "N/A"
    low52: str = "N/A"
    source: str = "Yahoo Finance"


# =========================
# Utility functions
# =========================

def cleanup_old_reports() -> None:
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = 0
    for filename in os.listdir(OUTPUT_DIR):
        if not filename.endswith(".html"):
            continue
        path = os.path.join(OUTPUT_DIR, filename)
        if datetime.fromtimestamp(os.path.getmtime(path)) < cutoff:
            os.remove(path)
            removed += 1
    print(f"Cleaned {removed} old report(s).")


def safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def fmt(value, digits: int = 2) -> str:
    number = safe_float(value)
    if number is None:
        return "N/A"
    return str(round(number, digits))


def html_escape(value: str) -> str:
    return html.escape(str(value or ""), quote=True)


def strip_html(text: str) -> str:
    """Convert RSS-provided HTML snippets into clean plain text.

    Google News RSS summaries often include publisher attribution links such as
    <a href=...>. Removing tags here prevents raw HTML from appearing in the
    generated dashboard.
    """
    if not text:
        return ""
    text = text.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]


def render_markdown(text: str) -> str:
    """Render a safe, lightweight subset of Markdown into HTML.

    The LLM naturally returns Markdown headings, bullets, and bold text. This
    renderer escapes all input first, then supports only presentation-oriented
    Markdown so the report looks polished without requiring an extra dependency.
    """
    if not text:
        return '<p class="muted-text">No analysis available.</p>'

    def inline_format(value: str) -> str:
        value = html.escape(value, quote=True)
        value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        return value

    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw in lines:
        line = raw.strip()
        if not line:
            close_lists()
            continue

        if line.startswith("#### "):
            close_lists()
            out.append(f"<h4>{inline_format(line[5:])}</h4>")
        elif line.startswith("### "):
            close_lists()
            out.append(f"<h3>{inline_format(line[4:])}</h3>")
        elif line.startswith("## "):
            close_lists()
            out.append(f"<h2>{inline_format(line[3:])}</h2>")
        elif line.startswith("# "):
            close_lists()
            out.append(f"<h2>{inline_format(line[2:])}</h2>")
        elif re.match(r"^[-*]\s+", line):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            clean = re.sub(r'^\*+\s+', '', line)
            out.append(f"<li>{inline_format(clean)}</li>")
        elif re.match(r"^\d+\.\s+", line):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            clean = re.sub(r'^\d+\.\s+', '', line)
            out.append(f"<li>{inline_format(clean)}</li>")
        else:
            close_lists()
            out.append(f"<p>{inline_format(line)}</p>")

    close_lists()
    return "\n".join(out)


def google_news_rss_url(query: str, language: str = "en-US", region: str = "US") -> str:
    encoded = quote_plus(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl={language}&gl={region}&ceid={region}:en"


def dedupe_news(items: Iterable[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    result: list[NewsItem] = []
    for item in items:
        key = item.title.lower().strip()[:90]
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


# =========================
# Data ingestion
# =========================

def fetch_rss_headlines(url: str, source: str, topic: str, limit: int = 5, lang: str = "en") -> list[NewsItem]:
    """Fetch headline metadata from an RSS feed.

    This function does not fetch full articles. It stores headline, publisher link,
    timestamp, and a short RSS summary when provided by the feed.
    """
    items: list[NewsItem] = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            title = strip_html(getattr(entry, "title", ""))
            if not title:
                continue
            items.append(
                NewsItem(
                    title=title[:220],
                    source=source,
                    topic=topic,
                    published=getattr(entry, "published", "") or getattr(entry, "updated", ""),
                    url=getattr(entry, "link", ""),
                    summary=strip_html(getattr(entry, "summary", "")),
                    lang=lang,
                )
            )
    except Exception as exc:
        print(f"RSS fetch failed for {topic}: {exc}")
    return items


def fetch_global_news() -> list[NewsItem]:
    print("Fetching global market headline metadata...")
    all_items: list[NewsItem] = []
    for topic, query in GLOBAL_NEWS_TOPICS:
        url = google_news_rss_url(query)
        items = fetch_rss_headlines(url, "Google News RSS", topic, MAX_GLOBAL_HEADLINES_PER_TOPIC)
        print(f"  {topic}: {len(items)} headline(s)")
        all_items.extend(items)
        time.sleep(0.25)
    return dedupe_news(all_items)


def fetch_yahoo_news(symbol: str, topic: str, limit: int = 5) -> list[NewsItem]:
    """Fetch stock headline metadata.

    Primary: Yahoo Finance metadata through yfinance.
    Fallback: Google News RSS if Yahoo returns too few headlines.
    """
    items: list[NewsItem] = []

    try:
        news = yf.Ticker(symbol).news or []
        for entry in news[:limit]:
            title = entry.get("title") or ""
            url = entry.get("link") or entry.get("url") or ""
            published = ""
            ts = entry.get("providerPublishTime")
            if ts:
                try:
                    published = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            if title:
                items.append(
                    NewsItem(
                        title=title[:220],
                        source="Yahoo Finance",
                        topic=topic,
                        published=published,
                        url=url,
                        summary="",
                        lang="en",
                    )
                )
    except Exception as exc:
        print(f"Yahoo news failed for {symbol}: {exc}")

    if len(items) < max(2, min(limit, 3)):
        query = f'{symbol} stock news OR earnings OR analyst'
        rss_items = fetch_rss_headlines(
            google_news_rss_url(query),
            source="Google News RSS",
            topic=topic,
            limit=limit,
            lang="en",
        )
        items.extend(rss_items)

    return dedupe_news(items)[:limit]


def fetch_price(symbol: str, name: str, market: str, sector: str) -> StockInfo:
    stock_info = StockInfo(symbol=symbol, name=name, market=market, sector=sector)
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        info = ticker.info or {}

        if not hist.empty:
            last = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) >= 2 else last
            stock_info.price = fmt(last, 2)
            if prev:
                stock_info.change_pct = fmt((last / prev - 1) * 100, 2)

        stock_info.pe = fmt(info.get("trailingPE") or info.get("forwardPE"), 1)
        stock_info.pb = fmt(info.get("priceToBook"), 2)
        stock_info.high52 = fmt(info.get("fiftyTwoWeekHigh"), 2)
        stock_info.low52 = fmt(info.get("fiftyTwoWeekLow"), 2)
    except Exception as exc:
        print(f"Price fetch failed for {symbol}: {exc}")
    return stock_info


def fetch_macro_snapshot() -> list[StockInfo]:
    print("Fetching global macro / market snapshot...")
    results = []
    for symbol, name in MACRO_TICKERS:
        results.append(fetch_price(symbol, name, "Macro", "Index / Commodity / FX"))
        time.sleep(0.15)
    return results


def fetch_watchlist_data() -> list[dict]:
    results: list[dict] = []

    print("Fetching A-share watchlist...")
    for code, yahoo_symbol, name, sector in A_SHARE_WATCHLIST:
        info = fetch_price(yahoo_symbol, name, "A-share", sector)
        news = fetch_yahoo_news(yahoo_symbol, f"{name} / {sector}", MAX_STOCK_HEADLINES)
        results.append({"info": info, "news": news, "code": code})
        time.sleep(0.2)

    if ENABLE_US_STOCKS:
        print("Fetching optional US watchlist...")
        for symbol, name, sector in US_WATCHLIST:
            info = fetch_price(symbol, name, "US", sector)
            news = fetch_yahoo_news(symbol, f"{name} / {sector}", MAX_STOCK_HEADLINES)
            results.append({"info": info, "news": news, "code": symbol})
            time.sleep(0.2)

    return results


# =========================
# LLM analysis
# =========================

def format_headlines_for_prompt(items: list[NewsItem], limit: int = 40) -> str:
    if not items:
        return "No headlines available."
    lines = []
    for idx, item in enumerate(items[:limit], 1):
        lines.append(
            f"[{idx}] Topic={item.topic} | Source={item.source} | Time={item.published}\n"
            f"Headline: {item.title}\n"
            f"URL: {item.url}"
        )
    return "\n\n".join(lines)


def call_ollama(prompt: str) -> str:
    try:
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options=LLM_OPTIONS,
        )
        return response["message"]["content"]
    except Exception as exc:
        return (
            "LLM analysis unavailable. Make sure Ollama is running and the configured model is installed.\n"
            f"Error: {exc}"
        )


def analyze_global_news(global_news: list[NewsItem], macro: list[StockInfo]) -> str:
    macro_text = "\n".join(
        f"- {m.name} ({m.symbol}): price={m.price}, change={m.change_pct}%, 52W={m.low52}~{m.high52}"
        for m in macro
    )

    prompt = f"""You are a professional market intelligence analyst.
Write in polished, concise English suitable for an equity research dashboard.

Use ONLY the market snapshot and headline metadata below. Do not invent facts.
Do not quote or reproduce article bodies. Treat headlines as signals, not confirmed full-article evidence.

[Market Snapshot]
{macro_text}

[Global Headline Metadata]
{format_headlines_for_prompt(global_news)}

Produce the following sections:
1. Global Market Summary: 5 concise bullets
2. Potential Impact on China A-shares: policy, currency, commodities, and risk appetite
3. Potential Impact on US Technology / AI / Semiconductors
4. Three Key Risks to Monitor Today
5. Three Most Important Market Themes

Keep the tone analytical, not promotional. Do not provide personalized investment advice.
"""
    return call_ollama(prompt)


def analyze_stock(info: StockInfo, news: list[NewsItem]) -> str:
    prompt = f"""You are a professional equity research analyst.
Write in polished, concise English suitable for a public GitHub demo report.

Use ONLY the price data and headline metadata below. Do not invent facts.
Do not copy article bodies. Explicitly treat headlines as preliminary signals, not full evidence.

[Stock]
Name={info.name}
Symbol={info.symbol}
Market={info.market}
Sector={info.sector}
Price={info.price}
Change={info.change_pct}%
PE={info.pe}
PB={info.pb}
52W={info.low52}~{info.high52}

[Headline Metadata]
{format_headlines_for_prompt(news, limit=10)}

Output exactly these sections:
1. Investment Thesis: 3 concise bullets
2. Catalyst Signals: based only on headline metadata
3. Key Risks: headline-driven and valuation-driven risks
4. Valuation / Technical Position: use PE, PB, and 52-week range when available
5. Tactical View: Watch / Hold / Cautious / Avoid, with a short rationale
6. Information Gaps: what should be verified from original publisher pages or filings

Keep it professional, concise, and non-promotional. Do not provide personalized investment advice.
"""
    return call_ollama(prompt)


# =========================
# HTML report generation
# =========================

def build_news_html(items: list[NewsItem], limit: int = 8) -> str:
    if not items:
        return '<div class="empty">No headlines available from Yahoo Finance or RSS fallback.</div>'

    blocks = []
    for item in items[:limit]:
        url = html_escape(item.url)
        title = html_escape(item.title)
        link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>' if url else title
        summary = f'<div class="news-summary">{html_escape(item.summary)}</div>' if item.summary else ""
        blocks.append(
            f"""
            <div class="news-item">
              <div class="news-meta">{html_escape(item.topic)} · {html_escape(item.source)} · {html_escape(item.published)}</div>
              <div class="news-title">{link}</div>
              {summary}
            </div>
            """
        )
    return "\n".join(blocks)


def build_macro_html(macro: list[StockInfo]) -> str:
    rows = []
    for item in macro:
        rows.append(
            f"""
            <tr>
              <td>{html_escape(item.name)}</td>
              <td>{html_escape(pretty_symbol(item.symbol))}</td>
              <td>{html_escape(item.price)}</td>
              <td>{html_escape(item.change_pct)}%</td>
              <td>{html_escape(item.low52)} ~ {html_escape(item.high52)}</td>
            </tr>
            """
        )
    return "\n".join(rows)


def build_stock_card(record: dict) -> str:
    info: StockInfo = record["info"]
    news: list[NewsItem] = record["news"]
    analysis = record.get("analysis", "")
    return f"""
    <div class="card">
      <div class="card-header">
        <div>
          <span class="stock-name">{html_escape(info.name)}</span>
          <span class="badge">{html_escape(info.market)}</span>
          <span class="badge muted">{html_escape(info.symbol)}</span>
        </div>
        <div class="price-block">
          <span class="price">{html_escape(info.price)}</span>
          <span class="change">{html_escape(info.change_pct)}%</span>
        </div>
      </div>
      <div class="meta">Sector: {html_escape(info.sector)} · PE: {html_escape(info.pe)} · PB: {html_escape(info.pb)} · 52W: {html_escape(info.low52)} ~ {html_escape(info.high52)}</div>
      <details>
        <summary>Headline signals / source links</summary>
        {build_news_html(news)}
      </details>
      <div class="analysis markdown-body">{render_markdown(analysis)}</div>
    </div>
    """


def save_report(global_news: list[NewsItem], macro: list[StockInfo], stocks: list[dict], global_analysis: str) -> str:
    today = date.today().strftime("%Y-%m-%d")
    now = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M %Z")
    stock_cards = "\n".join(build_stock_card(s) for s in stocks)
    path = os.path.join(OUTPUT_DIR, f"global_equity_report_{today}.html")

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Global + A-share + US Equity Research Report {today}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background:#f3f5f8; color:#1f2937; }}
  .hero {{ background:linear-gradient(135deg,#0f172a,#1e3a8a); color:white; padding:34px 20px; text-align:center; }}
  .hero h1 {{ margin:0; font-size:29px; letter-spacing:.2px; }}
  .hero p {{ opacity:.78; margin:8px 0 0; }}
  .container {{ max-width:1120px; margin:0 auto; padding:24px 16px 48px; }}
  .section-title {{ font-size:20px; font-weight:750; margin:28px 0 12px; border-left:5px solid #1d4ed8; padding-left:10px; }}
  .card {{ background:white; border-radius:16px; padding:20px; margin-bottom:16px; box-shadow:0 2px 16px rgba(15,23,42,.08); }}
  .card-header {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }}
  .stock-name {{ font-weight:750; font-size:19px; }}
  .badge {{ background:#dbeafe; color:#1d4ed8; padding:3px 8px; border-radius:999px; font-size:12px; margin-left:6px; }}
  .badge.muted {{ background:#eef2f7; color:#64748b; }}
  .price-block {{ text-align:right; white-space:nowrap; }}
  .price {{ display:block; font-size:20px; font-weight:750; }}
  .change {{ color:#64748b; font-size:14px; }}
  .meta {{ color:#64748b; font-size:14px; margin:10px 0 12px; }}
  .analysis {{ border-top:1px solid #e5e7eb; margin-top:14px; padding-top:16px; line-height:1.75; font-size:15px; }}
  .markdown-body h2 {{ font-size:20px; margin:6px 0 12px; color:#0f172a; }}
  .markdown-body h3 {{ font-size:17px; margin:18px 0 8px; color:#0f172a; }}
  .markdown-body h4 {{ font-size:15px; margin:14px 0 6px; color:#1e3a8a; }}
  .markdown-body p {{ margin:8px 0; }}
  .markdown-body ul, .markdown-body ol {{ margin:8px 0 12px 22px; padding:0; }}
  .markdown-body li {{ margin:6px 0; }}
  .markdown-body strong {{ color:#0f172a; }}
  .markdown-body code {{ background:#eef2f7; padding:2px 5px; border-radius:5px; font-size:13px; }}
  .muted-text {{ color:#64748b; }}
  details {{ background:#f8fafc; border:1px solid #e5e7eb; border-radius:12px; padding:10px 12px; }}
  summary {{ cursor:pointer; font-weight:650; color:#334155; }}
  .news-item {{ border-top:1px solid #e5e7eb; padding:10px 0; }}
  .news-item:first-of-type {{ border-top:0; }}
  .news-meta {{ color:#64748b; font-size:12px; margin-bottom:4px; }}
  .news-title a {{ color:#1d4ed8; text-decoration:none; font-weight:650; }}
  .news-title a:hover {{ text-decoration:underline; }}
  .news-summary {{ color:#475569; font-size:13px; margin-top:4px; }}
  .empty {{ color:#64748b; padding:10px 0; }}
  table {{ width:100%; border-collapse:collapse; background:white; border-radius:14px; overflow:hidden; box-shadow:0 2px 16px rgba(15,23,42,.08); }}
  th, td {{ padding:10px 12px; border-bottom:1px solid #e5e7eb; text-align:left; font-size:14px; }}
  th {{ background:#f8fafc; color:#334155; }}
  .disclaimer {{ color:#64748b; font-size:13px; line-height:1.7; text-align:center; margin-top:26px; }}
</style>
</head>
<body>
  <div class="hero">
    <h1>Global + A-share + US Equity Research Report</h1>
    <p>Generated at {html_escape(now)} · Data: Yahoo Finance market data + RSS/headline metadata · Local LLM: {html_escape(MODEL)}</p>
  </div>
  <div class="container">
    <div class="section-title">Global Market Snapshot</div>
    <table>
      <thead><tr><th>Asset</th><th>Symbol</th><th>Price</th><th>Change</th><th>52-week range</th></tr></thead>
      <tbody>{build_macro_html(macro)}</tbody>
    </table>

    <div class="section-title">Global News Intelligence</div>
    <div class="card">
      <details open>
        <summary>Global headline signals</summary>
        {build_news_html(global_news, limit=30)}
      </details>
      <div class="analysis markdown-body">{render_markdown(global_analysis)}</div>
    </div>

    <div class="section-title">A-share + Optional US Stock Watchlist</div>
    {stock_cards}

    <div class="disclaimer">
      Educational research project only. This report does not constitute investment advice.<br>
      The system stores headline metadata and source links, not full copyrighted articles. Always read original publisher pages for full context.
    </div>
  </div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return path


def export_sample_json(global_news: list[NewsItem], macro: list[StockInfo], stocks: list[dict]) -> None:
    payload = {
        "global_news_sample": [asdict(x) for x in global_news[:5]],
        "macro_sample": [asdict(x) for x in macro[:5]],
        "stock_sample": [
            {"info": asdict(s["info"]), "news": [asdict(n) for n in s["news"][:2]]}
            for s in stocks[:3]
        ],
    }
    with open(os.path.join(EXAMPLES_DIR, "sample_payload.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# =========================
# Pipeline entry point
# =========================

def generate_daily_report() -> str:
    print("Starting Global + A-share + US Equity Research System")
    cleanup_old_reports()

    macro = fetch_macro_snapshot()
    global_news = fetch_global_news()
    stocks = fetch_watchlist_data()

    print("Running global LLM analysis...")
    global_analysis = analyze_global_news(global_news, macro)

    print("Running stock-level LLM analysis...")
    for record in stocks:
        record["analysis"] = analyze_stock(record["info"], record["news"])
        time.sleep(0.2)

    export_sample_json(global_news, macro, stocks)
    report_path = save_report(global_news, macro, stocks, global_analysis)
    print(f"Report saved: {report_path}")
    return report_path


if __name__ == "__main__":
    generate_daily_report()
