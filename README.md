# OpenAlgo MCP Server

This is a Model Context Protocol (MCP) server that provides trading and market data functionality through the OpenAlgo platform. It enables AI assistants to execute trades, manage positions, and retrieve market data directly from supported brokers.

## Quick Start: Use Without Cloning

You can use this MCP server directly from GitHub—**no need to clone the repository manually**.

### 1. Install Directly from GitHub

If you have [uv](https://github.com/astral-sh/uv) (recommended) or pip:

```sh
uv pip install "git+https://github.com/yourusername/openalgo-mcp.git"
# or, with pip:
pip install "git+https://github.com/yourusername/openalgo-mcp.git"
```

- This will install the server and all dependencies into your current environment.
- **Requires Python 3.12+**

### 2. Run the MCP Server

After installation, you can start the server with:

```sh
uvx -m mcp.mcpserver YOUR_API_KEY_HERE http://127.0.0.1:5000
```
or, if using pip:
```sh
python -m mcp.mcpserver YOUR_API_KEY_HERE http://127.0.0.1:5000
```

- Replace `YOUR_API_KEY_HERE` and the URL as needed.
- If a CLI entry point is provided (e.g. `openalgo-mcp-server`), you can run:
  ```sh
  openalgo-mcp-server YOUR_API_KEY_HERE http://127.0.0.1:5000
  ```

### 3. (Alternative) Use pipx

If the repo provides a CLI entry point, you can run directly with [pipx](https://pipx.pypa.io/):

```sh
pipx run "git+https://github.com/yourusername/openalgo-mcp.git" -- YOUR_API_KEY_HERE http://127.0.0.1:5000
```

---

## Prerequisites

### 1. Python Version

- **Python 3.12 or higher is required.**  
  This MCP server is only supported on Python 3.12+ due to dependency and language feature requirements.

### 2. OpenAlgo Server Setup

Ensure your OpenAlgo server is running and properly configured:

1. **Start OpenAlgo Server**: Your OpenAlgo server should be running (e.g., on `http://127.0.0.1:5000`)
2. **Verify Connection**: Test that the server is accessible by visiting the web interface.
3. **Broker Authentication**: Ensure your broker credentials are properly configured in OpenAlgo.

### 3. API Key

To get your OpenAlgo API key:
1. Open your OpenAlgo web interface (e.g., `http://127.0.0.1:5000`)
2. Navigate to **Settings → API Keys**.
3. Generate or copy your existing API key.

### 4. (Recommended) Install [uv](https://github.com/astral-sh/uv)

- [uv](https://github.com/astral-sh/uv) is a fast Python package manager and runner that provides the `uvx` command, a drop-in replacement for `python`/`python3` for running scripts in virtual environments.
- Using `uvx` simplifies configuration and ensures the correct Python version/environment is used.
- Install with:  
  ```sh
  pip install uv
  ```
  or see the [uv installation guide](https://github.com/astral-sh/uv#installation).

## MCP Client Configuration

You can configure your MCP client to use either the traditional Python executable path or the modern [uvx](https://github.com/astral-sh/uv) runner.  
**uvx is recommended** for simplicity and reliability, and works cross-platform.

### Using `uvx` (Recommended, All Platforms)

**Example Configuration:**
```json
{
  "mcpServers": {
    "openalgo": {
      "command": "uvx",
      "args": [
        "mcp/mcpserver.py",
        "YOUR_API_KEY_HERE",
        "http://127.0.0.1:5000"
      ]
    }
  }
}
```
- This will run the server using the Python interpreter from your current virtual environment (must be Python 3.12+).
- Make sure to run your MCP client from the project root, or adjust the path to `mcp/mcpserver.py` as needed.

### Using Python Executable Path (Legacy/Alternative)

If you prefer to specify the Python executable directly, use the following examples for your OS:

#### Windows

```json
{
  "mcpServers": {
    "openalgo": {
      "command": "D:\\openalgo-mcp\\openalgo\\.venv\\Scripts\\python.exe",
      "args": [
        "D:\\openalgo-mcp\\openalgo\\mcp\\mcpserver.py",
        "YOUR_API_KEY_HERE",
        "http://127.0.0.1:5000"
      ]
    }
  }
}
```

#### macOS

```json
{
  "mcpServers": {
    "openalgo": {
      "command": "/Users/your_username/openalgo/.venv/bin/python3",
      "args": [
        "/Users/your_username/openalgo/mcp/mcpserver.py",
        "YOUR_API_KEY_HERE",
        "http://127.0.0.1:5000"
      ]
    }
  }
}
```

#### Linux

```json
{
  "mcpServers": {
    "openalgo": {
      "command": "/home/your_username/openalgo/.venv/bin/python3",
      "args": [
        "/home/your_username/openalgo/mcp/mcpserver.py",
        "YOUR_API_KEY_HERE",
        "http://127.0.0.1:5000"
      ]
    }
  }
}
```

### Configuration File Locations

- **Claude Desktop**:  
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Linux: `~/.config/Claude/claude_desktop_config.json`
- **Windsurf**:  
  - Windows: `%APPDATA%\Windsurf\mcp_config.json`
  - macOS: `~/.config/windsurf/mcp_config.json`
  - Linux: `~/.config/windsurf/mcp_config.json`
- **Cursor**:  
  - Windows: `%APPDATA%\Cursor\User\settings.json`
  - macOS: `~/Library/Application Support/Cursor/User/settings.json`
  - Linux: `~/.config/Cursor/User/settings.json`

### Path Configuration Notes

- **Important**: Replace the paths in the examples above with your actual installation paths.
- If using `uvx`, ensure you are in the correct project directory or adjust the script path accordingly.
- If using the Python executable path, ensure it points to a Python 3.12+ interpreter in your virtual environment.

### ChatGPT Configuration (Platform Independent)

If your ChatGPT client supports MCP, use the appropriate path format for your operating system from the examples above.

## Available Tools

The MCP server provides the following categories of tools:

### Order Management
- `place_order` - Place market or limit orders
- `place_smart_order` - Place orders considering position size
- `place_basket_order` - Place multiple orders at once
- `place_split_order` - Split large orders into smaller chunks
- `modify_order` - Modify existing orders
- `cancel_order` - Cancel specific orders
- `cancel_all_orders` - Cancel all orders for a strategy

### Position Management
- `close_all_positions` - Close all positions for a strategy
- `get_open_position` - Get current position for an instrument

### Order Status & Tracking
- `get_order_status` - Check status of specific orders
- `get_order_book` - View all orders
- `get_trade_book` - View executed trades
- `get_position_book` - View current positions
- `get_holdings` - View long-term holdings
- `get_funds` - Check account funds and margins

### Market Data
- `get_quote` - Get current price quotes
- `get_market_depth` - Get order book depth
- `get_historical_data` - Retrieve historical price data

### Instrument Search
- `search_instruments` - Search for trading instruments
- `get_symbol_info` - Get detailed symbol information
- `get_expiry_dates` - Get derivative expiry dates
- `get_available_intervals` - List available time intervals

### Utilities
- `get_openalgo_version` - Check OpenAlgo version
- `validate_order_constants` - Display valid order parameters

## Usage Examples

Once configured, you can ask your AI assistant to:

- "Place a buy order for 100 shares of RELIANCE at market price"
- "Show me my current positions"
- "Get the latest quote for NIFTY"
- "Cancel all my pending orders"
- "What are my account funds?"

## Supported Exchanges

- **NSE** - National Stock Exchange (Equity)
- **NFO** - NSE Futures & Options
- **CDS** - NSE Currency Derivatives
- **BSE** - Bombay Stock Exchange
- **BFO** - BSE Futures & Options
- **BCD** - BSE Currency Derivatives
- **MCX** - Multi Commodity Exchange
- **NCDEX** - National Commodity & Derivatives Exchange

## Security Note

⚠️ **Important**: This server is designed for local use. For production environments, consider implementing additional security measures such as environment variables for sensitive data and restricting network access.

## Troubleshooting

1. **Connection Issues**: Verify OpenAlgo server is running on `http://127.0.0.1:5000`
2. **Authentication Errors**: Check your API key is correct and valid
3. **Permission Errors**: Ensure the Python virtual environment has proper permissions
4. **Order Failures**: Verify your broker connection and trading permissions
4. **Order Failures**: Verify broker credentials in OpenAlgo are valid and active

## Support

For issues related to:
- **OpenAlgo Platform**: Visit the OpenAlgo documentation
- **MCP Protocol**: Check the Model Context Protocol specifications
- **Trading Errors**: Verify your broker connection and trading permissions
