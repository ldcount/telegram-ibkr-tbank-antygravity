import logging
from pybit.unified_trading import HTTP
from app.config import Config

logger = logging.getLogger(__name__)


class BybitClient:
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
        Fetches the total equity in USD from the Unified Trading Account.
        """
        if not self.client:
            logger.error("Bybit client not initialized.")
            raise RuntimeError("Bybit client not initialized")

        try:
            # For Unified Trading Account, get_wallet_balance returns equity.
            # We usually want 'accountType'='UNIFIED'
            response = self.client.get_wallet_balance(accountType="UNIFIED")

            # Response structure check
            if response.get("retCode") != 0:
                msg = f"Bybit API Error: {response.get('retMsg')}"
                logger.error(msg)
                raise RuntimeError(msg)

            result = response.get("result", {})
            list_accounts = result.get("list", [])

            if not list_accounts:
                logger.warning("Bybit: No accounts found in response.")
                return 0.0

            # Access the first account info
            account_info = list_accounts[0]
            total_equity_usd = account_info.get("totalEquity", 0.0)

            return float(total_equity_usd)

        except Exception as e:
            logger.error(f"Error fetching Bybit balance: {e}")
            raise
