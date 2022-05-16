import csv
import json

from datetime import datetime, date, timedelta
from re import T
from time import sleep
from pycoingecko import CoinGeckoAPI
from pymongo import MongoClient

def get_id_by_ticker(coinlist: dict, ticker: str) -> str:
    for coin in coinlist:
        if coin["symbol"] == ticker:
            return coin["id"]
    # TODO add case where coin doesn't exist, and add it


def load_coinlist() -> dict:
    with open("coinlist.json", "r") as read_file:
        data = json.load(read_file)
    return data


def load_tickers() -> dict:
    with open("tickers.json", "r") as read_file:
        data = json.load(read_file)
    return data


def save_tickers(data: dict):
    with open("tickers.json", "w") as write_file:
        json.dumps(data, write_file)


def get_price_from_response(response: dict, currency: str = "usd") -> float:
    return float(response["market_data"]["current_price"][currency])


def calculate_totals(totals: dict, id: str, price: float, count: float) -> dict:
    if id not in totals:
        totals[id] = {"count_received": 0, "rewards_total": 0}
    gains = price * count
    totals["rewards"] += gains
    totals[id]["count_received"] += count
    totals[id]["rewards_total"] += gains


def main():
    totals = {"rewards": 0}
    cg = CoinGeckoAPI()
    coin_list = load_coinlist()
    tickers = load_tickers()
    new_ticker = False

    with open("history.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["tx_type"] == "STAKING":
                date = datetime.strptime(
                    row["timestamp"], "%Y-%m-%d %H:%M:%S"
                ).strftime("%d-%m-%Y")
                ticker = row["received_currency"].lower()
                if row["received_currency"] not in tickers:
                    id = get_id_by_ticker(coin_list, ticker)
                    tickers[ticker] = id
                    new_ticker = True
                try:
                    response = cg.get_coin_history_by_id(id, date, localization=False)
                    sleep(1.5)
                except:
                    print("Max timer reached")
                    sleep(60)
                    response = cg.get_coin_history_by_id(id, date, localization=False)
                price = get_price_from_response(response)
                count = float(row["received_amount"])
                calculate_totals(totals, id, price, count)

    for total in totals.keys():
        print(
            f"USD Total from {total}: {totals[total]['rewards_total']} from {totals[total][id]['count_received']}"
        )
    print(f"Total rewards earned: {totals['rewards']}")

    if new_ticker:
        save_tickers(tickers)

def populate_prices():
    cg = CoinGeckoAPI()
    client = MongoClient("mongodb://localhost:27017")
    db = client.osmosis_taxes
    token = {
        'id': 'cosmos',
        'ticker': 'atom',
        'name': 'Cosmos Hub',
        'prices': {

        }
    }

    start_date = date(2021, 6, 1)
    end_date = date.today()
    delta = timedelta(days=1)
    while start_date <= end_date:
        try: 
            response = cg.get_coin_history_by_id(token['id'], start_date.strftime("%d-%m-%Y"), localization=False)
            sleep(1.5)
        except Exception as e:
            print(f'Exception: {e}')
            sleep(60)
            response = cg.get_coin_history_by_id(id, start_date, localization=False)
        price = get_price_from_response(response)
        print(f"Price of {token['id']} on {start_date} was ${price}")
        token['prices'][start_date] = price
        start_date += delta
    db.prices.insert_one(token)
    

if __name__ == "__main__":
    # main()
    populate_prices()
