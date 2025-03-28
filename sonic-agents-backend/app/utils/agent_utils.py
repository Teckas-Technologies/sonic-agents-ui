import json
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain.tools import Tool
from langgraph.graph import START, StateGraph, MessagesState
from langgraph.prebuilt import tools_condition, ToolNode
from app.utils.openai_utils import llm
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from app.config import MONGODB_URI
from app.config import CMC_API_KEY
import requests

AGENT_REGISTRY = {}


def create_bridge_graph():
    def prepare_bridge_request(*args) -> Dict:
        """Prepares a cross-chain bridge request between Sonic and Solana."""
        params = json.loads(args[0])
        print("🔹 Bridge Request Initiated:", params)

        required_fields = ["fromChain", "amount", "fromToken"]
        for field in required_fields:
            if field not in params or not params[field]:
                return {"error": f"Missing required field: {field}"}
        recipientAddress = ""
        if "recipientAddress" in params:
            recipientAddress = params["recipientAddress"]
        return {
            "fromChain": params["fromChain"],
            "amount": params["amount"],
            "recipientAddress": recipientAddress,
            "success": True,
            "type": "bridge",
            "tokenSymbol": params["fromToken"]
        }

    bridge_tool = Tool(
        name="bridge_assets",
        func=prepare_bridge_request,
        description="Collects details for a cross-chain bridge transaction. "
                    "Ensure the following details are provided: "
                    "- `fromChain`: The chain you're bridging from. Only solanamainnet and sonicsvm chains are "
                    "allowed. If user"
                    "- `fromToken`: The token to be bridged. Only SOL, SONIC, sonicSOL, USDT, USDC, sSOL, lrtsSOL are "
                    "allowed. Example if the user provide Solana then pass it as SOL"
                    "provides any different chain then tell them only Solana and Sonic are allowed. have to "
                    "return only solanamainnet or sonicsvm. "
                    "- `amount`: The amount of tokens to bridge. This should be a number."
                    "- `recipientAddress`: The recipient wallet address on the destination chain. This is optional. "
                    "User May or may not provide the recipient address"
                    "Call this tool only when all parameters are correctly provided.",

    )

    # ✅ Bind LLM with tools
    llm_with_tools = llm.bind_tools([bridge_tool])

    # ✅ Define Assistant Node
    sys_msg = SystemMessage(
        content="Role: You are an AI-powered assistant specialized in handling cross-chain bridging between Sonic and "
                "Solana. Your task is to collect the necessary details from the user and ensure all parameters are "
                "correctly provided before preparing the bridge request. If There is a general question from the user "
                "apart from bridge answer general AI response."
                "Guidelines for Handling Bridge Requests:"
                "Validate the Source Chain (fromChain)"
                "The user can only bridge assets between Sonic and Solana."
                "If the user provides a different chain (e.g., Ethereum, Binance Smart Chain, etc.), inform them that "
                "only Solana and Sonic are allowed and ask them to select from the two."
                "Ensure the Bridge Amount (amount) is Provided"
                "The user must specify the amount of tokens to bridge."
                "If missing, prompt the user to enter a valid amount."
                "Recipient Address (recipientAddress) is Optional"
                "The user may or may not provide a recipient address."
                "If not provided, assume the recipient is the sender unless the user specifies otherwise."
    )

    def assistant(state: MessagesState):
        """
        - AI responds to normal chat.
        - If swap details are missing, it asks for them.
        - When all required params are collected, it calls the swap API.
        """

        response = llm_with_tools.invoke([sys_msg] + state["messages"])

        return {"messages": state["messages"] + [response]}  # No separate tool execution step

    builder = StateGraph(MessagesState)
    builder.add_node("tools", ToolNode([bridge_tool]))
    builder.add_node("assistant", assistant)
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)

    # ✅ Compile Graph
    mongodb_client = MongoClient(MONGODB_URI, tlsAllowInvalidCertificates=True, tlsAllowInvalidHostnames=True)
    checkpointer = MongoDBSaver(
        mongodb_client,
        db_name="new_memory",
        checkpoint_ns="AGY"
    )

    # ✅ Compile Graph & Register Multi-ABI Agent
    graph = builder.compile(checkpointer=checkpointer)
    AGENT_REGISTRY["bridgeAgent"] = {"graph": graph, "tools": [bridge_tool]}
    return graph


