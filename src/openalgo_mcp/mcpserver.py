
import nest_asyncio

nest_asyncio.apply()

from fastmcp import FastMCP
import httpx
from typing import List, Dict, Any, Optional
import json
import sys
import asyncio
import concurrent.futures
import threading
from urllib.parse import urlparse


# Get API key and host from command line arguments
if len(sys.argv) < 3:
    raise ValueError("API key and host must be provided as command line arguments")

api_key = sys.argv[1]
host = sys.argv[2]

print("APIKEY : ", api_key)
print("Host   : ", host)

# Ensure host ends with /
if not host.endswith('/'):
    host += '/'

# Create MCP server
mcp = FastMCP("openalgo")

# HTTP Client class for OpenAlgo API
class OpenAlgoHTTPClient:
    def __init__(self, api_key: str, host: str):
        parsed = urlparse(host)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        self.api_key = api_key
        self.base_url = f"{host}api/v1/"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Origin": origin,
            "Referer": f"{origin}/",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest"
        }
    
    async def _make_request(self, endpoint: str, data: dict) -> dict:
        """Make HTTP POST request to OpenAlgo API"""
        # Add API key to request data
        data["apikey"] = self.api_key
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0,
            http2=True,
            follow_redirects=True
        ) as client:
            try:
                response = await client.post(endpoint, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                body = ""
                try:
                    body = e.response.text if e.response is not None else ""
                except Exception:
                    pass
                status = e.response.status_code if e.response is not None else "unknown"
                reason = e.response.reason_phrase if e.response is not None else "unknown"
                url_info = str(e.request.url) if e.request is not None else url
                raise Exception(f"HTTP request failed: {status} {reason} for url '{url_info}' - Response body: {body[:500]}")
            except httpx.HTTPError as e:
                raise Exception(f"HTTP request failed: {str(e)}")
            except Exception as e:
                raise Exception(f"Request error: {str(e)}")

# Initialize HTTP client
http_client = OpenAlgoHTTPClient(api_key, host)

# Helper function to run async functions
def run_async(coro):
    """Run async function in sync context, safe for nested event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop is running, safe to use asyncio.run
        return asyncio.run(coro)
    else:
        # If we're already in an event loop, run in a new thread with its own event loop
        import queue

        q = queue.Queue()

        def thread_worker():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result = new_loop.run_until_complete(coro)
                q.put((result, None))
            except Exception as e:
                q.put((None, e))
            finally:
                new_loop.close()

        t = threading.Thread(target=thread_worker)
        t.start()
        result, error = q.get()
        t.join()
        if error:
            raise error
        return result

# ORDER MANAGEMENT TOOLS

@mcp.tool()
def place_order(
    symbol: str, 
    quantity: int, 
    action: str, 
    exchange: str = "NSE", 
    price_type: str = "MARKET", 
    product: str = "MIS", 
    strategy: str = "Python",
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None
) -> str:
    """
    Place a new order (market or limit).
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE')
        quantity: Number of shares
        action: 'BUY' or 'SELL'
        exchange: 'NSE', 'NFO', 'CDS', 'BSE', 'BFO', 'BCD', 'MCX', 'NCDEX'
        price_type: 'MARKET', 'LIMIT', 'SL', 'SL-M'
        product: 'CNC', 'NRML', 'MIS'
        strategy: Strategy name
        price: Limit price (required for LIMIT orders)
        trigger_price: Trigger price (for stop loss orders)
        disclosed_quantity: Disclosed quantity
    """
    try:
        data = {
            "strategy": strategy,
            "symbol": symbol.upper(),
            "action": action.upper(),
            "exchange": exchange.upper(),
            "pricetype": price_type.upper(),  # Note: API uses 'pricetype' not 'price_type'
            "product": product.upper(),
            "quantity": str(quantity)  # API expects string
        }
        
        if price is not None:
            data["price"] = str(price)
        if trigger_price is not None:
            data["trigger_price"] = str(trigger_price)
        if disclosed_quantity is not None:
            data["disclosed_quantity"] = str(disclosed_quantity)
            
        response = run_async(http_client._make_request("placeorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error placing order: {str(e)}"

@mcp.tool()
def place_smart_order(
    symbol: str, 
    quantity: int, 
    action: str, 
    position_size: int,
    exchange: str = "NSE", 
    price_type: str = "MARKET", 
    product: str = "MIS", 
    strategy: str = "Python",
    price: Optional[float] = None
) -> str:
    """
    Place a smart order considering current position size.
    
    Args:
        symbol: Stock symbol
        quantity: Number of shares
        action: 'BUY' or 'SELL'
        position_size: Current position size
        exchange: Exchange name
        price_type: Order type
        product: Product type
        strategy: Strategy name
        price: Limit price (optional)
    """
    try:
        data = {
            "strategy": strategy,
            "symbol": symbol.upper(),
            "action": action.upper(),
            "exchange": exchange.upper(),
            "pricetype": price_type.upper(),
            "product": product.upper(),
            "quantity": str(quantity),
            "position_size": str(position_size)
        }
        
        if price is not None:
            data["price"] = str(price)
        else:
            data["price"] = "0"
            
        # Add default values as seen in Postman collection
        data["trigger_price"] = "0"
        data["disclosed_quantity"] = "0"
            
        response = run_async(http_client._make_request("placesmartorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error placing smart order: {str(e)}"

@mcp.tool()
def place_basket_order(orders_json: str) -> str:
    """
    Place multiple orders in a basket.
    
    Args:
        orders_json: JSON string containing list of orders
        Example: '[{"symbol": "BHEL", "exchange": "NSE", "action": "BUY", "quantity": 1, "pricetype": "MARKET", "product": "MIS"}]'
    """
    try:
        orders = json.loads(orders_json)
        data = {
            "strategy": "Python",  # Default strategy
            "orders": orders
        }
        
        response = run_async(http_client._make_request("basketorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error placing basket order: {str(e)}"

@mcp.tool()
def place_split_order(
    symbol: str,
    quantity: int,
    split_size: int,
    action: str,
    exchange: str = "NSE",
    price_type: str = "MARKET",
    product: str = "MIS",
    price: Optional[float] = None
) -> str:
    """
    Place an order split into smaller chunks.
    
    Args:
        symbol: Stock symbol
        quantity: Total quantity to trade
        split_size: Size of each split order
        action: 'BUY' or 'SELL'
        exchange: Exchange name
        price_type: Order type
        product: Product type
        price: Limit price (optional)
    """
    try:
        data = {
            "strategy": "Python",  # Default strategy
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "action": action.upper(),
            "quantity": str(quantity),
            "splitsize": str(split_size),
            "pricetype": price_type.upper(),
            "product": product.upper()
        }
        
        if price is not None:
            data["price"] = str(price)
            
        response = run_async(http_client._make_request("splitorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error placing split order: {str(e)}"

@mcp.tool()
def modify_order(
    order_id: str,
    strategy: str,
    symbol: str,
    action: str,
    exchange: str,
    price_type: str,
    product: str,
    quantity: int,
    price: Optional[float] = None
) -> str:
    """
    Modify an existing order.
    
    Args:
        order_id: Order ID to modify
        strategy: Strategy name
        symbol: Stock symbol
        action: 'BUY' or 'SELL'
        exchange: Exchange name
        price_type: Order type
        product: Product type
        quantity: New quantity
        price: New price (optional)
    """
    try:
        data = {
            "orderid": order_id,  # Note: API uses 'orderid' not 'order_id'
            "strategy": strategy,
            "symbol": symbol.upper(),
            "action": action.upper(),
            "exchange": exchange.upper(),
            "pricetype": price_type.upper(),
            "product": product.upper(),
            "quantity": str(quantity),
            "disclosed_quantity": "0",
            "trigger_price": "0"
        }
        
        if price is not None:
            data["price"] = str(price)
            
        response = run_async(http_client._make_request("modifyorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error modifying order: {str(e)}"

@mcp.tool()
def cancel_order(order_id: str, strategy: str) -> str:
    """
    Cancel a specific order.
    
    Args:
        order_id: Order ID to cancel
        strategy: Strategy name
    """
    try:
        data = {
            "orderid": order_id,  # Note: API uses 'orderid' not 'order_id'
            "strategy": strategy
        }
        
        response = run_async(http_client._make_request("cancelorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error canceling order: {str(e)}"

@mcp.tool()
def cancel_all_orders(strategy: str) -> str:
    """
    Cancel all open orders for a strategy.
    
    Args:
        strategy: Strategy name
    """
    try:
        data = {
            "strategy": strategy
        }
        
        response = run_async(http_client._make_request("cancelallorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error canceling all orders: {str(e)}"

# POSITION MANAGEMENT TOOLS

@mcp.tool()
def close_all_positions(strategy: str) -> str:
    """
    Close all open positions for a strategy.
    
    Args:
        strategy: Strategy name
    """
    try:
        data = {
            "strategy": strategy
        }
        
        response = run_async(http_client._make_request("closeposition", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error closing positions: {str(e)}"

@mcp.tool()
def get_open_position(strategy: str, symbol: str, exchange: str, product: str) -> str:
    """
    Get current open position for a specific instrument.
    
    Args:
        strategy: Strategy name
        symbol: Stock symbol
        exchange: Exchange name
        product: Product type
    """
    try:
        data = {
            "strategy": strategy,
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "product": product.upper()
        }
        
        response = run_async(http_client._make_request("openposition", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting open position: {str(e)}"

# ORDER STATUS AND TRACKING TOOLS

@mcp.tool()
def get_order_status(order_id: str, strategy: str) -> str:
    """
    Get status of a specific order.
    
    Args:
        order_id: Order ID
        strategy: Strategy name
    """
    try:
        data = {
            "orderid": order_id,  # Note: API uses 'orderid' not 'order_id'
            "strategy": strategy
        }
        
        response = run_async(http_client._make_request("orderstatus", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting order status: {str(e)}"

@mcp.tool()
def get_order_book() -> str:
    """Get all orders from the order book."""
    try:
        data = {}  # Only API key is needed
        
        response = run_async(http_client._make_request("orderbook", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting order book: {str(e)}"

@mcp.tool()
def get_trade_book() -> str:
    """Get all executed trades."""
    try:
        data = {}  # Only API key is needed
        
        response = run_async(http_client._make_request("tradebook", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting trade book: {str(e)}"

@mcp.tool()
def get_position_book() -> str:
    """Get all current positions."""
    try:
        data = {}  # Only API key is needed
        
        response = run_async(http_client._make_request("positionbook", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting position book: {str(e)}"

@mcp.tool()
def get_holdings() -> str:
    """Get all holdings (long-term investments)."""
    try:
        data = {}  # Only API key is needed
        response = run_async(http_client._make_request("holdings", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting holdings: {str(e)}"

@mcp.tool()
def get_funds() -> str:
    """Get account funds and margin information."""
    try:
        data = {}  # Only API key is needed
        
        response = run_async(http_client._make_request("funds", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting funds: {str(e)}"

# MARKET DATA TOOLS

@mcp.tool()
def get_quote(symbol: str, exchange: str = "NSE") -> str:
    """
    Get current quote for a symbol.
    
    Args:
        symbol: Stock symbol
        exchange: Exchange name
    """
    try:
        data = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper()
        }
        
        response = run_async(http_client._make_request("quotes", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting quote: {str(e)}"

@mcp.tool()
def get_market_depth(symbol: str, exchange: str = "NSE") -> str:
    """
    Get market depth (order book) for a symbol.
    
    Args:
        symbol: Stock symbol
        exchange: Exchange name
    """
    try:
        data = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper()
        }
        
        response = run_async(http_client._make_request("depth", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting market depth: {str(e)}"

@mcp.tool()
def get_historical_data(
    symbol: str,
    exchange: str,
    interval: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Get historical price data.
    
    Args:
        symbol: Stock symbol
        exchange: Exchange name
        interval: Time interval ('1m', '3m', '5m', '10m', '15m', '30m', '1h', 'D')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    try:
        data = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = run_async(http_client._make_request("history", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting historical data: {str(e)}"

# INSTRUMENT SEARCH AND INFO TOOLS

@mcp.tool()
def search_instruments(query: str, exchange: str = "NSE", instrument_type: Optional[str] = None) -> str:
    """
    Search for instruments by name or symbol.
    
    Args:
        query: Search query
        exchange: Exchange to search in (NSE, BSE, NSE_INDEX, BSE_INDEX, etc.)
        instrument_type: Optional - 'INDEX' to search in index exchanges
    """
    try:
        # Handle index searches
        if instrument_type and instrument_type.upper() == "INDEX":
            if exchange.upper() == "NSE":
                exchange = "NSE_INDEX"
            elif exchange.upper() == "BSE":
                exchange = "BSE_INDEX"
        
        data = {
            "query": query,
            "exchange": exchange.upper()
        }
        
        response = run_async(http_client._make_request("search", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error searching instruments: {str(e)}"

@mcp.tool()
def get_symbol_info(symbol: str, exchange: str = "NSE", instrument_type: Optional[str] = None) -> str:
    """
    Get detailed information about a symbol.
    
    Args:
        symbol: Stock symbol
        exchange: Exchange name
        instrument_type: Optional - 'INDEX' for index symbols
    """
    try:
        # Handle index symbols
        if instrument_type and instrument_type.upper() == "INDEX":
            if exchange.upper() == "NSE":
                exchange = "NSE_INDEX"
            elif exchange.upper() == "BSE":
                exchange = "BSE_INDEX"
        
        # Or check if symbol is a known index
        nse_indices = ["NIFTY", "NIFTYNXT50", "FINNIFTY", "BANKNIFTY", "MIDCPNIFTY", "INDIAVIX"]
        bse_indices = ["SENSEX", "BANKEX", "SENSEX50"]
        
        if symbol.upper() in nse_indices and exchange.upper() == "NSE":
            exchange = "NSE_INDEX"
        elif symbol.upper() in bse_indices and exchange.upper() == "BSE":
            exchange = "BSE_INDEX"
        
        data = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper()
        }
        
        response = run_async(http_client._make_request("symbol", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting symbol info: {str(e)}"

@mcp.tool()
def get_index_symbols(exchange: str = "NSE") -> str:
    """
    Get common index symbols for NSE or BSE.
    
    Args:
        exchange: NSE or BSE
    
    Returns:
        List of common index symbols for the specified exchange
    """
    indices = {
        "NSE": {
            "exchange_code": "NSE_INDEX",
            "symbols": ["NIFTY", "NIFTYNXT50", "FINNIFTY", "BANKNIFTY", "MIDCPNIFTY", "INDIAVIX"]
        },
        "BSE": {
            "exchange_code": "BSE_INDEX", 
            "symbols": ["SENSEX", "BANKEX", "SENSEX50"]
        }
    }
    
    exchange_upper = exchange.upper()
    if exchange_upper in indices:
        return json.dumps({
            "exchange": exchange_upper,
            "exchange_code": indices[exchange_upper]["exchange_code"],
            "indices": indices[exchange_upper]["symbols"]
        }, indent=2)
    else:
        return json.dumps({
            "error": f"Unknown exchange: {exchange}. Use NSE or BSE."
        }, indent=2)

@mcp.tool()
def get_expiry_dates(symbol: str, exchange: str = "NFO", instrument_type: str = "options") -> str:
    """
    Get expiry dates for derivatives.
    
    Args:
        symbol: Underlying symbol
        exchange: Exchange name (typically NFO for F&O)
        instrument_type: 'options' or 'futures'
    """
    try:
        data = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "instrumenttype": instrument_type.lower()
        }
        
        response = run_async(http_client._make_request("expiry", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting expiry dates: {str(e)}"

@mcp.tool()
def get_available_intervals() -> str:
    """Get all available time intervals for historical data."""
    try:
        data = {}  # Only API key is needed
        
        response = run_async(http_client._make_request("intervals", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting intervals: {str(e)}"

# UTILITY TOOLS

@mcp.tool()
def get_openalgo_version() -> str:
    """Get the OpenAlgo API version information."""
    return json.dumps({
        "message": "Using direct HTTP client instead of openalgo library",
        "client": "httpx",
        "version": "Direct API calls"
    }, indent=2)

@mcp.tool()
def validate_order_constants() -> str:
    """Display all valid order constants for reference."""
    constants = {
        "exchanges": {
            "NSE": "NSE Equity",
            "NFO": "NSE Futures & Options", 
            "CDS": "NSE Currency",
            "BSE": "BSE Equity",
            "BFO": "BSE Futures & Options",
            "BCD": "BSE Currency", 
            "MCX": "MCX Commodity",
            "NCDEX": "NCDEX Commodity"
        },
        "product_types": {
            "CNC": "Cash & Carry for equity",
            "NRML": "Normal for futures and options", 
            "MIS": "Intraday Square off"
        },
        "price_types": {
            "MARKET": "Market Order",
            "LIMIT": "Limit Order",
            "SL": "Stop Loss Limit Order",
            "SL-M": "Stop Loss Market Order"
        },
        "actions": {
            "BUY": "Buy",
            "SELL": "Sell"
        },
        "intervals": ["1m", "3m", "5m", "10m", "15m", "30m", "1h", "D"]
    }
    return json.dumps(constants, indent=2)

# ANALYZER TOOLS

@mcp.tool()
def analyzer_status() -> dict:
    """
    Get the current analyzer status including mode and total logs.
    
    Returns:
        Dictionary containing analyzer status information:
        - analyze_mode: Boolean indicating if analyzer is active
        - mode: Current mode ('analyze' or 'live')
        - total_logs: Number of logs in analyzer
    
    Example Response:
        {
            'data': {
                'analyze_mode': True,
                'mode': 'analyze',
                'total_logs': 2
            },
            'status': 'success'
        }
    """
    try:
        data = {}  # Only API key is needed
        response = run_async(http_client._make_request("analyzer", data))
        return response
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def analyzer_toggle(mode: bool) -> dict:
    """
    Toggle the analyzer mode between analyze (simulated) and live trading.
    
    Args:
        mode: True for analyze mode (simulated), False for live mode
    
    Returns:
        Dictionary with updated analyzer status:
        - analyze_mode: Boolean indicating current state
        - message: Status message
        - mode: Current mode string
        - total_logs: Number of logs in analyzer
    
    Example:
        analyzer_toggle(True) - Switch to analyze mode (simulated responses)
        analyzer_toggle(False) - Switch to live trading mode
    """
    try:
        data = {
            "mode": mode
        }
        response = run_async(http_client._make_request("analyzer/toggle", data))
        return response
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    # If "--test-holdings" is passed as an argument, test get_holdings directly
    if "--test-holdings" in sys.argv:
        print("Testing get_holdings() directly...")
        print("get_holdings type:", type(get_holdings))
        print("get_holdings dir:", dir(get_holdings))
        # Try to call the underlying function if possible
        def _call_tool_func(obj):
            if asyncio.iscoroutinefunction(obj):
                return asyncio.run(obj())
            return obj()

        if hasattr(get_holdings, "fn"):
            result = _call_tool_func(get_holdings.fn)
        elif hasattr(get_holdings, "__wrapped__"):
            result = _call_tool_func(get_holdings.__wrapped__)
        elif hasattr(get_holdings, "func"):
            result = _call_tool_func(get_holdings.func)
        else:
            result = "Could not call get_holdings: unknown decorator structure"
        print("get_holdings() result:")
        print(result)
        return

    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
