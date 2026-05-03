"""Project configuration.

Edit this file to change tracked markets, RSS topics, LLM model, and output settings.
This version intentionally uses headline/RSS/API style inputs instead of copying full news articles.
"""

OUTPUT_DIR = "./reports"
TIMEZONE = "America/Toronto"
KEEP_DAYS = 14

# Local LLM runtime. Make sure Ollama is running and the model has been pulled:
# ollama pull qwen2.5:14b
MODEL = "qwen2.5:14b"
LLM_OPTIONS = {
    "temperature": 0.5,
    "num_ctx": 8192,
    "num_gpu": 35,
}

# A-share watchlist: (A-share code, Yahoo ticker, Chinese name, sector)
A_SHARE_WATCHLIST = [
    ("600519", "600519.SS", "贵州茅台", "消费/白酒"),
    ("000858", "000858.SZ", "五粮液", "消费/白酒"),
    ("000977", "000977.SZ", "浪潮信息", "科技/算力"),
    ("000938", "000938.SZ", "紫光股份", "科技/半导体"),
    ("300750", "300750.SZ", "宁德时代", "新能源/电动车"),
    ("601318", "601318.SS", "中国平安", "金融/保险"),
    ("600036", "600036.SS", "招商银行", "金融/银行"),
    ("688041", "688041.SS", "海光信息", "科技/国产芯片"),
    ("518880", "518880.SS", "黄金ETF", "贵金属"),
]

# Optional US stock coverage. Set ENABLE_US_STOCKS = False to disable.
ENABLE_US_STOCKS = True
US_WATCHLIST = [
    ("AAPL", "Apple", "US Mega-cap Tech"),
    ("MSFT", "Microsoft", "US Mega-cap Tech"),
    ("NVDA", "NVIDIA", "AI Semiconductors"),
    ("TSLA", "Tesla", "EV / Clean Energy"),
    ("JPM", "JPMorgan Chase", "US Financials"),
]

# Macro indices tracked through Yahoo Finance.
MACRO_TICKERS = [
    ("000001.SS", "上证指数"),
    ("399001.SZ", "深证成指"),
    ("399006.SZ", "创业板指"),
    ("^GSPC", "S&P 500"),
    ("^IXIC", "Nasdaq Composite"),
    ("^DJI", "Dow Jones"),
    ("GC=F", "Gold Futures"),
    ("CL=F", "WTI Crude Oil"),
    ("USDCNY=X", "USD/CNY"),
]

# RSS / headline topics. Google News RSS is used as a configurable public RSS feed.
# You can replace these URLs with Reuters, official exchange RSS, company IR RSS, etc.
GLOBAL_NEWS_TOPICS = [
    ("Global Markets", "global markets stock market economy"),
    ("Federal Reserve", "Federal Reserve interest rates inflation"),
    ("China Economy", "China economy A shares policy"),
    ("AI Semiconductors", "AI semiconductors NVIDIA chips datacenter"),
    ("EV Battery", "electric vehicles battery lithium China"),
    ("Gold Oil FX", "gold oil dollar yuan market"),
]

# Report limits.
MAX_GLOBAL_HEADLINES_PER_TOPIC = 5
MAX_STOCK_HEADLINES = 5