def create_swap_graph():
    allowed_tokens = {
        "SOL": "So11111111111111111111111111111111111111112",
        "USDT": "qPzdrTCvxK3bxoh2YoTZtDcGVgRUwm37aQcC3abFgBy",
        "USDC": "HbDgpvHVxeNSRCGEUFvapCYmtYfqxexWcCbxtYecruy8",
        "SONIC": "mrujEYaN1oyQXDHeYNxBYpxWKVkQ2XsGxfznpifu4aL",
        "sonicSOL": "CCaj4n3kbuqsGvx4KxiXBfoQPtAgww6fwinHTAPqV5dS",
        "sSOL": "DYzxL1BWKytFiEnP7XKeRLvgheuQttHW643srPG6rNRn",
        "lrtsSOL": "7JPHd4DQMwMnFSrKJQZzqabcrWfuRvsuWsxwuGbbmFfR",
    }

    allowed_swaps = {
        ("SOL", "SONIC"): "DgMweMfMbmPFChTuAvTf4nriQDWpf9XX3g66kod9nsR4",
        ("SOL", "sonicSOL"): "PVefkK6H5CL4qyBKmJaqFKYGM2bhzkpfwRhnMEUgXy4",
        ("USDT", "USDC"): "Q3xCT8sxU9VVYfHSmfQDahwGe9e43Q6hfEpLLi15yLo",
        ("SOL", "lrtsSOL"): "BeqkciWYCaAtn2FRaXrhfkWnWSgjnBB96ovZ4toJCTKW",
        ("SOL", "USDT"): "28UY6pGdJxvhhg1L45nrDe8j6RPUBuneL51RJ18NBcoz",
        ("SONIC", "USDT"): "3htP3trfRffLQSYf3ixJD3kx7kkKwEyPYJceCodt9UBz",
    }

    TOKEN_DESCRIPTION = "\n".join([f"- {name} ," for name, address in allowed_tokens.items()])
    SWAP_DESCRIPTION = "\n".join([f"- {pair[0]} → {pair[1]}" for pair, pool_id in allowed_swaps.items()])

    def prepare_swap_transaction(*args) -> Dict:
        """
        Validates swap parameters and prepares a swap transaction using Sega SDK.
        """
        params = json.loads(args[0])
        required_fields = ["fromToken", "toToken", "amount"]
        for field in required_fields:
            if field not in params or not params[field]:
                return {"error": f"Missing required field: {field}"}
        # Extract parameters
        from_token = params["fromToken"]
        to_token = params["toToken"]
        amount = params["amount"]

        # Validate token selection
        if from_token not in allowed_tokens.keys() or to_token not in allowed_tokens.keys():
            return {
                "error": "Invalid tokens. Allowed tokens are:\n" + "\n".join(
                    [f"{name}: {address}" for name, address in allowed_tokens.items()]
                )
            }

        swap_key = (from_token, to_token)
        print("Swap Key: ", swap_key)
        print("ALLOWED SWAPS", allowed_swaps.keys())
        if swap_key not in allowed_swaps.keys():
            return {
                "error": f"Invalid swap pair. Allowed swaps are:\n" + "\n".join(
                    [f"{pair[0]} → {pair[1]} (Pool: {pool_id})" for pair, pool_id in allowed_swaps.items()]
                )
            }

        print("Swap selected.....")
        # Get correct pool ID
        pool_id = allowed_swaps.get(swap_key)

        # Return formatted swap transaction
        return {
            "inputMint": allowed_tokens.get(from_token),
            "outputMint": allowed_tokens.get(to_token),
            "amount": amount,
            "poolId": pool_id,
            "success": True,
            "type": "swap"
        }

    swap_tool = Tool(
        name="swap_tokens",
        func=prepare_swap_transaction,
        description=f"Prepares a token swap transaction on Sega SDK.\n\n"
                    f" **Allowed Tokens:**\n{TOKEN_DESCRIPTION}\n\n"
                    f" **Allowed Swap Pairs:**\n{SWAP_DESCRIPTION}\n\n"
                    "- `fromToken` & `toToken` must be valid token names or addresses.\n"
                    "- `amount` must be the number \n"
                    "- Only specific token pairs are allowed for swapping.\n"
                    "Call this tool only when all parameters are correctly provided.(fromToken,toToken,amount) "
    )

    # ✅ Bind LLM with tools
    llm_with_tools = llm.bind_tools([swap_tool])

    # ✅ Define Assistant Node
    sys_msg = SystemMessage(
        content="You are an AI-powered Swap Agent responsible for guiding users through the process of swapping tokens."
    )

    def assistant(state: MessagesState):
        """
        - AI responds to normal chat.
        - If swap details are missing, it asks for them.
        - When all required params are collected, it calls the swap API.
        """

        response = llm_with_tools.invoke([sys_msg] + state["messages"])

        return {"messages": state["messages"] + [response]}  # No separate tool execution step

    builder = StateGraph(MessagesState)
    builder.add_node("tools", ToolNode([swap_tool]))
    builder.add_node("assistant", assistant)
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)
    # ✅ Compile Graph
    mongodb_client = MongoClient(MONGODB_URI, tlsAllowInvalidCertificates=True, tlsAllowInvalidHostnames=True)
    checkpointer = MongoDBSaver(
        mongodb_client,
        db_name="new_memory",
        checkpoint_ns="AGY"
    )

    # ✅ Compile Graph & Register Multi-ABI Agent
    graph = builder.compile(checkpointer=checkpointer)
    AGENT_REGISTRY["swapAgent"] = {"graph": graph, "tools": [swap_tool]}
    return graph


