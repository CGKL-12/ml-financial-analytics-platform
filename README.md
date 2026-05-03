# AI Global + A-Share + US Equity Research System

An automated market intelligence system that generates daily HTML research reports covering:

- **Global macro and market headlines**
- **China A-share watchlist analysis**
- **Optional US equity watchlist analysis**
- **Local LLM-powered investment commentary** using Ollama / Qwen

This project was redesigned to use safer data access patterns (RSS feeds and public APIs instead of web scraping), making it more suitable for production use and GitHub distribution.

---

## Why this version is compliance-conscious

The system was intentionally designed to minimize legal and ethical risks:

- It does **not** scrape or redistribute full news articles.
- It stores only **headline metadata**: title, source, publish time, URL, and short RSS summary if provided.
- It always links back to the original publisher instead of copying content.
- It uses only public RSS feeds and official APIs (`yfinance`, Google News RSS).
- It includes explicit educational-use disclaimers in generated reports.

> **Note:** This is not legal advice. Users are responsible for complying with each data provider's terms. See Disclaimer below.

---

## ⚠️ Important Disclaimer

**This project is for educational research purposes only. It does NOT constitute investment advice.**

Users are solely responsible for:

1. **Complying with Terms of Service** of all data providers (Yahoo Finance, Google News RSS, Ollama, etc.)
2. **Verifying data accuracy** before using it for any financial decisions
3. **Understanding LLM limitations** — AI-generated market analysis may be incorrect or misleading
4. **Consulting professionals** — Always speak with qualified financial advisors before making investment decisions

**The authors make NO warranties** about:
- Data accuracy or completeness
- Timeliness of news or price information
- Suitability for any particular purpose
- Fitness for trading or investment decisions

**By using this software, you assume all risks and agree that the authors are not liable for any losses, damages, or consequences.**

---

## Key Features

### 1. Global Market Intelligence

The system tracks global themes through RSS/headline queries, including:

- Global equity markets
- Federal Reserve / rates / inflation
- China economy and A-share policy
- AI semiconductors
- Electric vehicles and batteries
- Gold, oil, USD/CNY, and commodities

### 2. A-Share Watchlist

Default A-share coverage includes:

- 贵州茅台
- 五粮液
- 浪潮信息
- 紫光股份
- 宁德时代
- 中国平安
- 招商银行
- 海光信息
- 黄金ETF

Each stock report includes:

- Price and daily change
- PE / PB if available
- 52-week range
- Headline signals
- Local LLM-generated Chinese analysis

### 3. Optional US Watchlist

US stock coverage is enabled by default and can be disabled in `config.py`.

Default US watchlist:

- AAPL
- MSFT
- NVDA
- TSLA
- JPM

### 4. Local LLM Analysis

The system uses Ollama locally with Qwen2.5:

```bash
ollama pull qwen2.5:14b
ollama serve
```

Default model:

```python
MODEL = "qwen2.5:14b"
```

You can change this in `config.py`.

---

## Project Structure

```text
AI-Global-Ashare-US-Research-System/
├── main.py                 # One-click runnable entry point
├── config.py               # Watchlists, model config, RSS topics
├── requirements.txt        # pip dependencies
├── environment.yml         # conda environment
├── reports/                # generated HTML reports
├── examples/               # generated sample JSON payload
├── docs/                   # notes / screenshots / future documentation
├── LICENSE
├── .gitignore
└── README.md
```

---

## Quick Start

### Option A: Use your existing environment

From the project root:

```bash
pip install -r requirements.txt
python main.py
```

### Option B: Create a fresh Conda environment

```bash
conda env create -f environment.yml
conda activate global-equity-research
python main.py
```

### Make sure Ollama is running

```bash
ollama pull qwen2.5:14b
ollama serve
```

Then run:

```bash
python main.py
```

The report will be saved to:

```text
reports/global_equity_report_YYYY-MM-DD.html
```

---

## Configuration

Edit `config.py`.

### Change A-share watchlist

```python
A_SHARE_WATCHLIST = [
    ("600519", "600519.SS", "贵州茅台", "消费/白酒"),
    ("300750", "300750.SZ", "宁德时代", "新能源/电动车"),
]
```

### Disable US stocks

```python
ENABLE_US_STOCKS = False
```

### Change US watchlist

