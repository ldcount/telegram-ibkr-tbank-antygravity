import logging
from pybit.unified_trading import HTTP
from app.config import Config

logger = logging.getLogger(__name__)


class BybitClient:
    ASSET_OVERVIEW_PATH = "/v5/asset/asset-overview"

    STABLECOINS_1_TO_1_USD = {
        "USD",
        "USDT",
        "USDC",
        "USDE",
        "USDD",
        "FDUSD",
        "PYUSD",
        "TUSD",
    }

    def __init__(self):
        self.api_key = Config.BYBIT_API_KEY
        self.api_secret = Config.BYBIT_API_SECRET
        self.client = None

        if self.api_key and self.api_secret:
            try:
                self.client = HTTP(
                    testnet=False, api_key=self.api_key, api_secret=self.api_secret
                )
            except Exception as e:
                logger.error(f"Failed to initialize Bybit client: {e}")
        else:
            logger.warning("Bybit API credentials not found.")

    def get_balance_usd(self) -> float:
        """
        Fetch the total Bybit balance in USD across all Bybit asset buckets.

        Bybit's asset overview endpoint includes balances from account types
        like Unified Trading, Funding, and TradFi in one valuation currency.
        Fall back to the legacy UNIFIED + FUND aggregation if the newer
        endpoint is unavailable for the current API key or SDK.
        """
        if not self.client:
            logger.error("Bybit client not initialized.")
            raise RuntimeError("Bybit client not initialized")

        try:
            return self._get_asset_overview_balance_usd()

        except Exception as e:
            logger.warning(
                "Bybit asset overview failed, falling back to legacy balance "
                f"aggregation: {e}"
            )
            try:
                unified_total_usd = self._get_unified_balance_usd()
                fund_total_usd = self._get_fund_balance_usd()
                return unified_total_usd + fund_total_usd
            except Exception as fallback_error:
                logger.error(f"Error fetching Bybit balance: {fallback_error}")
                raise

    def _get_asset_overview_balance_usd(self) -> float:
        response = self.client._submit_request(
            method="GET",
            path=f"{self.client.endpoint}{self.ASSET_OVERVIEW_PATH}",
            query={"valuationCurrency": "USD"},
            auth=True,
        )

        if response.get("retCode") != 0:
            msg = f"Bybit asset overview API Error: {response.get('retMsg')}"
            logger.error(msg)
            raise RuntimeError(msg)

        result = response.get("result", {})
        total_equity = result.get("totalEquity")

        if total_equity is not None:
            return float(total_equity)

        account_list = result.get("list", [])
        if not account_list:
            logger.warning("Bybit asset overview: No accounts found in response.")
            return 0.0

        return sum(float(account.get("totalEquity") or 0.0) for account in account_list)

    def _get_unified_balance_usd(self) -> float:
        # Request the UNIFIED account from Bybit. This is the trading account
        # equity that the previous bot version already used.
        response = self.client.get_wallet_balance(accountType="UNIFIED")

        if response.get("retCode") != 0:
            msg = f"Bybit UNIFIED API Error: {response.get('retMsg')}"
            logger.error(msg)
            raise RuntimeError(msg)

        result = response.get("result", {})
        list_accounts = result.get("list", [])

        if not list_accounts:
            logger.warning("Bybit UNIFIED: No accounts found in response.")
            return 0.0

        account_info = list_accounts[0]
        return float(account_info.get("totalEquity", 0.0))

    def _get_fund_balance_usd(self) -> float:
        # Request the FUND account from Bybit. The mobile app total can include
        # this wallet, but it is not included in UNIFIED totalEquity.
        response = self.client.get_coins_balance(accountType="FUND")

        if response.get("retCode") != 0:
            msg = f"Bybit FUND API Error: {response.get('retMsg')}"
            logger.error(msg)
            raise RuntimeError(msg)

        balances = response.get("result", {}).get("balance", [])
        total_fund_usd = 0.0

        for balance in balances:
            coin = balance.get("coin", "")
            wallet_balance = float(balance.get("walletBalance") or 0.0)
            if wallet_balance <= 0:
                continue

            usd_rate = self._get_coin_usd_rate(coin)
            total_fund_usd += wallet_balance * usd_rate

        return total_fund_usd

    def _get_coin_usd_rate(self, coin: str) -> float:
        coin = (coin or "").upper()
        if not coin:
            return 0.0

        if coin in self.STABLECOINS_1_TO_1_USD:
            return 1.0

        for quote_coin in ("USDT", "USDC"):
            if coin == quote_coin:
                return 1.0

            response = self.client.get_tickers(
                category="spot", symbol=f"{coin}{quote_coin}"
            )
            if response.get("retCode") != 0:
                continue

            tickers = response.get("result", {}).get("list", [])
            if not tickers:
                continue

            last_price = tickers[0].get("lastPrice")
            if last_price:
                return float(last_price)

        logger.warning(f"Bybit FUND: Could not price coin {coin} in USD. Ignoring it.")
        return 0.0