def coin_market_cap_graph():
    API_KEY = CMC_API_KEY
    BASE_URL = "https://pro-api.coinmarketcap.com/v1"

    def get_all_crypto_prices(symbols: str) -> dict:
        """
        Fetches the latest price data for given cryptocurrencies and returns an AI-friendly response as JSON.
        """
        if not symbols or not isinstance(symbols, str):
            return {"response": "Invalid input. Please provide a valid list of cryptocurrency symbols."}

        # Clean and process the symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return {"response": "No valid cryptocurrency symbols provided."}

        symbols_str = ",".join(symbol_list)
        quotes_url = f"{BASE_URL}/cryptocurrency/quotes/latest?symbol={symbols_str}"
        headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": API_KEY
        }

        response = requests.get(quotes_url, headers=headers)
        if response.status_code != 200:
            return {"response": f"Failed to fetch data. Status code: {response.status_code}"}

        price_data = response.json()
        if "data" not in price_data:
            return {"response": "Invalid response from API. Please try again later."}

        # Construct a readable response string
        response_text = []
        for symbol in symbol_list:
            if symbol in price_data["data"]:
                crypto_data = price_data["data"][symbol]
                price_info = crypto_data["quote"]["USD"]
                response_text.append(
                    f"🔹 **{crypto_data['name']} ({crypto_data['symbol']})**\n"
                    f"   - Price: ${price_info['price']:.2f}\n"
                    f"   - Market Cap: ${price_info['market_cap']:.2f}\n"
                    f"   - 24h Change: {price_info['percent_change_24h']:.2f}%\n"
                )
            else:
                response_text.append(f"⚠️ {symbol}: Symbol not found or invalid.")

        return {"response": "\n".join(response_text), "success": True, "type":"coinMarketCap"}

    crypto_price_tool = Tool(
        name="get_all_crypto_prices",
        func=get_all_crypto_prices,
        description=(
            "Fetches the latest price, market cap, and 24-hour price changes for specified cryptocurrencies from the CoinMarketCap API. "
            "Ensure that valid cryptocurrency symbols are provided as input. "
            "If users provide cryptocurrency names instead of symbols, convert them to their corresponding symbols before using this tool. "
            "Call this tool only when all required parameters are correctly provided."
        )
    )

    def get_global_crypto_metrics(*args, **kwargs) -> dict:
        """
        Fetches global cryptocurrency market metrics and returns an AI-friendly response.
        """
        metrics_url = f"{BASE_URL}/global-metrics/quotes/latest"
        headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": API_KEY
        }

        try:
            response = requests.get(metrics_url, headers=headers)
            if response.status_code != 200:
                return {"response": f"Failed to fetch global crypto metrics. Status code: {response.status_code}"}

            data = response.json()
            if "data" not in data:
                return {"response": "Invalid response structure from API."}

            metrics_data = data["data"]
            quotes = metrics_data.get("quote", {})

            # Extracting the USD quote if available
            usd_quote = quotes.get("USD", {})

            # Building the response string
            response_text = (
                f"🌍 **Global Crypto Market Metrics**\n"
                f"- Active Cryptocurrencies: {metrics_data.get('active_cryptocurrencies')}\n"
                f"- Total Cryptocurrencies: {metrics_data.get('total_cryptocurrencies')}\n"
                f"- Active Market Pairs: {metrics_data.get('active_market_pairs')}\n"
                f"- BTC Dominance: {metrics_data.get('btc_dominance', 0):.2f}%\n"
                f"- ETH Dominance: {metrics_data.get('eth_dominance', 0):.2f}%\n"
                f"- Total Market Cap: ${usd_quote.get('total_market_cap', 0):,.2f}\n"
                f"- 24h Trading Volume: ${usd_quote.get('total_volume_24h', 0):,.2f}\n"
                f"- 24h Market Cap Change: {usd_quote.get('total_market_cap_yesterday_percentage_change', 0):.2f}%\n"
                f"- 24h Volume Change: {usd_quote.get('total_volume_24h_yesterday_percentage_change', 0):.2f}%\n"
                f"- Last Updated: {metrics_data.get('last_updated')}\n"
            )

            return {"response": response_text, "success": True, "type":"coinMarketCap"}

        except Exception as e:
            return {"response": f"An error occurred while fetching data: {str(e)}", "success": False, "type":"coinMarketCap"}

    global_crypto_metrics_tool = Tool(
        name="get_global_crypto_metrics",
        func=get_global_crypto_metrics,
        description=(
            "Fetches global cryptocurrency market metrics including market cap, trading volume, BTC & ETH dominance, "
            "stablecoin & DeFi statistics."
        )
    )

    # Bind AI model with tools
    llm_with_tools = llm.bind_tools([crypto_price_tool, global_crypto_metrics_tool])

    sys_msg = SystemMessage(
        content=(
            "You are an AI-powered Crypto Market Assistant. Your role is to provide real-time cryptocurrency price data, "
            "global market metrics, and insights into DeFi, stablecoins, and derivatives. Use the available tools to fetch "
            "accurate data from CoinMarketCap and guide users through their queries effectively."
        )
    )

    def assistant(state: MessagesState):
        """
        AI responds to cryptocurrency-related queries.
        - Calls get_all_crypto_prices tool for price queries.
        - Calls get_global_crypto_metrics for market metrics queries.
        """
        response = llm_with_tools.invoke([sys_msg] + state["messages"])
        return {"messages": state["messages"] + [response]}

    # Define state graph
    builder = StateGraph(MessagesState)
    builder.add_node("tools", ToolNode([crypto_price_tool, global_crypto_metrics_tool]))
    builder.add_node("assistant", assistant)
    builder.add_edge(START, "assistant")

    def tools_condition(state: MessagesState) -> str:
        # Implement your condition for routing here
        return "tools"

    builder.add_conditional_edges("assistant", tools_condition)
    mongodb_client = MongoClient(MONGODB_URI, tlsAllowInvalidCertificates=True, tlsAllowInvalidHostnames=True)
    checkpointer = MongoDBSaver(
        mongodb_client,
        db_name="new_memory",
        checkpoint_ns="AGY"
    )

    # ✅ Compile Graph & Register Multi-ABI Agent
    graph = builder.compile(checkpointer=checkpointer)

    AGENT_REGISTRY["coinMarketCapAgent"] = {
        "graph": graph,
        "tools": [crypto_price_tool, global_crypto_metrics_tool]
    }

    return graph


