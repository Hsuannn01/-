import os
import numpy as np
import datetime
import pandas as pd
import streamlit as st 
import streamlit.components.v1 as stc 
import indicator_forKBar_short

###### (1) 開始設定 ######
html_temp = """
		<div style="background-color:#3872fb;padding:10px;border-radius:10px">
		<h1 style="color:white;text-align:center;">金融資料視覺化呈現 (金融看板) </h1>
		<h2 style="color:white;text-align:center;">Financial Dashboard </h2>
		</div>
		"""
stc.html(html_temp)

## 读取Pickle文件
@st.cache(ttl=3600, show_spinner="正在加載資料...")
def load_data(url):
    df = pd.read_pickle(url)
    return df 

df_original = load_data('kbars_2330_2022-01-01-2022-11-18.pkl')

df_original = df_original.drop('Unnamed: 0', axis=1)

##### 選擇資料區間
st.subheader("選擇開始與結束的日期, 區間:2022-01-03 至 2022-11-18")
start_date = st.text_input('選擇開始日期 (日期格式: 2022-01-03)', '2022-01-03')
end_date = st.text_input('選擇結束日期 (日期格式: 2022-11-18)', '2022-11-18')
start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')

# 使用条件筛选选择时间区间的数据
df = df_original[(df_original['time'] >= start_date) & (df_original['time'] <= end_date)]

###### (2) 轉化為字典 ######
KBar_dic = df.to_dict()
KBar_dic['open'] = np.array(list(KBar_dic['open'].values()))
KBar_dic['product'] = np.repeat('tsmc', KBar_dic['open'].size)
KBar_dic['time'] = np.array([i.to_pydatetime() for i in list(KBar_dic['time'].values())])
KBar_dic['low'] = np.array(list(KBar_dic['low'].values()))
KBar_dic['high'] = np.array(list(KBar_dic['high'].values()))
KBar_dic['close'] = np.array(list(KBar_dic['close'].values()))
KBar_dic['volume'] = np.array(list(KBar_dic['volume'].values()))
KBar_dic['amount'] = np.array(list(KBar_dic['amount'].values()))

######  (3) 改變 KBar 時間長度 (以下)  ########
Date = start_date.strftime("%Y-%m-%d")
st.subheader("設定一根 K 棒的時間長度(單位: 日, 週, 月)")
cycle_duration = st.selectbox("設定一根 K 棒的時間長度", ['日', '周', '月'])

# 根據選擇的周期設定 KBar 週期
if cycle_duration == '日':
    cycle_duration = 1440  # 1 日
elif cycle_duration == '周':
    cycle_duration = 1440 * 5  # 1 週
elif cycle_duration == '月':
    cycle_duration = 1440 * 21  # 1 月

KBar = indicator_forKBar_short.KBar(Date, cycle_duration)

for i in range(KBar_dic['time'].size):
    time = KBar_dic['time'][i]
    open_price = KBar_dic['open'][i]
    close_price = KBar_dic['close'][i]
    low_price = KBar_dic['low'][i]
    high_price = KBar_dic['high'][i]
    qty = KBar_dic['volume'][i]
    amount = KBar_dic['amount'][i]
    tag = KBar.AddPrice(time, open_price, close_price, low_price, high_price, qty)

###### 形成 KBar 字典 (新週期的)
KBar_dic = {}
KBar_dic['time'] = KBar.TAKBar['time']   
KBar_dic['product'] = np.repeat('tsmc', KBar_dic['time'].size)
KBar_dic['open'] = KBar.TAKBar['open']
KBar_dic['high'] = KBar.TAKBar['high']
KBar_dic['low'] = KBar.TAKBar['low']
KBar_dic['close'] = KBar.TAKBar['close']
KBar_dic['volume'] = KBar.TAKBar['volume']

###### (4) 計算各種技術指標 ######
KBar_df = pd.DataFrame(KBar_dic)

#####  (i) 移動平均線策略   #####
st.subheader("設定計算長移動平均線(MA)的 K 棒數目(整數, 例如 10)")
LongMAPeriod = st.slider('選擇一個整數', 0, 100, 10)
st.subheader("設定計算短移動平均線(MA)的 K 棒數目(整數, 例如 2)")
ShortMAPeriod = st.slider('選擇一個整數', 0, 100, 2)

