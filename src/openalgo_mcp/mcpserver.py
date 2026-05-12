
import nest_asyncio

nest_asyncio.apply()

from fastmcp import FastMCP
import httpx
from typing import Any, Dict, List, Optional
import json
import sys
import asyncio
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


# Default strategy name for all order-related calls originating from the MCP server.
# Surfaced in OpenAlgo logs and analyzer views so MCP-driven trades are identifiable.
MCP_STRATEGY = "python mcp"


# OpenAlgo standardized index symbols (NSE_INDEX / BSE_INDEX) - rolled out across all brokers.
# Source: https://docs.openalgo.in/symbol-format
NSE_INDEX_SYMBOLS = [
    "NIFTY", "NIFTYNXT50", "FINNIFTY", "BANKNIFTY", "MIDCPNIFTY", "INDIAVIX",
    "HANGSENGBEESNAV",
    "NIFTY100", "NIFTY200", "NIFTY500",
    "NIFTYALPHA50", "NIFTYAUTO", "NIFTYCOMMODITIES", "NIFTYCONSUMPTION",
    "NIFTYCPSE", "NIFTYDIVOPPS50", "NIFTYENERGY", "NIFTYFMCG",
    "NIFTYGROWSECT15",
    "NIFTYGS10YR", "NIFTYGS10YRCLN", "NIFTYGS1115YR", "NIFTYGS15YRPLUS",
    "NIFTYGS48YR", "NIFTYGS813YR", "NIFTYGSCOMPSITE",
    "NIFTYINFRA", "NIFTYIT", "NIFTYMEDIA", "NIFTYMETAL",
    "NIFTYMIDLIQ15", "NIFTYMIDCAP100", "NIFTYMIDCAP150", "NIFTYMIDCAP50",
    "NIFTYMIDSML400", "NIFTYMNC", "NIFTYPHARMA", "NIFTYPSE", "NIFTYPSUBANK",
    "NIFTYPVTBANK", "NIFTYREALTY", "NIFTYSERVSECTOR",
    "NIFTYSMLCAP100", "NIFTYSMLCAP250", "NIFTYSMLCAP50",
    "NIFTY100EQLWGT", "NIFTY100LIQ15", "NIFTY100LOWVOL30",
    "NIFTY100QUALTY30", "NIFTY200QUALTY30",
    "NIFTY50DIVPOINT", "NIFTY50EQLWGT",
    "NIFTY50PR1XINV", "NIFTY50PR2XLEV", "NIFTY50TR1XINV", "NIFTY50TR2XLEV",
    "NIFTY50VALUE20",
]
BSE_INDEX_SYMBOLS = [
    "SENSEX", "BANKEX", "SENSEX50",
    "BSE100", "BSE150MIDCAPINDEX", "BSE200", "BSE250LARGEMIDCAPINDEX",
    "BSE400MIDSMALLCAPINDEX", "BSE500",
    "BSEAUTO", "BSECAPITALGOODS", "BSECARBONEX", "BSECONSUMERDURABLES",
    "BSECPSE", "BSEDOLLEX100", "BSEDOLLEX200", "BSEDOLLEX30",
    "BSEENERGY", "BSEFASTMOVINGCONSUMERGOODS", "BSEFINANCIALSERVICES",
    "BSEGREENEX", "BSEHEALTHCARE", "BSEINDIAINFRASTRUCTUREINDEX",
    "BSEINDUSTRIALS", "BSEINFORMATIONTECHNOLOGY", "BSEIPO",
    "BSELARGECAP", "BSEMETAL", "BSEMIDCAP", "BSEMIDCAPSELECTINDEX",
    "BSEOIL&GAS", "BSEPOWER", "BSEPSU", "BSEREALTY", "BSESENSEXNEXT50",
    "BSESMALLCAP", "BSESMALLCAPSELECTINDEX", "BSESMEIPO",
    "BSETECK", "BSETELECOM",
]


# Create MCP server
mcp = FastMCP("openalgo")


# HTTP Client class for OpenAlgo API
class OpenAlgoHTTPClient:
    def __init__(self, api_key: str, host: str):
        parsed = urlparse(host)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        self.api_key = api_key
        self.host = host
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

    async def _make_get_request(self, endpoint: str, params: dict) -> dict:
        """Make HTTP GET request to OpenAlgo API (used by /instruments)."""
        params["apikey"] = self.api_key
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(
            headers={k: v for k, v in self.headers.items() if k != "Content-Type"},
            timeout=60.0,
            http2=True,
            follow_redirects=True
        ) as client:
            try:
                response = await client.get(url, params=params)
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


