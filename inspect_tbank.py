import os
from t_tech.invest import Client
from t_tech.invest.services import OperationsService
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TBANK_API_TOKEN")


def inspect():
    with Client(TOKEN) as client:
        users = client.users
        accounts = users.get_accounts().accounts
        print(f"Found {len(accounts)} accounts.")

        operations: OperationsService = client.operations

        for account in accounts:
            print(f"\n--- Account: {account.id} ({account.name}) ---")
            portfolio = operations.get_portfolio(account_id=account.id)

            print("Portfolio keys:", dir(portfolio))
            print("Portfolio data:", portfolio)

            # Check if there's a specific field for expected yield per day
            # Usually it's in the portfolio object or we sum positions

            if hasattr(portfolio, "expected_yield"):
                print("Total Yield:", portfolio.expected_yield)

            # Check positions briefly
            if hasattr(portfolio, "positions") and portfolio.positions:
                print("First position sample:", portfolio.positions[0])

            break  # Just need one to see structure


if __name__ == "__main__":
    inspect()
