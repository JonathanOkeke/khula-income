import json
import numpy as np
import pandas as pd
from flask import Flask, request

def prepare_data(data: pd.DataFrame):
  
  data['date'] = pd.to_datetime(data.date)
  data['month'] = data['date'].dt.month
  data['year'] = data['date'].dt.year
  data['year-month'] = data['year'].astype(str) + data['month'].astype(str)
  data['group'] = np.where(data.category == 'Salaries/Wages', 'Income', 'Expenses')
  data['credit'] = np.where(data['amount'] > 0, data['amount'], 0.0)
  data['debit'] = np.where(data['amount'] < 0, data['amount'], 0.0)
  data['tx'] = data['credit'] + data['debit']
  data = data.sort_values(by='date')
  
  return data

def get_balance(df: pd.DataFrame):
  
  if df.loc[df['category'] == 'Salaries/Wages', :].empty:
        return None
  pay_day = df.loc[df['category'] == 'Salaries/Wages', :].date.max()
  df_tx = df.groupby('date').agg({'tx':'sum'})
  ending_balance = df_tx.tx.values[-1]
  starting_balance =  ending_balance - df_tx['tx'].sum()
  df_tx['running_balance'] = starting_balance + df_tx['tx'].cumsum()
  df_index = pd.date_range(df_tx.index.min(),df_tx.index.max())
  df_daily = pd.DataFrame(df_tx['running_balance'])
  df_daily = df_daily.reindex(df_index, fill_value=np.nan)
  df_daily = df_daily.fillna(method='ffill')
  idx = (pay_day - df_daily.index[0]).days - 1
  balance = df_daily.values[idx][0]
  
  return balance

app = Flask(__name__)

@app.route('/')
def hello():
  return 'Hello there'


@app.route('/balance', methods=['POST'])
def balance():
  json_data = request.get_json(force=True)
  data_df = pd.json_normalize(json_data)
  data = prepare_data(data_df)
  data_splits = list(data['year-month'].unique())
  balances = []
  for split in data_splits:
      year = int(split[:4])
      month = int(split[4:])
      df_split = data.query(f"year == {year} and month == {month}")
      balance = get_balance(df_split)
      balances.append(balance)

  balances = list(filter(None, balances))
  avg_balance = np.array(balances).mean()
  print(avg_balance)
  res = {'balance': avg_balance}
  
  return json.dumps(res)