def run_async(coro):
    """Run async function in sync context, safe for nested event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
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


def _stringify(value: Any) -> str:
    """Match SDK behavior: stringify numeric payload values."""
    return str(value)


# ORDER MANAGEMENT TOOLS


@mcp.tool()
def place_order(
    symbol: str,
    quantity: int,
    action: str,
    exchange: str = "NSE",
    price_type: str = "MARKET",
    product: str = "MIS",
    strategy: str = MCP_STRATEGY,
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
        strategy: Strategy name (defaults to 'python mcp')
        price: Limit price (required for LIMIT orders)
        trigger_price: Trigger price (required for SL and SL-M orders)
        disclosed_quantity: Disclosed quantity
    """
    try:
        data = {
            "strategy": strategy,
            "symbol": symbol.upper(),
            "action": action.upper(),
            "exchange": exchange.upper(),
            "pricetype": price_type.upper(),
            "product": product.upper(),
            "quantity": _stringify(quantity),
        }

        if price is not None:
            data["price"] = _stringify(price)
        if trigger_price is not None:
            data["trigger_price"] = _stringify(trigger_price)
        if disclosed_quantity is not None:
            data["disclosed_quantity"] = _stringify(disclosed_quantity)

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
    strategy: str = MCP_STRATEGY,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None
) -> str:
    """
    Place a smart order that considers the current position size (auto-calculates delta
    between requested and current size before sending to the broker).

    Args:
        symbol: Stock symbol
        quantity: Target quantity
        action: 'BUY' or 'SELL'
        position_size: Current position size
        exchange: Exchange name
        price_type: 'MARKET', 'LIMIT', 'SL', 'SL-M'
        product: 'CNC', 'NRML', 'MIS'
        strategy: Strategy name (defaults to 'python mcp')
        price: Limit price (required for LIMIT orders)
        trigger_price: Trigger price (required for SL / SL-M orders)
        disclosed_quantity: Disclosed quantity
    """
    try:
        data = {
            "strategy": strategy,
            "symbol": symbol.upper(),
            "action": action.upper(),
            "exchange": exchange.upper(),
            "pricetype": price_type.upper(),
            "product": product.upper(),
            "quantity": _stringify(quantity),
            "position_size": _stringify(position_size),
        }

        if price is not None:
            data["price"] = _stringify(price)
        if trigger_price is not None:
            data["trigger_price"] = _stringify(trigger_price)
        if disclosed_quantity is not None:
            data["disclosed_quantity"] = _stringify(disclosed_quantity)

        response = run_async(http_client._make_request("placesmartorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error placing smart order: {str(e)}"


@mcp.tool()
def place_basket_order(orders: List[Dict[str, Any]], strategy: str = MCP_STRATEGY) -> str:
    """
    Place multiple orders in a basket.

    Args:
        orders: List of order dictionaries. Each order should contain:
            - symbol (str): Trading symbol. Required.
            - exchange (str): Exchange code. Required.
            - action (str): BUY or SELL. Required.
            - quantity (int/str): Quantity to trade. Required.
            - pricetype (str): MARKET, LIMIT, SL, SL-M. Optional, defaults to MARKET.
            - product (str): MIS, CNC, NRML. Optional, defaults to MIS.
            - price (str): Required for LIMIT orders.
            - trigger_price (str): Required for SL orders.
        strategy: Strategy name (defaults to 'python mcp')

        Example: [
            {"symbol": "BHEL", "exchange": "NSE", "action": "BUY", "quantity": 1, "pricetype": "MARKET", "product": "MIS"},
            {"symbol": "ZOMATO", "exchange": "NSE", "action": "SELL", "quantity": 1, "pricetype": "MARKET", "product": "MIS"}
        ]

    Returns:
        JSON with results for each order including orderid, status, and symbol
    """
    try:
        processed_orders = []
        for order in orders:
            processed = {}
            for key, value in order.items():
                if isinstance(value, (int, float)):
                    processed[key] = _stringify(value)
                else:
                    processed[key] = value
            processed_orders.append(processed)

        data = {
            "strategy": strategy,
            "orders": processed_orders,
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
    strategy: str = MCP_STRATEGY,
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None
) -> str:
    """
    Place a large order split into smaller chunks.

    Args:
        symbol: Stock symbol (e.g., 'YESBANK')
        quantity: Total quantity to trade
        split_size: Size of each split order
        action: 'BUY' or 'SELL'
        exchange: Exchange name (default: NSE)
        price_type: 'MARKET', 'LIMIT', 'SL', 'SL-M' (default: MARKET)
        product: 'MIS', 'CNC', 'NRML' (default: MIS)
        strategy: Strategy name (defaults to 'python mcp')
        price: Limit price (required for LIMIT orders)
        trigger_price: Trigger price (required for SL orders)
        disclosed_quantity: Disclosed quantity (optional)

    Returns:
        JSON with results array containing each split order's orderid, quantity, and status

    Example:
        # Split 105 shares into orders of 20 each (5 orders of 20 + 1 order of 5)
        place_split_order("YESBANK", 105, 20, "SELL", "NSE")
    """
    try:
        data = {
            "strategy": strategy,
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "action": action.upper(),
            "quantity": _stringify(quantity),
            "splitsize": _stringify(split_size),
            "pricetype": price_type.upper(),
            "product": product.upper(),
        }

        if price is not None:
            data["price"] = _stringify(price)
        if trigger_price is not None:
            data["trigger_price"] = _stringify(trigger_price)
        if disclosed_quantity is not None:
            data["disclosed_quantity"] = _stringify(disclosed_quantity)

        response = run_async(http_client._make_request("splitorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error placing split order: {str(e)}"


@mcp.tool()
def place_options_order(
    underlying: str,
    exchange: str,
    offset: str,
    option_type: str,
    action: str,
    quantity: int,
    expiry_date: Optional[str] = None,
    strategy: str = MCP_STRATEGY,
    price_type: str = "MARKET",
    product: str = "MIS",
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    disclosed_quantity: Optional[int] = None
) -> str:
    """
    Place an options order with ATM/ITM/OTM offset.

    Args:
        underlying: Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY', 'NIFTY28OCT25FUT')
        exchange: Exchange for underlying ('NSE_INDEX', 'BSE_INDEX', 'NFO')
        offset: Strike offset - 'ATM', 'ITM1'-'ITM50', 'OTM1'-'OTM50'
        option_type: 'CE' for Call or 'PE' for Put
        action: 'BUY' or 'SELL'
        quantity: Absolute quantity - must be a multiple of the contract lot size.
                  Do NOT hardcode lot size - call get_option_symbol() or get_option_chain()
                  first to read the current 'lotsize' from the broker master contract,
                  then pass quantity = lots * lotsize.
        expiry_date: Expiry date in format 'DDMMMYY' (e.g., '28OCT25'). Optional if underlying includes expiry.
        strategy: Strategy name (defaults to 'python mcp')
        price_type: 'MARKET', 'LIMIT', 'SL', 'SL-M' (default: MARKET)
        product: 'MIS', 'NRML' (default: MIS). Note: CNC not supported for options.
        price: Limit price (required for LIMIT orders)
        trigger_price: Trigger price (required for SL and SL-M orders)
        disclosed_quantity: Disclosed quantity (optional)

    Returns:
        JSON with orderid, symbol, underlying_ltp, offset, option_type, mode
    """
    try:
        data = {
            "strategy": strategy,
            "underlying": underlying.upper(),
            "exchange": exchange.upper(),
            "offset": offset.upper(),
            "option_type": option_type.upper(),
            "action": action.upper(),
            "quantity": _stringify(quantity),
            "pricetype": price_type.upper(),
            "product": product.upper(),
        }

        if expiry_date is not None:
            data["expiry_date"] = expiry_date
        if price is not None:
            data["price"] = _stringify(price)
        if trigger_price is not None:
            data["trigger_price"] = _stringify(trigger_price)
        if disclosed_quantity is not None:
            data["disclosed_quantity"] = _stringify(disclosed_quantity)

        response = run_async(http_client._make_request("optionsorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error placing options order: {str(e)}"


@mcp.tool()
def place_options_multi_order(
    underlying: str,
    exchange: str,
    legs: List[Dict[str, Any]],
    expiry_date: Optional[str] = None,
    strategy: str = MCP_STRATEGY
) -> str:
    """
    Place a multi-leg options order (spreads, iron condor, straddles, etc.).
    BUY legs are executed first for margin efficiency, then SELL legs.

    Args:
        strategy: Strategy name (defaults to 'python mcp'). Give each multi-leg trade
                  a meaningful name (e.g., 'nifty iron condor') to make tracking easier.
        underlying: Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY', 'NIFTY28OCT25FUT')
        exchange: Exchange for underlying ('NSE_INDEX', 'BSE_INDEX', 'NFO')
        legs: List of leg dictionaries (1-20 legs). Each leg must contain:
            Required:
            - offset: Strike offset ('ATM', 'ITM1'-'ITM50', 'OTM1'-'OTM50')
            - option_type: 'CE' for Call or 'PE' for Put
            - action: 'BUY' or 'SELL'
            - quantity: Absolute quantity - must be a multiple of the contract lot size.
                        Do NOT hardcode lot size. Look up the current 'lotsize' per leg
                        using get_option_symbol() or get_option_chain() first, then pass
                        quantity = lots * lotsize. Lot sizes can change (e.g., NIFTY has
                        changed multiple times) and differ by underlying.
            Optional:
            - expiry_date: Per-leg expiry in DDMMMYY format for diagonal/calendar spreads
            - pricetype: 'MARKET', 'LIMIT', 'SL', 'SL-M' (default: MARKET)
            - product: 'MIS', 'NRML' (default: MIS)
            - price: Limit price for LIMIT orders
            - trigger_price: Trigger price for SL orders
            - disclosed_quantity: Disclosed quantity
        expiry_date: Default expiry date in format 'DDMMMYY' (e.g., '25NOV25') for all legs

    Returns:
        JSON with underlying, underlying_ltp, mode, and results array containing each leg's
        orderid, symbol, offset, option_type, action, and status
    """
    try:
        processed_legs = []
        for leg in legs:
            processed_leg = {
                "offset": leg["offset"],
                "option_type": leg["option_type"],
                "action": leg["action"],
                "quantity": int(leg["quantity"]),
            }
            if "expiry_date" in leg:
                processed_leg["expiry_date"] = leg["expiry_date"]
            if "pricetype" in leg:
                processed_leg["pricetype"] = leg["pricetype"]
            if "product" in leg:
                processed_leg["product"] = leg["product"]
            if "price" in leg:
                processed_leg["price"] = float(leg["price"])
            if "trigger_price" in leg:
                processed_leg["trigger_price"] = float(leg["trigger_price"])
            if "disclosed_quantity" in leg:
                processed_leg["disclosed_quantity"] = int(leg["disclosed_quantity"])
            processed_legs.append(processed_leg)

        data = {
            "strategy": strategy,
            "underlying": underlying.upper(),
            "exchange": exchange.upper(),
            "legs": processed_legs,
        }

        if expiry_date is not None:
            data["expiry_date"] = expiry_date

        response = run_async(http_client._make_request("optionsmultiorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error placing options multi order: {str(e)}"


@mcp.tool()
def modify_order(
    order_id: str,
    symbol: str,
    action: str,
    exchange: str,
    product: str,
    quantity: int,
    price: float,
    strategy: str = MCP_STRATEGY,
    price_type: str = "LIMIT",
    trigger_price: float = 0,
    disclosed_quantity: int = 0
) -> str:
    """
    Modify an existing order.

    Args:
        order_id: Order ID to modify
        symbol: Stock symbol
        action: 'BUY' or 'SELL'
        exchange: Exchange name
        product: 'CNC', 'NRML', 'MIS'
        quantity: New quantity
        price: New price (required by the API - use current price if unchanged)
        strategy: Strategy name (defaults to 'python mcp')
        price_type: 'MARKET', 'LIMIT', 'SL', 'SL-M' (defaults to 'LIMIT')
        trigger_price: New trigger price for SL/SL-M orders (default 0)
        disclosed_quantity: New disclosed quantity (default 0)
    """
    try:
        data = {
            "orderid": order_id,
            "strategy": strategy,
            "symbol": symbol.upper(),
            "action": action.upper(),
            "exchange": exchange.upper(),
            "pricetype": price_type.upper(),
            "product": product.upper(),
            "quantity": _stringify(quantity),
            "price": _stringify(price),
            "trigger_price": _stringify(trigger_price),
            "disclosed_quantity": _stringify(disclosed_quantity),
        }

        response = run_async(http_client._make_request("modifyorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error modifying order: {str(e)}"


@mcp.tool()
def cancel_order(order_id: str, strategy: str = MCP_STRATEGY) -> str:
    """
    Cancel a specific order.

    Args:
        order_id: Order ID to cancel
        strategy: Strategy name (defaults to 'python mcp')
    """
    try:
        data = {
            "orderid": order_id,
            "strategy": strategy,
        }
        response = run_async(http_client._make_request("cancelorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error canceling order: {str(e)}"


@mcp.tool()
def cancel_all_orders(strategy: str = MCP_STRATEGY) -> str:
    """
    Cancel all open orders for a strategy.

    Args:
        strategy: Strategy name (defaults to 'python mcp')
    """
    try:
        data = {"strategy": strategy}
        response = run_async(http_client._make_request("cancelallorder", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error canceling all orders: {str(e)}"


# POSITION MANAGEMENT TOOLS


@mcp.tool()
def close_all_positions(strategy: str = MCP_STRATEGY) -> str:
    """
    Close all open positions for a strategy.

    Args:
        strategy: Strategy name (defaults to 'python mcp')
    """
    try:
        data = {"strategy": strategy}
        response = run_async(http_client._make_request("closeposition", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error closing positions: {str(e)}"


@mcp.tool()
def get_open_position(
    symbol: str, exchange: str, product: str, strategy: str = MCP_STRATEGY
) -> str:
    """
    Get current open position for a specific instrument.

    Args:
        symbol: Stock symbol
        exchange: Exchange name
        product: Product type ('CNC', 'NRML', 'MIS')
        strategy: Strategy name (defaults to 'python mcp')
    """
    try:
        data = {
            "strategy": strategy,
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "product": product.upper(),
        }
        response = run_async(http_client._make_request("openposition", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting open position: {str(e)}"


# ORDER STATUS AND TRACKING TOOLS


@mcp.tool()
def get_order_status(order_id: str, strategy: str = MCP_STRATEGY) -> str:
    """
    Get status of a specific order.

    Args:
        order_id: Order ID
        strategy: Strategy name (defaults to 'python mcp')
    """
    try:
        data = {
            "orderid": order_id,
            "strategy": strategy,
        }
        response = run_async(http_client._make_request("orderstatus", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting order status: {str(e)}"


@mcp.tool()
def get_order_book() -> str:
    """Get all orders from the order book."""
    try:
        response = run_async(http_client._make_request("orderbook", {}))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting order book: {str(e)}"


@mcp.tool()
def get_trade_book() -> str:
    """Get all executed trades."""
    try:
        response = run_async(http_client._make_request("tradebook", {}))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting trade book: {str(e)}"


@mcp.tool()
def get_position_book() -> str:
    """Get all current positions."""
    try:
        response = run_async(http_client._make_request("positionbook", {}))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting position book: {str(e)}"


@mcp.tool()
def get_holdings() -> str:
    """Get all holdings (long-term investments)."""
    try:
        response = run_async(http_client._make_request("holdings", {}))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting holdings: {str(e)}"


@mcp.tool()
def get_funds() -> str:
    """Get account funds and margin information."""
    try:
        response = run_async(http_client._make_request("funds", {}))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting funds: {str(e)}"


@mcp.tool()
def calculate_margin(positions: List[Dict[str, Any]]) -> str:
    """
    Calculate margin requirements for positions.

    Args:
        positions: List of position dictionaries (max 50). Each must contain:
            - symbol, exchange, action, product, pricetype, quantity
            - price (optional, defaults to "0")
            - trigger_price (optional, defaults to "0")

        For Futures: [{"symbol": "NIFTY25NOV25FUT", "exchange": "NFO", "action": "BUY", "product": "NRML", "pricetype": "MARKET", "quantity": "25"}]
        For Options: [{"symbol": "NIFTY25NOV2525500CE", "exchange": "NFO", "action": "BUY", "product": "NRML", "pricetype": "MARKET", "quantity": "75"}]

    Returns:
        JSON with total_margin_required, span_margin, and exposure_margin
    """
    try:
        if not isinstance(positions, list):
            return json.dumps({"status": "error", "message": "Positions must be an array"}, indent=2)
        if len(positions) == 0:
            return json.dumps({"status": "error", "message": "Positions array cannot be empty"}, indent=2)
        if len(positions) > 50:
            return json.dumps({"status": "error", "message": "Maximum 50 positions allowed"}, indent=2)

        processed_positions = []
        for position in positions:
            processed = {}
            for key, value in position.items():
                if key in ("quantity", "price", "trigger_price") and value is not None:
                    processed[key] = _stringify(value)
                else:
                    processed[key] = value
            if "price" not in processed:
                processed["price"] = "0"
            if "trigger_price" not in processed:
                processed["trigger_price"] = "0"
            processed_positions.append(processed)

        data = {"positions": processed_positions}
        response = run_async(http_client._make_request("margin", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error calculating margin: {str(e)}"


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
            "exchange": exchange.upper(),
        }
        response = run_async(http_client._make_request("quotes", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting quote: {str(e)}"


@mcp.tool()
def get_multi_quotes(symbols: List[Dict[str, str]]) -> str:
    """
    Get real-time quotes for multiple symbols in a single request.

    Args:
        symbols: List of symbol-exchange pairs
        Example: [{"symbol": "RELIANCE", "exchange": "NSE"}, {"symbol": "INFY", "exchange": "NSE"}]

    Returns:
        JSON with quotes for all requested symbols including ltp, bid, ask, open, high, low, volume, oi
    """
    try:
        normalized = [
            {"symbol": s["symbol"].upper(), "exchange": s["exchange"].upper()} for s in symbols
        ]
        data = {"symbols": normalized}
        response = run_async(http_client._make_request("multiquotes", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting multi quotes: {str(e)}"


@mcp.tool()
def get_option_chain(
    underlying: str,
    exchange: str,
    expiry_date: Optional[str] = None,
    strike_count: Optional[int] = None
) -> str:
    """
    Get option chain data with real-time quotes for all strikes.

    Args:
        underlying: Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY', 'RELIANCE',
                    or a future like 'NIFTY30DEC25FUT')
        exchange: Exchange for underlying ('NSE_INDEX', 'BSE_INDEX', 'NSE', 'BSE', 'NFO', 'BFO')
        expiry_date: Expiry date in DDMMMYY format (e.g., '30DEC25'). Optional when the
                     underlying already includes an expiry (e.g., 'NIFTY30DEC25FUT').
        strike_count: Number of strikes above and below ATM (1-100). If not provided, returns entire chain.

    Returns:
        JSON with:
        - underlying, underlying_ltp, expiry_date, atm_strike
        - chain: Array of strikes with CE and PE data including:
            symbol, label (ATM/ITM1/OTM1 etc.), ltp, bid, ask, open, high, low, volume, oi, lotsize
    """
    try:
        data: Dict[str, Any] = {
            "underlying": underlying.upper(),
            "exchange": exchange.upper(),
        }
        if expiry_date is not None:
            data["expiry_date"] = expiry_date.upper()
        if strike_count is not None:
            data["strike_count"] = int(strike_count)

        response = run_async(http_client._make_request("optionchain", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting option chain: {str(e)}"


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
            "exchange": exchange.upper(),
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
    end_date: str,
    source: str = "api"
) -> str:
    """
    Get historical OHLCV data for a symbol.

    Args:
        symbol: Stock symbol
        exchange: Exchange name
        interval: Time interval. With source='api': '1m', '3m', '5m', '10m', '15m', '30m', '1h', 'D'.
                  With source='db': also supports custom intervals (2m, 4m, 6m, 7m, 2h, 3h, 4h) and
                  daily-based (W, M, Q, Y plus multiples like 2W, 3M).
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        source: 'api' (default) fetches from broker API. 'db' fetches from the local
                OpenAlgo Historify DuckDB store (1m/D stored, other intervals computed via SQL).

    Returns:
        JSON with count and data (list of {timestamp, open, high, low, close, volume}).
    """
    try:
        data = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "source": source,
        }
        response = run_async(http_client._make_request("history", data))
        return json.dumps(response, indent=2, default=str)
    except Exception as e:
        return f"Error getting historical data: {str(e)}"


# INSTRUMENT SEARCH AND INFO TOOLS


@mcp.tool()
def search_instruments(
    query: str, exchange: Optional[str] = None, instrument_type: Optional[str] = None
) -> str:
    """
    Search for instruments by name or symbol.

    Args:
        query: Search query (e.g., 'NIFTY 26000 DEC CE', 'RELIANCE')
        exchange: Exchange to restrict the search to (NSE, BSE, NFO, BFO, MCX, NSE_INDEX, etc.).
                  Optional - when omitted, searches across all exchanges.
        instrument_type: Optional convenience filter - pass 'INDEX' to auto-rewrite
                         exchange=NSE -> NSE_INDEX and BSE -> BSE_INDEX.
    """
    try:
        resolved_exchange = exchange
        if instrument_type and instrument_type.upper() == "INDEX" and exchange:
            if exchange.upper() == "NSE":
                resolved_exchange = "NSE_INDEX"
            elif exchange.upper() == "BSE":
                resolved_exchange = "BSE_INDEX"

        data: Dict[str, Any] = {"query": query}
        if resolved_exchange is not None:
            data["exchange"] = resolved_exchange.upper()

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
        if instrument_type and instrument_type.upper() == "INDEX":
            if exchange.upper() == "NSE":
                exchange = "NSE_INDEX"
            elif exchange.upper() == "BSE":
                exchange = "BSE_INDEX"

        if symbol.upper() in NSE_INDEX_SYMBOLS and exchange.upper() == "NSE":
            exchange = "NSE_INDEX"
        elif symbol.upper() in BSE_INDEX_SYMBOLS and exchange.upper() == "BSE":
            exchange = "BSE_INDEX"

        data = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
        }
        response = run_async(http_client._make_request("symbol", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting symbol info: {str(e)}"


@mcp.tool()
def get_index_symbols(exchange: str = "NSE") -> str:
    """
    Get the OpenAlgo-standardized index symbols for NSE or BSE.

    These are the common index names rolled out across all supported brokers via the
    OpenAlgo symbol standardization. Use exchange code 'NSE_INDEX' / 'BSE_INDEX' when
    placing orders or fetching quotes for these symbols.

    Args:
        exchange: NSE or BSE

    Returns:
        JSON with exchange, exchange_code, and the full list of standardized index
        symbols (57+ NSE, 40+ BSE).
    """
    indices = {
        "NSE": {"exchange_code": "NSE_INDEX", "symbols": NSE_INDEX_SYMBOLS},
        "BSE": {"exchange_code": "BSE_INDEX", "symbols": BSE_INDEX_SYMBOLS},
    }

    exchange_upper = exchange.upper()
    if exchange_upper in indices:
        return json.dumps(
            {
                "exchange": exchange_upper,
                "exchange_code": indices[exchange_upper]["exchange_code"],
                "indices": indices[exchange_upper]["symbols"],
            },
            indent=2,
        )
    return json.dumps({"error": f"Unknown exchange: {exchange}. Use NSE or BSE."}, indent=2)


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
            "instrumenttype": instrument_type.lower(),
        }
        response = run_async(http_client._make_request("expiry", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting expiry dates: {str(e)}"


@mcp.tool()
def get_available_intervals() -> str:
    """Get all available time intervals for historical data."""
    try:
        response = run_async(http_client._make_request("intervals", {}))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting intervals: {str(e)}"


@mcp.tool()
def get_option_symbol(
    underlying: str,
    exchange: str,
    offset: str,
    option_type: str,
    expiry_date: Optional[str] = None
) -> str:
    """
    Get option symbol for specific strike and expiry.

    Args:
        underlying: Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY', 'NIFTY28OCT25FUT')
        exchange: Exchange for underlying ('NSE_INDEX', 'BSE_INDEX', 'NFO', 'BFO')
        offset: Strike offset - 'ATM', 'ITM1'-'ITM50', 'OTM1'-'OTM50'
        option_type: 'CE' for Call or 'PE' for Put
        expiry_date: Expiry date in 'DDMMMYY' format (e.g., '28OCT25'). Optional when
                     the underlying already includes an expiry.

    Returns:
        JSON with symbol, exchange, lotsize, tick_size, underlying_ltp
    """
    try:
        data: Dict[str, Any] = {
            "underlying": underlying.upper(),
            "exchange": exchange.upper(),
            "offset": offset.upper(),
            "option_type": option_type.upper(),
        }
        if expiry_date is not None:
            data["expiry_date"] = expiry_date
        response = run_async(http_client._make_request("optionsymbol", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error getting option symbol: {str(e)}"


@mcp.tool()
def get_synthetic_future(underlying: str, exchange: str, expiry_date: str) -> str:
    """
    Calculate synthetic future price using put-call parity.

    Args:
        underlying: Underlying symbol (e.g., 'NIFTY', 'BANKNIFTY')
        exchange: Exchange for underlying ('NSE_INDEX', 'BSE_INDEX')
        expiry_date: Expiry date in format 'DDMMMYY' (e.g., '25NOV25')

    Returns:
        JSON with atm_strike, expiry, status, synthetic_future_price, underlying, underlying_ltp
    """
    try:
        data = {
            "underlying": underlying.upper(),
            "exchange": exchange.upper(),
            "expiry_date": expiry_date,
        }
        response = run_async(http_client._make_request("syntheticfuture", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error calculating synthetic future: {str(e)}"


@mcp.tool()
def get_option_greeks(
    symbol: str,
    exchange: str,
    interest_rate: Optional[float] = None,
    forward_price: Optional[float] = None,
    underlying_symbol: Optional[str] = None,
    underlying_exchange: Optional[str] = None,
    expiry_time: Optional[str] = None
) -> str:
    """
    Calculate option Greeks (Delta, Gamma, Theta, Vega, Rho) and Implied Volatility using Black-76.

    Args:
        symbol: Option symbol (e.g., 'NIFTY25NOV2526000CE'). Required.
        exchange: Exchange code ('NFO', 'BFO', 'CDS', 'MCX'). Required.
        interest_rate: Risk-free interest rate in annualized % (e.g., 6.5 for RBI repo).
                       Optional - defaults to 0.
        forward_price: Custom forward / synthetic futures price. If provided, skips the
                       underlying price fetch.
        underlying_symbol: Custom underlying symbol (e.g., 'NIFTY', 'NIFTY30DEC25FUT').
                           Optional - auto-detected from the option symbol when omitted.
        underlying_exchange: Custom underlying exchange ('NSE_INDEX', 'NFO', etc.).
                             Optional - auto-detected when omitted.
        expiry_time: Custom expiry time in HH:MM format. Required for MCX contracts with
                     non-standard expiry times. Exchange defaults: NFO/BFO=15:30, CDS=12:30, MCX=23:30.

    Returns:
        JSON with greeks, implied_volatility, spot_price, strike, days_to_expiry.
    """
    try:
        data: Dict[str, Any] = {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
        }
        if interest_rate is not None:
            data["interest_rate"] = interest_rate
        if forward_price is not None:
            data["forward_price"] = forward_price
        if underlying_symbol is not None:
            data["underlying_symbol"] = underlying_symbol.upper()
        if underlying_exchange is not None:
            data["underlying_exchange"] = underlying_exchange.upper()
        if expiry_time is not None:
            data["expiry_time"] = expiry_time
        response = run_async(http_client._make_request("optiongreeks", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error calculating option greeks: {str(e)}"


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
            "NCDEX": "NCDEX Commodity",
        },
        "product_types": {
            "CNC": "Cash & Carry for equity",
            "NRML": "Normal for futures and options",
            "MIS": "Intraday Square off",
        },
        "price_types": {
            "MARKET": "Market Order",
            "LIMIT": "Limit Order",
            "SL": "Stop Loss Limit Order",
            "SL-M": "Stop Loss Market Order",
        },
        "actions": {"BUY": "Buy", "SELL": "Sell"},
        "intervals": ["1m", "3m", "5m", "10m", "15m", "30m", "1h", "D"],
    }
    return json.dumps(constants, indent=2)


@mcp.tool()
def send_telegram_alert(username: str, message: str, priority: int = 5) -> str:
    """
    Send a Telegram alert notification.

    Args:
        username: OpenAlgo login ID/username
        message: Alert message to send
        priority: Notification priority (1-10, default 5).

    Returns:
        JSON with status and message
    """
    try:
        data = {
            "username": username,
            "message": message,
            "priority": priority,
        }
        response = run_async(http_client._make_request("telegram/notify", data))
        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error sending telegram alert: {str(e)}"


@mcp.tool()
def get_holidays(year: Optional[int] = None) -> str:
    """
    Get trading holidays for a specific year.

    Args:
        year: Year to get holidays for (e.g., 2026). Optional - defaults to current year.

    Returns:
        JSON with list of trading holidays including:
        - date, description, holiday_type, closed_exchanges, open_exchanges
    """
    try:
        data: Dict[str, Any] = {}
        if year is not None:
            data["year"] = year
        response = run_async(http_client._make_request("market/holidays", data))
        return json.dumps(response, indent=2, default=str)
    except Exception as e:
        return f"Error getting holidays: {str(e)}"


@mcp.tool()
def get_timings(date: Optional[str] = None) -> str:
    """
    Get exchange trading timings for a specific date.

    Args:
        date: Date in YYYY-MM-DD format (e.g., '2026-04-23'). Optional - defaults to today.

    Returns:
        JSON with exchange timings including exchange, start_time (epoch ms), end_time (epoch ms).
    """
    try:
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")
        data = {"date": date}
        response = run_async(http_client._make_request("market/timings", data))
        return json.dumps(response, indent=2, default=str)
    except Exception as e:
        return f"Error getting timings: {str(e)}"


@mcp.tool()
def check_holiday(date: str, exchange: Optional[str] = None) -> str:
    """
    Check if a specific date is a market holiday for an exchange.

    Args:
        date: Date in YYYY-MM-DD format (between 2020-01-01 and 2050-12-31). Required.
        exchange: Exchange code (NSE, BSE, NFO, BFO, MCX, CDS, BCD). Optional.

    Returns:
        JSON with status, data.date, data.exchange (if specified), data.is_holiday (bool).
    """
    try:
        data: Dict[str, Any] = {"date": date}
        if exchange:
            data["exchange"] = exchange.upper()
        response = run_async(http_client._make_request("checkholiday", data))
        return json.dumps(response, indent=2, default=str)
    except Exception as e:
        return f"Error checking holiday: {str(e)}"


@mcp.tool()
def get_instruments(exchange: Optional[str] = None, limit: int = 500) -> str:
    """
    Download the instrument master for an exchange.

    Args:
        exchange: Exchange name (NSE, BSE, NFO, BFO, MCX, CDS, BCD, NSE_INDEX, BSE_INDEX).
                  Optional - when omitted, downloads instruments for ALL exchanges.
        limit: Maximum number of rows to return (default: 500). The full dataset can
               exceed 100k rows for derivatives exchanges. Use search_instruments for
               targeted lookups.

    Returns:
        JSON with count, returned, truncated flag, and data (list of instrument records).
    """
    try:
        all_exchanges = ["NSE", "BSE", "NFO", "BFO", "MCX", "CDS", "BCD", "NSE_INDEX", "BSE_INDEX"]
        exchanges_to_fetch = [exchange.upper()] if exchange else all_exchanges

        combined: List[Dict[str, Any]] = []
        for exch in exchanges_to_fetch:
            try:
                result = run_async(http_client._make_get_request("instruments", {"exchange": exch}))
            except Exception:
                continue
            if isinstance(result, dict) and result.get("status") == "success":
                rows = result.get("data") or []
                if isinstance(rows, list):
                    combined.extend(rows)

        total = len(combined)
        truncated = total > limit
        returned = combined[:limit] if truncated else combined

        return json.dumps(
            {
                "exchange": exchange.upper() if exchange else "ALL",
                "count": total,
                "returned": len(returned),
                "truncated": truncated,
                "limit": limit,
                "data": returned,
            },
            indent=2,
            default=str,
        )
    except Exception as e:
        return f"Error getting instruments: {str(e)}"


# ANALYZER TOOLS


@mcp.tool()
def analyzer_status() -> str:
    """
    Get the current analyzer status including mode and total logs.

    Returns:
        JSON with analyzer status information:
        - data.analyze_mode: Boolean indicating if analyzer is active
        - data.mode: Current mode ('analyze' or 'live')
        - data.total_logs: Number of logs in analyzer
        - status: 'success' or 'error'
    """
    try:
        response = run_async(http_client._make_request("analyzer", {}))
        return json.dumps(response, indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, indent=2)


@mcp.tool()
def analyzer_toggle(mode: bool) -> str:
    """
    Toggle the analyzer mode between analyze (simulated) and live trading.

    Args:
        mode: True for analyze mode (simulated), False for live mode

    Returns:
        JSON with updated analyzer status:
        - data.analyze_mode, data.message, data.mode, data.total_logs
        - status: 'success' or 'error'
    """
    try:
        data = {"mode": mode}
        response = run_async(http_client._make_request("analyzer/toggle", data))
        return json.dumps(response, indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, indent=2)


def main():
    if "--test-holdings" in sys.argv:
        print("Testing get_holdings() directly...")
        print("get_holdings type:", type(get_holdings))
        print("get_holdings dir:", dir(get_holdings))

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