```python
US_WATCHLIST = [
    ("NVDA", "NVIDIA", "AI Semiconductors"),
    ("MSFT", "Microsoft", "US Mega-cap Tech"),
]
```

### Change global news topics

```python
GLOBAL_NEWS_TOPICS = [
    ("Federal Reserve", "Federal Reserve interest rates inflation"),
    ("AI Semiconductors", "AI semiconductors NVIDIA chips datacenter"),
]
```

---

## Data Sources

This project intentionally uses only low-risk, public data access methods:

| Data Type | Source | Method | Notes |
|---|---|---|---|
| Stock prices & fundamentals | Yahoo Finance | `yfinance` API wrapper | Widely used, non-official but stable |
| Global news headlines | Google News RSS | Public RSS feed | Headlines only, no full-text scraping |
| Stock news headlines | Yahoo Finance | News API metadata | Links to original articles provided |
| LLM analysis | Ollama (local) | Local inference | No external API calls, user controls model |

**What do NOT do:**
- ❌ Scrape full news article bodies
- ❌ Republish copyrighted content
- ❌ Bypass paywalls or login systems
- ❌ Store publisher text datasets
- ❌ High-frequency crawling

---

## Compliance-Oriented Design

This project is designed to be safe for production and open-source distribution:

- **API-first architecture** — Uses official or widely-accepted data APIs
- **Metadata-only storage** — Stores headlines and links, not full articles
- **Source attribution** — All content links back to original publishers
- **Educational focus** — Clear disclaimers and research-only language
- **No API keys in code** — Configuration is data-only, no secrets
- **Local LLM** — No external AI API dependencies or logging

---

## Example Resume Bullets

### Data / Analytics Version

- Built an AI-powered global equity research automation system integrating public market data APIs, RSS headline feeds, and local LLM analysis to generate daily HTML research reports.
- Designed a compliance-conscious data pipeline that stores only headline metadata and source links, reducing copyright risk while preserving research signals.

### ML / MLOps Version

- Deployed a local LLM-based financial analysis workflow using Ollama and Qwen2.5, combining structured market data with news headline signals to produce automated equity research summaries.
- Implemented configurable watchlists, modular data ingestion, fault-tolerant report generation, and local inference settings optimized for consumer GPU environments.

### Finance / Quant Version

- Developed an equity research platform monitoring A-share and US equity watchlists using valuation metrics, 52-week positioning, global macro headlines, and sector-specific catalyst signals.

---

## Known Limitations

- **`yfinance` is unofficial** — Yahoo Finance does not officially support it; data may have delays or gaps
- **RSS feeds are unstable** — Feed formats change and sources may become unavailable
- **LLM output is unreliable** — AI-generated analysis can be factually incorrect
- **Headlines are signals, not evidence** — Always open original source links for full context
- **No real-time data** — Reports are batch-processed daily; prices lag real-time

---

## Security & Best Practices

- **Never hardcode secrets** — Use environment variables for any API keys
- **Verify critical data** — Cross-check prices/news with official sources before trading
- **Update dependencies** — Run `pip install --upgrade -r requirements.txt` regularly
- **Monitor Ollama** — Ensure local LLM is running and reachable before starting
- **Keep reports private** — Generated HTML may contain personal watchlists; store securely

---

## Contributing

We welcome contributions! Please ensure:

1. No new web scraping methods
2. Only official APIs or public RSS feeds
3. Clear documentation of data sources
4. Updated compliance disclaimers

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) file for details.

**IMPORTANT:** The MIT License includes an explicit disclaimer that the software is provided "as-is" with no warranties. For financial software, please also review the Additional Financial Disclaimer in the LICENSE file.

---

## Questions?

- **Data source issues?** Check `config.py` and ensure all APIs/feeds are reachable
- **LLM issues?** Ensure Ollama is running (`ollama serve`) and the model is downloaded
- **Report not generating?** Check console output for specific errors and verify Python 3.9+
- **Legal questions?** Consult a lawyer — this is not legal advice

---

## Acknowledgments

- [yfinance](https://github.com/ranaroussi/yfinance) — Market data
- [feedparser](https://github.com/kurtmckee/feedparser) — RSS parsing
- [Ollama](https://ollama.ai/) — Local LLM runtime
- [Google News](https://news.google.com) — Public RSS feeds


