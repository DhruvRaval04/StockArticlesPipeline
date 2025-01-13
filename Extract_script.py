import requests
import pandas as pd
import numpy as np
from datetime import datetime

def run_stock_etl():
    # Fetching data from the first API
    stockdata = requests.get('https://api.stockdata.org/v1/news/all?countries=us,ca&language=en&api_token=xbGGrZ1B4MXQBuQwpdyBRlSKywQkDJaId5On0u6j')   

    if stockdata.status_code != 200:
        print(f"Error stockdata: API returned status code {stockdata.status_code}")
        print(f"Response stockdata: {stockdata.text}")
        return

    stockdata_response = stockdata.json()

    # Processing stockdata
    df_1 = pd.DataFrame(stockdata_response["data"])
    df_1.drop(['uuid', 'image_url', 'language', 'entities', 'similar', 'relevance_score'], axis=1, inplace=True)

    tickers = []
    names = []
    scores = []
    industries = []

    rowcount = 0
    for article in stockdata_response["data"]:
        if 'entities' in article and article['entities']:
            new_row = df_1.loc[rowcount].copy()
            duplicatedrows = len(article['entities']) - 1
            df_1 = df_1._append([new_row] * duplicatedrows, ignore_index=True)

            for entity in article['entities']:
                tickers.append(entity.get('symbol', None))
                names.append(entity.get('name', None))
                scores.append(entity.get('sentiment_score', None))
                industries.append(entity.get('industry', None))

        rowcount += 1

    df_1['ticker'] = tickers
    df_1['names'] = names
    df_1['sentiment score'] = scores
    df_1['industry'] = industries
    df_1 = df_1.rename({'sentiment score': 'ticker_sentiment'}, axis=1)
    df_1.drop(columns='names', inplace=True)

    # Fetching data from the second API
    alphavantage = requests.get('https://www.alphavantage.co/query?function=NEWS_SENTIMENT&limit=10&apikey=J6SDVR8XMY3RQLMQ')

    if alphavantage.status_code != 200:
        print(f"Error alphavantage: API returned status code {alphavantage.status_code}")
        print(f"Response alphavantage: {alphavantage.text}")
        return

    alphavantage_response = alphavantage.json()

    # Processing alphavantage
    df_2 = pd.DataFrame(alphavantage_response["feed"])
    df_2.drop(['banner_image', 'authors', 'category_within_source', 'topics', 'source', 'overall_sentiment_label'], axis=1, inplace=True)

    topics = []
    for element in alphavantage_response["feed"]:
        templist = [topic["topic"] for topic in element["topics"]]
        topics.append(', '.join(templist))
    df_2['industry'] = topics

    tickers_2 = []
    ticker_sentiment_2 = []
    rowcount_2 = 0

    for element in alphavantage_response["feed"]:
        if 'ticker_sentiment' in element and element['ticker_sentiment']:
            for ticker in element["ticker_sentiment"]:
                tickers_2.append(ticker['ticker'])
                ticker_sentiment_2.append(ticker['ticker_sentiment_score'])

            duplicatedrows = len(element['ticker_sentiment']) - 1
            if duplicatedrows > 0:
                new_row = df_2.iloc[rowcount_2].copy()
                df_2 = pd.concat([df_2, pd.DataFrame([new_row] * duplicatedrows)], ignore_index=True)
        else:
            tickers_2.append(None)
            ticker_sentiment_2.append(None)
        rowcount_2 += 1

    if len(df_2) != len(tickers_2):
        raise ValueError(f"Row mismatch: DataFrame rows ({len(df_2)}) and tickers ({len(tickers_2)})")

    df_2['ticker'] = tickers_2
    df_2['ticker_sentiment'] = ticker_sentiment_2
    df_2.drop(df_2[df_2.title == 'Before you continue'].index, inplace=True)
    df_2 = df_2.rename({'summary': 'description', 'time_published': 'published_at', 'source_domain': 'source'}, axis=1)

    df_final = pd.concat([df_1, df_2], ignore_index=True)
    df_final.sort_values('published_at', inplace=True)

    current_time = datetime.now()
    df_final.to_csv(f's3://stock-datanews-etl-bucket/{current_time}_stocknewsdata.csv')