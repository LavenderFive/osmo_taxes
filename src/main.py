import csv

from pycoingecko import CoinGeckoAPI

def main():
    cg = CoinGeckoAPI() 
    print(cg.get_price(ids='bitcoin', vs_currencies='usd'))

if __name__ == "__main__":
   main()