def get_last_ai_message(response_data):
    """
    Extracts the content of the last AIMessage from the response data.
    """
    messages = response_data.get("messages", [])

    # Iterate in reverse to find the last AI message
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:  # Ensure it's an AI message with content
            return message.content

    return "No valid AI response found."


def get_last_message(message):
    response_payload = {
        "ai_message": "None",
        "tool_response": "None"
    }
    if isinstance(message, AIMessage) and message.content:
        response_payload = {
            "ai_message": message.content,
            "tool_response": "None"
        }
    if isinstance(message, ToolMessage) and message.content:
        response_payload = {
            "ai_message": "None",
            "tool_response": message.content
        }
    return response_payload


def get_relevant_tool_message(response_data):
    """
    Extracts the last ToolMessage before the last AIMessage.
    If the last AIMessage doesn't have a preceding ToolMessage, find the most recent one before it.
    """
    messages = response_data.get("messages", [])

    last_ai_index = None
    last_tool_message = None

    # Iterate in reverse to locate the last AIMessage
    for i in range(len(messages) - 1, -1, -1):
        message = messages[i]

        if isinstance(message, AIMessage):
            if last_ai_index is None:
                last_ai_index = i  # Store the index of the last AIMessage
            else:
                break  # Stop when encountering an earlier AIMessage

        if isinstance(message, ToolMessage):
            last_tool_message = message.content  # Store the most recent ToolMessage

        # If we found an AIMessage and already stored a ToolMessage before it, return it
        if last_ai_index is not None and last_tool_message:
            return last_tool_message

    return "None"


def load_agents_on_startup():
    """
    Loads agents from the database into memory on startup.
    """
    print("Agent loaded successfully!")
    create_bridge_graph()
    create_swap_graph()
    coin_market_cap_graph()
