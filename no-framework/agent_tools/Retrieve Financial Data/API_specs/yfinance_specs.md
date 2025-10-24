# yfinance Public API (Markdown Spec for LLM Tooling)

> **Goal:** One self‑contained `.md` file that an LLM (or human) can scan to understand what it can call, with clear signatures, param types, return types, and property names.
>
> **Version note:** This reflects the public surface from the current yfinance docs/GitHub (Raná Roussi). Minor changes may occur between releases.

---

## 0. How to Read This Spec

- **Function/Method blocks** follow:
  ```markdown
  object.path.name(param: type = default, ...) → return_type
  ```
- **Parameters** = inputs you pass when calling a function/method.
- **Properties** = attributes you *access* (no parentheses). They usually trigger a fetch under the hood and return cached results. Example:
  ```python
  t = yfinance.Ticker("AAPL")
  df = t.financials          # property (no parentheses)
  df2 = t.get_financials()   # method (explicit call)
  ```
- **Types** are indicative (pandas objects, dicts, etc.). Refer to actual runtime objects for exact schemas.
- **Ellipses (`…`)** means more kwargs accepted and forwarded internally.

---

## 1. Top‑Level Module Functions & Utilities

```markdown
yfinance.download(
    tickers,
    start=None, end=None,
    actions=False,
    threads=True,
    ignore_tz=None,
    group_by='column',
    auto_adjust=None,
    back_adjust=False,
    repair=False,
    keepna=False,
    progress=True,
    period=None,                # '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max'
    interval='1d',              # '1m','2m','5m','15m','30m','60m','90m','1h','1d','5d','1wk','1mo','3mo'
    prepost=False,
    proxy=_SENTINEL_,
    rounding=False,
    timeout=10,
    session=None,
    multi_level_index=True
) → pandas.DataFrame | None
```

```markdown
yfinance.screen(
    query,                      # EquityQuery/FundQuery object or raw dict
    offset=None, size=None, count=None,
    sortField=None, sortAsc=None,
    userId=None, userIdType=None,
    session=None, proxy=<object>
) → dict
```

```markdown
yfinance.enable_debug_mode() → None
yfinance.set_config(proxy=None) → None
yfinance.set_tz_cache_location(path: str) → None
```

---

## 2. Core Classes

### 2.1 `Ticker`
```markdown
class yfinance.Ticker(ticker: str, session=None, proxy=<object>)
```

#### 2.1.1 Properties (read-only attributes)
Access without parentheses. Most return `pandas.DataFrame` or `dict`.

```
actions
analyst_price_targets
balance_sheet
calendar
capital_gains
cashflow
dividends
earnings
earnings_dates
earnings_estimate
earnings_history
eps_revisions
eps_trend
fast_info
financials
funds_data
growth_estimates
history_metadata
income_stmt
info
insider_purchases
insider_roster_holders
insider_transactions
institutional_holders
isin
major_holders
mutualfund_holders
news
options                      # list[str] of option expiration dates
quarterly_balance_sheet
quarterly_cashflow
quarterly_earnings
quarterly_financials
quarterly_income_stmt
recommendations
recommendations_summary
revenue_estimate
sec_filings
shares
splits
sustainability
ttm_cashflow
ttm_financials
ttm_income_stmt
upgrades_downgrades
```

#### 2.1.2 Public Methods

```markdown
history(
    period=None, interval='1d',
    start=None, end=None,
    prepost=False,
    actions=True, auto_adjust=True,
    back_adjust=False, repair=False,
    keepna=False,
    proxy=_SENTINEL_,
    rounding=False,
    timeout=10,
    raise_errors=False
) → pandas.DataFrame
```

```markdown
option_chain(date=None, tz=None) → OptionChain
```

```markdown
live(message_handler=None, verbose=True) → None
```

##### “get_” Accessor Methods (explicit fetchers)
All usually accept `as_dict=False` (to get DataFrame) or `pretty=False` flags where relevant.

```markdown
get_actions(period='max')
get_analyst_price_targets()
get_balance_sheet(as_dict=False, pretty=False, freq='yearly')
get_cashflow(as_dict=False, pretty=False, freq='yearly')
get_capital_gains(period='max')
get_dividends(period='max')
get_earnings(as_dict=False, freq='yearly'|'quarterly'|'trailing')
get_earnings_dates(limit=12)
get_earnings_estimate(as_dict=False)
get_earnings_history(as_dict=False)
get_eps_revisions(as_dict=False)
get_eps_trend(as_dict=False)
get_fast_info()
get_financials(as_dict=False, pretty=False, freq='yearly')
get_funds_data()
get_growth_estimates(as_dict=False)
get_history_metadata()
get_income_stmt(as_dict=False, pretty=False, freq='yearly'|'quarterly'|'trailing')
get_info()
get_insider_purchases(as_dict=False)
get_insider_transactions(as_dict=False)
get_insider_roster_holders(as_dict=False)
get_institutional_holders(as_dict=False)
get_isin()
get_major_holders(as_dict=False)
get_mutualfund_holders(as_dict=False)
get_news(count=10, tab='news'|'all'|'press releases')
get_recommendations(as_dict=False)
get_recommendations_summary(as_dict=False)
get_revenue_estimate(as_dict=False)
get_sec_filings()
get_shares(as_dict=False)
get_shares_full(start=None, end=None)
get_splits(period='max')
get_sustainability(as_dict=False)
get_upgrades_downgrades(as_dict=False)
```

---

