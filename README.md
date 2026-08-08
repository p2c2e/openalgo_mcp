This is an MCP server for OpenAlgo - (logic is copied from https://github.com/marketcalls/openalgo )

It has been repackaged for use as a module without necessity of cloning repos and installing python script.

Requirements:
- Local 3.12 or higher Python 
- uvx installed

How to Install uvx (uv)
-----------------------

- **Universal (Windows, Linux, Mac):**
  ```sh
  pip install uv
  ```
- **Mac (with Homebrew):**
  ```sh
  brew install uv
  ```
- **Prebuilt binaries:**  
  Download from [uv releases](https://github.com/astral-sh/uv/releases) for your platform.

After installation, the `uvx` command will be available in your terminal.

Addition of an entry similar to below on your favorite MCP Client. The below is tested with Cline plugin on VSCode. 

``` 
 "openalgo": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uvx",
      "args": [
        "openalgo-mcp@latest",
        "YOUR-OPENALGO-KEY",
        "http://127.0.0.1:5000"
      ]
    }
```

Divergence from upstream
------------------------

This package talks to the OpenAlgo REST API (`/api/v1/*`) directly over `httpx`. It
deliberately does **not** depend on the `openalgo` Python library, so installs stay small
and work on musl/Alpine images (the library ships a Rust `abi3` core with no musllinux
wheel).

Consequence: the 9 upstream research tools that compute indicators locally via
`openalgo.ta` (`calculate_indicator`, `get_trend_snapshot`, `get_momentum_snapshot`,
`get_volatility_snapshot`, `get_support_resistance`, `detect_signals`,
`screen_instruments`, `multi_timeframe_analysis`, `correlation_beta`) are **not** included.
They are pure local math, not REST endpoints, so they cannot be proxied. Everything that
maps to an API endpoint is covered - 40 tools.

`get_historical_data` matches upstream behaviour: `start_date`/`end_date` are optional,
`bars` (default 20) or `lookback_days` size the window, epoch timestamps are normalised to
ISO 8601 (IST for intraday intervals), and the response carries `count`/`returned`/
`truncated` metadata.
