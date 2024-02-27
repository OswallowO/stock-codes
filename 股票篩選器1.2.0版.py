#更新日誌(2024/02/25更新)
#2/21完成基礎程式建置
#2/23完成ema資料建立與導出
#2/24完成BB_KC計算公式與股價、成交量篩選公式
#2/25完成整體程式與優化


import yfinance as yf
import numpy as np
import requests as r
from lxml import etree
import warnings
import pandas as pd

import importlib

def install_missing_packages(package_names):
    for package_name in package_names:
        try:
            importlib.import_module(package_name)
            print('正在安裝套件...')
        except ImportError:
            print(f"Installing {package_name}...")
            import subprocess
            subprocess.check_call(["pip", "install", package_name])
            
# 要检查的库列表
required_packages = ["yfinance", "numpy", "requests", "lxml", "pandas"]

# 检查并安装缺少的库
install_missing_packages(required_packages)

print('套件安裝完成！\n')

# 隱藏警告訊息
warnings.filterwarnings("ignore")

def twse_stock_codes():
    # 下載上市證券國際證券辨識號碼一覽表
    url = 'https://isin.twse.com.tw/isin/C_public.jsp?strMode=2'
    res = r.get(url)
    root = etree.HTML(res.text)
    data = root.xpath('//tr')[1:]
    
    # 儲存符合條件的股票代碼及名稱的清單
    stock_list = []
    
    # 提取每一列的股票代碼和名稱
    for row in data:
        # 檢查是否存在第一個td元素
        tds = row.xpath('.//td')
        if tds:
            row_data = tds[0].text
            if row_data is not None:  # 確保row_data存在
                # 只保留代碼部分並過濾掉非數字的代碼
                stock = ''.join(filter(str.isdigit, row_data))
                if stock and len(stock) <= 4:  # 過濾掉4個數字以上的股票代號
                    stock_code_and_name = tds[0].text.strip()
                    stock_name = stock_code_and_name.split('\u3000', 1)[1]
                    stock_list.append((stock + ".TW", stock_name))  # 將股票代碼和名稱作為一個tuple加入清單
    
    return stock_list


stock_info = twse_stock_codes()
stock_names = [stock[1] for stock in stock_info]

# 取得股票代碼列表
stock_codes = [stock[0] for stock in stock_info]

'''
print(stock_codes)
'''

stock_data_2 = yf.download(stock_codes, period="5d", interval="1d")

filter_stocks = []

# 篩選條件：前一日股價介於10和50之間，前一日成交量大於3,000,000
for symbol in stock_codes:

    # 取得特定股票的最後一個交易日的股價和成交量
    last_day_price = stock_data_2.loc[stock_data_2.index[-1], ('Close', symbol)]
    last_day_volume = stock_data_2.loc[stock_data_2.index[-1], ('Volume', symbol)]

    if 10 <= last_day_price <= 50 and last_day_volume > 3000000:
        filter_stocks.append(symbol)
        '''
        print(f"股票代碼 {symbol} 符合篩選條件")
        '''
'''
print("篩選後的股票清單：", filter_stocks)
'''
print('\n已成功篩選成交量大於3,000,000股且股價介於$10~$50之股票！\n')
# 初始定義 ema_data
ema_data = pd.DataFrame()

def get_ema_data(stock_codes):
    try:
        # 下載股票數據  
        stock_data = yf.download(stock_codes, period="1mo", interval="60m")

        # 計算收盤價的EMA
        close_prices = stock_data['Close']
        ema = close_prices.ewm(span=20, adjust=False).mean()

        # 得到最後40個EMA值
        last_40_ema = ema.iloc[-40:]
        return last_40_ema
        
    except Exception as e:
        return None
    
# 取得最後40條K線的原始K線數據
kline_data = yf.download(filter_stocks, period="1mo", interval="60m").iloc[-40:]
print('\n成功下載K線資料！\n')

'''
for col in kline_data.columns:
    print(col)
'''
'''
print("Kline_data：")
print(kline_data)
'''
# 取得最後40根K線的 EMA 數據
ema_data = get_ema_data(filter_stocks)
print('\n已成功建立EMA資料！\n')
'''
print("ema_data：")
print(ema_data)
'''
if ema_data is not None:
    # 計算布林通道數據
    SMA = kline_data['Close'].rolling(window=20).mean()
    '''
    print('SMA：')
    print(SMA)
    '''
    SD = kline_data['Close'].rolling(window=20).std()
    BB_upper = SMA + 2 * SD
    BB_lower = SMA - 2 * SD
    '''
    print('BB_upper：')
    print(BB_upper)
    print('BB_lower：')
    print(BB_lower)
    '''
    # 計算每根K線的KC_BASIS、KC_UPPER和KC_LOWER
    KC_basis = ema_data
    
def calculate_atr(close_data, high_data, low_data):
    high_low = high_data - low_data
    high_close = np.abs(high_data - close_data.shift())
    low_close = np.abs(low_data - close_data.shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(14).mean()
    return atr


atr_data = pd.DataFrame()

for ticker in filter_stocks:

    close_data = kline_data['Close', ticker]
    high_data = kline_data['High', ticker]
    low_data = kline_data['Low', ticker]

    # 計算出atr數值
    atr = calculate_atr(close_data, high_data, low_data)

    # 將計算得到的atr值加入atr_data的DataFrame中
    atr_data[ticker] = atr

# 將 atr_data的DataFrame和filter_stocks、stock_codes合併
atr_data.index = kline_data.index

'''
print('ATR：')
print(atr_data)
'''
crossed_list = []
if ema_data is not None:
    KC_upper = KC_basis + 1.5 * atr_data
    KC_lower = KC_basis - 1.5 * atr_data
    '''
    print('KC_upper：')
    print(KC_upper)

    print('kc_lower：')
    print(KC_lower)
    '''
    
    # 檢查最後20根K棒的BB_upper和KC_upper是否有交叉  
    crossed_upper1 = BB_upper.iloc[-20:].gt(KC_upper.iloc[-20:]).any()
    crossed_upper2 = BB_upper.iloc[-20:].lt(KC_upper.iloc[-20:]).any()

    crossed_lower1 = BB_lower.iloc[-20:].gt(KC_lower.iloc[-20:]).any()
    crossed_lower2 = BB_lower.iloc[-20:].lt(KC_lower.iloc[-20:]).any()
    
    crossed_set = set()
    for ticker in filter_stocks:
        if crossed_lower1.any() or crossed_lower2.any() or crossed_upper1.any() or crossed_upper2.any():
            crossed_list.append(ticker)

            crossed_set.add(ticker)
else:
    print(f"數據不足。")

print('已成功篩選發生過布林通道與肯特納通道交叉之股票！\n')

'''
for ticker in crossed_set:
    print(ticker, end='\n')
'''
print('列出結果： ')
print('股票代號\t\t\t股票網址')

for ticker in crossed_set:
    url = f"https://tw.tradingview.com/chart/ifVxylSI/?symbol=TWSE%3A{ticker.split('.')[0]}"
    print(f"{ticker}\t\t\t\t{url}") #印出篩選結果

crossed_df = pd.DataFrame(list(crossed_set), columns=['股票代號'])
crossed_df['股票網址'] = crossed_df['股票代號'].apply(lambda ticker: f"https://tw.tradingview.com/chart/ifVxylSI/?symbol=TWSE%3A{ticker.split('.')[0]}")
crossed_df.to_csv('篩選結果.csv', index=False)
print("篩選結果已保存到 '篩選結果.csv' 文件中。")

input('按下任何鍵離開')