### 2.2 `Tickers`
```markdown
class yfinance.Tickers(tickers: str | list[str], session=None)
```

#### Methods
```markdown
download(...same args as yfinance.download...) → pandas.DataFrame
history(...same args as Ticker.history...) → dict[str, pandas.DataFrame]
live(message_handler=None, verbose=True) → None
news() → dict
```

---

### 2.3 `Market`
```markdown
class yfinance.Market(market: str, session=None, proxy=<object>, timeout=30)
```

- **Properties:** `status`, `summary` (dicts)
- Instantiation performs the fetch; no extra public methods.

---

### 2.4 Search & Lookup Classes

#### 2.4.1 `Search`
```markdown
class yfinance.Search(
    query,
    max_results=8, news_count=8, lists_count=8,
    include_cb=True, include_nav_links=False,
    include_research=False, include_cultural_assets=False,
    enable_fuzzy_query=False,
    recommended=8,
    session=None, proxy=<object>, timeout=30,
    raise_errors=True
)
```
- **Method:** `search()` → `Search` (executes and populates properties)
- **Properties:** `all, lists, nav, news, quotes, research, response` (dicts/lists)

#### 2.4.2 `Lookup`
```markdown
class yfinance.Lookup(query: str, session=None, proxy=<object>, timeout=30, raise_errors=True)
```

- **Getter methods** (each returns `pandas.DataFrame`):
  - `get_all(count=25)`
  - `get_stock(count=25)`
  - `get_etf(count=25)`
  - `get_index(count=25)`
  - `get_currency(count=25)`
  - `get_future(count=25)`
  - `get_mutualfund(count=25)`
  - `get_cryptocurrency(count=25)`
- **Properties:** `all, stock, etf, index, currency, future, mutualfund, cryptocurrency`

---

### 2.5 Streaming / WebSockets

#### 2.5.1 `WebSocket`
```markdown
class yfinance.WebSocket(url='wss://streamer.finance.yahoo.com/?version=2', verbose=True)
```
- `listen(message_handler=None)` → None
- `subscribe(symbols: list[str] | str)` → None
- `unsubscribe(symbols: list[str] | str)` → None
- `close()` → None

#### 2.5.2 `AsyncWebSocket`
```markdown
class yfinance.AsyncWebSocket(url='wss://streamer.finance.yahoo.com/?version=2', verbose=True)
```
- `listen(message_handler=None)` (async)
- `subscribe(symbols)` / `unsubscribe(symbols)` (async)
- `close()` (async)

---

### 2.6 Screener DSL (Query Builders)

#### Base Concept
- Build structured queries instead of raw dicts for `yfinance.screen()`.
- Logical operators: `AND`, `OR`
- Comparison ops: `EQ`, `IS-IN`, `BTWN`, `GT`, `LT`, `GTE`, `LTE`

#### 2.6.1 `EquityQuery`
```markdown
class yfinance.EquityQuery(operator: str, operand: list[QueryBase] | tuple[str, tuple[Any,...]])
```
- Class attributes: `valid_fields`, `valid_values` (dicts of allowed keys)

#### 2.6.2 `FundQuery`
```markdown
class yfinance.FundQuery(operator: str, operand: list[QueryBase] | tuple[str, tuple[Any,...]])
```
- Similar semantics, different field lists.

---

### 2.7 Domain / Helper Classes

- `OptionChain` – returned by `Ticker.option_chain()`. Exposes `.calls` and `.puts` DataFrames.
- `FundsData` – structured return from `Ticker.get_funds_data()`.
- `PriceHistory` – internal wrapper used by `.history()`.
- `Sector`, `Industry` – simple containers for sector/industry data.

(These have small, obvious attribute surfaces; see source for nested keys.)

---

## 3. Patterns & Best Practices for LLMs

1. **Prefer explicit `get_` methods** when you need deterministic I/O. Properties are fine but hide side effects.
2. **Validate enums & ranges** (e.g., `interval`, `freq`) before calling.
3. **Chunk large tickers lists** for `download/quote` style endpoints to avoid 414 URI errors or server throttling.
4. **Cache results**—yfinance doesn’t aggressively cache between runs.
5. **Handle missing fields**—Yahoo frequently omits values; check for `None`/empty frames.

---

## 4. Minimal JSON Schema Template (Optional)
If you’re wrapping these for tools/functions:

```json
{
  "name": "yfinance_download",
  "description": "Fetch historical OHLCV data from Yahoo Finance via yfinance.download",
  "parameters": {
    "type": "object",
    "properties": {
      "tickers": {"type": "string", "description": "Ticker or comma-separated tickers"},
      "period": {"type": "string", "enum": ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"]},
      "interval": {"type": "string", "enum": ["1m","2m","5m","15m","30m","60m","90m","1h","1d","5d","1wk","1mo","3mo"]},
      "start": {"type": "string", "format": "date"},
      "end": {"type": "string", "format": "date"},
      "prepost": {"type": "boolean"},
      "actions": {"type": "boolean"}
    },
    "required": ["tickers"]
  }
}
```

(Replicate for other high-use methods as needed.)

---

## 5. Glossary

- **Property (attribute):** A value you read from an object without calling it like a function. In Python, properties can run code lazily, but usage looks like `obj.name`, not `obj.name()`.
- **Method:** A function bound to an object; you call it with parentheses and arguments.
- **DataFrame:** pandas 2D table. Serialize to JSON/CSV if sending through an LLM tool.
- **OptionChain:** yfinance object with `.calls`/`.puts` DataFrames.

---

*End of file.*

