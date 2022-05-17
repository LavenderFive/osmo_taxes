import csv
import json

from datetime import datetime, date, timedelta
from re import T
from time import sleep
from pycoingecko import CoinGeckoAPI
from pymongo import MongoClient


def get_coin_by_ticker(coinlist: dict, ticker: str) -> dict:
    for coin in coinlist:
        if coin["symbol"] == ticker:
            return coin
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
        json.dump(data, write_file)


def get_price_from_response(response: dict, currency: str = "usd") -> float:
    return float(response["market_data"]["current_price"][currency])


def calculate_totals(totals: dict, id: str, price: float, count: float) -> dict:
    if id not in totals:
        totals[id] = {"count_received": 0, "rewards_total": 0}
    gains = price * count
    totals["rewards"] += gains
    totals[id]["count_received"] += count
    totals[id]["rewards_total"] += gains


def get_coin_price_by_date(coin_history: dict, date: str) -> float:
    price_history = coin_history["prices"]
    for price in price_history:
        if price["date"] == date:
            return price["price"]
    return None


def main():
    client = MongoClient("mongodb://localhost:27017")
    db = client.osmosis_taxes
    totals = {"rewards": 0}
    cg = CoinGeckoAPI()
    coin_list = load_coinlist()
    tickers = load_tickers()
    new_ticker = False
    coinprices = {}

    with open("default.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["tx_type"] == "STAKING":
                date = datetime.strptime(
                    row["timestamp"], "%Y-%m-%d %H:%M:%S"
                ).strftime("%d-%m-%Y")
                ticker = row["received_currency"].lower()
                if ticker not in tickers.keys():
                    print(f"Ticket: {ticker} not in tickers: {tickers}")
                    coin = get_coin_by_ticker(coin_list, ticker)
                    tickers[ticker] = coin["id"]
                    new_ticker = True
                    populate_prices(coin)
                id = tickers[ticker]
                if id not in coinprices.keys():
                    coinprices[id] = db.prices.find_one(
                        {"id": id}
                    )
                price = get_coin_price_by_date(coinprices[id], date)
                if price:
                    count = float(row["received_amount"])
                    calculate_totals(totals, id, price, count)
                else: 
                    print(f'id: {id}, date: {date}, row: {row}')

    for total in totals.keys():
        if total == 'rewards':
            continue
        print(
            f"USD Total from {total}: ${totals[total]['rewards_total']} from {totals[total]['count_received']} tokens."
        )
    print(f"Total rewards earned: {totals['rewards']}")

    if new_ticker:
        save_tickers(tickers)


def populate_prices(coin: dict):
    cg = CoinGeckoAPI()
    client = MongoClient("mongodb://localhost:27017")
    db = client.osmosis_taxes
    token = {
        "id": coin["id"],
        "ticker": coin["symbol"],
        "name": coin["name"],
        "prices": [],
    }
    start_date = date(2021, 6, 1)

    existing_token = db.prices.find_one({"id": coin["id"]})
    if existing_token:
        latest_date = existing_token["prices"][-1]["date"]
        token["prices"] = existing_token["prices"]
        start_date = datetime.strptime(latest_date, "%d-%m-%Y").date()
        print(f"Start Date with price history: {start_date}")

    end_date = date.today()
    delta = timedelta(days=1)
    while start_date <= end_date:
        formatted_date = start_date.strftime("%d-%m-%Y")
        try:
            response = cg.get_coin_history_by_id(
                token["id"], formatted_date, localization=False
            )
            sleep(1.25)
        except Exception as e:
            print(f"Exception: {e}")
            sleep(60)
            continue
        if "market_data" not in response:
            start_date += delta
            continue
        price = get_price_from_response(response)
        print(f"Date: {formatted_date}, Price: {price}")
        token["prices"].append({"date": formatted_date, "price": price})
        start_date += delta

    if existing_token:
        db.prices.update_one({"id": coin["id"]}, {"$set": {"prices": token["prices"]}})
    else:
        db.prices.insert_one(token)
    client.close()


if __name__ == "__main__":
    token = {"id": "osmosis", "symbol": "osmo", "name": "Osmosis"}

    main()
    # populate_prices(token)

# https://lcd-osmosis.keplr.app/osmosis/gamm/v1beta1/pools?pagination.limit=10000