KBar_df['MA_long'] = KBar_df['close'].rolling(window=LongMAPeriod).mean()
KBar_df['MA_short'] = KBar_df['close'].rolling(window=ShortMAPeriod).mean()

last_nan_index_MA = KBar_df['MA_long'][::-1].index[KBar_df['MA_long'][::-1].apply(pd.isna)][0]

#####  (ii) RSI 策略   #####
st.subheader("設定計算長RSI的 K 棒數目(整數, 例如 10)")
LongRSIPeriod = st.slider('選擇一個整數', 0, 1000, 10)
st.subheader("設定計算短RSI的 K 棒數目(整數, 例如 2)")
ShortRSIPeriod = st.slider('選擇一個整數', 0, 1000, 2)

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

KBar_df['RSI_long'] = calculate_rsi(KBar_df, LongRSIPeriod)
KBar_df['RSI_short'] = calculate_rsi(KBar_df, ShortRSIPeriod)
KBar_df['RSI_Middle'] = np.array([50] * len(KBar_dic['time']))

last_nan_index_RSI = KBar_df['RSI_long'][::-1].index[KBar_df['RSI_long'][::-1].apply(pd.isna)][0]

###### (5) 將 Dataframe 欄位名稱轉換  ###### 
KBar_df.columns = [i[0].upper() + i[1:] for i in KBar_df.columns]

###### (6) 畫圖 ######
st.subheader("畫圖")
import plotly.graph_objects as go
from plotly.subplots import make_subplots

##### K線圖, 移動平均線 MA
with st.expander("K線圖, 移動平均線"):
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Candlestick(x=KBar_df['Time'],
                    open=KBar_df['Open'], high=KBar_df['High'],
                    low=KBar_df['Low'], close=KBar_df['Close'], name='K線'),
                   secondary_y=True)
    fig1.add_trace(go.Bar(x=KBar_df['Time'], y=KBar_df['Volume'], name='成交量', marker=dict(color='black')), secondary_y=False)
    fig1.add_trace(go.Scatter(x=KBar_df['Time'][last_nan_index_MA+1:], y=KBar_df['MA_long'][last_nan_index_MA+1:], mode='lines', line=dict(color='orange', width=2), name=f'{LongMAPeriod}-根 K棒 移動平均線'), secondary_y=True)
    fig1.add_trace(go.Scatter(x=KBar_df['Time'][last_nan_index_MA+1:], y=KBar_df['MA_short'][last_nan_index_MA+1:], mode='lines', line=dict(color='pink', width=2), name=f'{ShortMAPeriod}-根 K棒 移動平均線'), secondary_y=True)
    fig1.layout.yaxis2.showgrid=True
    st.plotly_chart(fig1, use_container_width=True)

##### K線圖, RSI
with st.expander("K線圖, 長短 RSI"):
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Candlestick(x=KBar_df['Time'],
                    open=KBar_df['Open'], high=KBar_df['High'],
                    low=KBar_df['Low'], close=KBar_df['Close'], name='K線'),
                   secondary_y=True)
    fig2.add_trace(go.Scatter(x=KBar_df['Time'][last_nan_index_RSI+1:], y=KBar_df['RSI_long'][last_nan_index_RSI+1:], mode='lines', line=dict(color='blue', width=2), name=f'{LongRSIPeriod}-根 K棒 RSI 長線'), secondary_y=True)
    fig2.add_trace(go.Scatter(x=KBar_df['Time'][last_nan_index_RSI+1:], y=KBar_df['RSI_short'][last_nan_index_RSI+1:], mode='lines', line=dict(color='red', width=2), name=f'{ShortRSIPeriod}-根 K棒 RSI 短線'), secondary_y=True)
    fig2.add_trace(go.Scatter(x=KBar_df['Time'], y=KBar_df['RSI_Middle'], mode='lines', line=dict(color='grey', width=1, dash='dot'), name='RSI 中線'), secondary_y=True)
    fig2.layout.yaxis2.showgrid=True
    st.plotly_chart(fig2, use_container_width=True)
