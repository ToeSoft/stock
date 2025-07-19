import pandas

import pandas as pd
import numpy as np


def compute_rsi(df, N, column='close'):
    delta = df[column].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / N, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / N, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_indicators(df:pandas.DataFrame,symbol: str):


    # 计算 MA5（5 日移动平均线），用收盘价计算
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA30'] = df['close'].rolling(window=30).mean()
    df['MA60'] = df['close'].rolling(window=60).mean()

    df["VOL"] = df["volume"]
    # 成交量的 MA5 和 MA10
    df["VOL_MA5"] = df["volume"].rolling(window=5).mean()
    df["VOL_MA10"] = df["volume"].rolling(window=10).mean()

    # === RSI 参数 ===
    df['RSI6'] = compute_rsi(df, 6)
    df['RSI12'] = compute_rsi(df, 12)
    df['RSI24'] = compute_rsi(df, 24)

    # === KDJ 参数 ===
    n = 9  # RSV周期，KDJ 通常用 9 日
    low_min = df['low'].rolling(window=n).min()
    high_max = df['high'].rolling(window=n).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100

    df['K'] = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    df['D'] = df['K'].ewm(alpha=1 / 3, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']

    # === MACD 参数 ===
    short = 12  # EMA短周期
    long = 26  # EMA长周期
    signal = 9  # DEA周期

    # 计算 EMA
    df['EMA12'] = df['close'].ewm(span=short, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=long, adjust=False).mean()

    # 计算 DIF（快线）
    df['DIF'] = df['EMA12'] - df['EMA26']

    # 计算 DEA（慢线）
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()

    # 计算 MACD（柱状图）
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])

    # === WR10 ===
    n1 = 10
    high_n1 = df['high'].rolling(window=n1).max()
    low_n1 = df['low'].rolling(window=n1).min()
    df['WR10'] = (high_n1 - df['close']) / (high_n1 - low_n1) * 100

    # === WR6 ===
    n2 = 6
    high_n2 = df['high'].rolling(window=n2).max()
    low_n2 = df['low'].rolling(window=n2).min()
    df['WR6'] = (high_n2 - df['close']) / (high_n2 - low_n2) * 100

    # === DMI 指标 ===
    N = 14  # 常用周期
    M = 6  # ADX 平滑周期
    # 计算 TR（True Range）
    df['H-L'] = df['high'] - df['low']
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)

    # 计算 +DM 和 -DM
    df['+DM'] = df['high'] - df['high'].shift(1)
    df['-DM'] = df['low'].shift(1) - df['low']

    df['+DM'] = df['+DM'].where((df['+DM'] > df['-DM']) & (df['+DM'] > 0), 0)
    df['-DM'] = df['-DM'].where((df['-DM'] > df['+DM']) & (df['-DM'] > 0), 0)

    # 对 TR、+DM、-DM 进行 N 日平滑
    df['TR_sum'] = df['TR'].rolling(window=N).sum()
    df['+DM_sum'] = df['+DM'].rolling(window=N).sum()
    df['-DM_sum'] = df['-DM'].rolling(window=N).sum()

    df['PDI'] = 100 * (df['+DM_sum'] / df['TR_sum'])
    df['MDI'] = 100 * (df['-DM_sum'] / df['TR_sum'])

    # 计算 DX（动向指数）
    df['DX'] = 100 * (abs(df['PDI'] - df['MDI']) / (df['PDI'] + df['MDI']))

    # 用Wilder平滑法计算ADX
    df['ADX'] = df['DX'].rolling(window=M).mean()

    # 计算 ADXR（平滑平均趋向指数）
    df['ADXR'] = (df['ADX'] + df['ADX'].shift(M)) / 2

    # === BIAS ===
    df['MA6'] = df['close'].rolling(window=6).mean()
    df['MA12'] = df['close'].rolling(window=12).mean()
    df['MA24'] = df['close'].rolling(window=24).mean()

    df['BIAS6'] = (df['close'] - df['MA6']) / df['MA6'] * 100
    df['BIAS12'] = (df['close'] - df['MA12']) / df['MA12'] * 100
    df['BIAS24'] = (df['close'] - df['MA24']) / df['MA24'] * 100

    # === OBV ===
    # 确保日期排序
    df = df.sort_values("date").reset_index(drop=True)

    # 计算 OBV
    df["close_diff"] = df["close"].diff()
    df["direction"] = np.where(df["close_diff"] > 0, 1, np.where(df["close_diff"] < 0, -1, 0))
    df["obv_change"] = df["volume"] * df["direction"]
    df["OBV"] = df["obv_change"].fillna(0).cumsum()
    df['OBV_MA'] = df['OBV'].rolling(window=30).mean()
    # 将 OBV_MA 转为非科学计数法，并保留两位小数
    df['OBV_MA'] = df['OBV_MA'].apply(lambda x: f'{x:.2f}' if pd.notnull(x) else '')

    # === CCI ===
    N = 14  # 通常为 14 天

    # 1. 计算典型价格 TP
    df['TP'] = (df['high'] + df['low'] + df['close']) / 3

    # 2. 计算 TP 的 N 日简单移动平均
    df['TP_MA'] = df['TP'].rolling(window=N).mean()

    # 3. 计算 TP 的 N 日平均绝对偏差
    df['MD'] = df['TP'].rolling(window=N).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)

    # 4. 计算 CCI
    df['CCI'] = (df['TP'] - df['TP_MA']) / (0.015 * df['MD'])

    # === ROC ===
    N = 12  # ROC 默认周期常用值为 12

    # 1. 计算 ROC
    df['ROC'] = (df['close'] - df['close'].shift(N)) / df['close'].shift(N) * 100

    # 2. 计算 ROC 的均线（如 6 日简单移动平均）
    df['ROC_MA'] = df['ROC'].rolling(window=6).mean()

    # === CR ===
    N = 26

    # 1. 前一天的中间价 MID
    df['MID'] = (df['high'] + df['low']) / 2
    df['MID_yesterday'] = df['MID'].shift(1)

    # 2. 计算 CR 指标
    P1 = (df['high'] - df['MID_yesterday']).clip(lower=0)
    P2 = (df['MID_yesterday'] - df['low']).clip(lower=0)

    df['CR'] = P1.rolling(window=N).sum() / P2.rolling(window=N).sum() * 100

    # 3. 计算 CR 均线 MA1~MA3
    df['MA1'] = df['CR'].rolling(window=10).mean().shift(1 + int(10 / 2.5))
    df['MA2'] = df['CR'].rolling(window=20).mean().shift(1 + int(20 / 2.5))
    df['MA3'] = df['CR'].rolling(window=40).mean().shift(1 + int(40 / 2.5))

    return df.iloc[[-1]].assign(symbol=symbol)

def compute_hk_rsi(df, N, column='收盘'):
    delta = df[column].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / N, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / N, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi



def compute_hk_indicators(df:pandas.DataFrame,symbol: str):
    # 计算 MA5（5 日移动平均线），用收盘价计算
    df['MA5'] = df['收盘'].rolling(window=5).mean()
    df['MA10'] = df['收盘'].rolling(window=10).mean()
    df['MA20'] = df['收盘'].rolling(window=20).mean()
    df['MA30'] = df['收盘'].rolling(window=30).mean()
    df['MA60'] = df['收盘'].rolling(window=60).mean()

    df["VOL"] = df["成交量"]
    # 成交量的 MA5 和 MA10
    df["VOL_MA5"] = df["成交量"].rolling(window=5).mean()
    df["VOL_MA10"] = df["成交量"].rolling(window=10).mean()

    # === RSI 参数 ===
    df['RSI6'] = compute_hk_rsi(df, 6)
    df['RSI12'] = compute_hk_rsi(df, 12)
    df['RSI24'] = compute_hk_rsi(df, 24)

    # === KDJ 参数 ===
    n = 9  # RSV周期，KDJ 通常用 9 日
    low_min = df['最低'].rolling(window=n).min()
    high_max = df['最高'].rolling(window=n).max()
    rsv = (df['收盘'] - low_min) / (high_max - low_min) * 100

    df['K'] = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    df['D'] = df['K'].ewm(alpha=1 / 3, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']

    # === MACD 参数 ===
    short = 12  # EMA短周期
    long = 26  # EMA长周期
    signal = 9  # DEA周期

    # 计算 EMA
    df['EMA12'] = df['收盘'].ewm(span=short, adjust=False).mean()
    df['EMA26'] = df['收盘'].ewm(span=long, adjust=False).mean()

    # 计算 DIF（快线）
    df['DIF'] = df['EMA12'] - df['EMA26']

    # 计算 DEA（慢线）
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()

    # 计算 MACD（柱状图）
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])

    # === WR10 ===
    n1 = 10
    high_n1 = df['最高'].rolling(window=n1).max()
    low_n1 = df['最低'].rolling(window=n1).min()
    df['WR10'] = (high_n1 - df['收盘']) / (high_n1 - low_n1) * 100

    # === WR6 ===
    n2 = 6
    high_n2 = df['最高'].rolling(window=n2).max()
    low_n2 = df['最低'].rolling(window=n2).min()
    df['WR6'] = (high_n2 - df['收盘']) / (high_n2 - low_n2) * 100

    # === DMI 指标 ===
    N = 14  # 常用周期
    M = 6  # ADX 平滑周期
    # 计算 TR（True Range）
    df['H-L'] = df['最高'] - df['最低']
    df['H-PC'] = abs(df['最高'] - df['收盘'].shift(1))
    df['L-PC'] = abs(df['最低'] - df['收盘'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)

    # 计算 +DM 和 -DM
    df['+DM'] = df['最高'] - df['最高'].shift(1)
    df['-DM'] = df['最低'].shift(1) - df['最低']

    df['+DM'] = df['+DM'].where((df['+DM'] > df['-DM']) & (df['+DM'] > 0), 0)
    df['-DM'] = df['-DM'].where((df['-DM'] > df['+DM']) & (df['-DM'] > 0), 0)

    # 对 TR、+DM、-DM 进行 N 日平滑
    df['TR_sum'] = df['TR'].rolling(window=N).sum()
    df['+DM_sum'] = df['+DM'].rolling(window=N).sum()
    df['-DM_sum'] = df['-DM'].rolling(window=N).sum()

    df['PDI'] = 100 * (df['+DM_sum'] / df['TR_sum'])
    df['MDI'] = 100 * (df['-DM_sum'] / df['TR_sum'])

    # 计算 DX（动向指数）
    df['DX'] = 100 * (abs(df['PDI'] - df['MDI']) / (df['PDI'] + df['MDI']))

    # 用Wilder平滑法计算ADX
    df['ADX'] = df['DX'].rolling(window=M).mean()

    # 计算 ADXR（平滑平均趋向指数）
    df['ADXR'] = (df['ADX'] + df['ADX'].shift(M)) / 2

    #     # === BIAS ===
    df['MA6'] = df['收盘'].rolling(window=6).mean()
    df['MA12'] = df['收盘'].rolling(window=12).mean()
    df['MA24'] = df['收盘'].rolling(window=24).mean()

    df['BIAS6'] = (df['收盘'] - df['MA6']) / df['MA6'] * 100
    df['BIAS12'] = (df['收盘'] - df['MA12']) / df['MA12'] * 100
    df['BIAS24'] = (df['收盘'] - df['MA24']) / df['MA24'] * 100
    # === OBV ===
    # 确保日期排序
    df = df.sort_values("日期").reset_index(drop=True)

    # 计算 OBV
    df["close_diff"] = df["收盘"].diff()
    df["direction"] = np.where(df["close_diff"] > 0, 1, np.where(df["close_diff"] < 0, -1, 0))
    df["obv_change"] = df["成交量"] * df["direction"]
    df["OBV"] = df["obv_change"].fillna(0).cumsum()
    df['OBV_MA'] = df['OBV'].rolling(window=30).mean()
    # 将 OBV_MA 转为非科学计数法，并保留两位小数
    df['OBV_MA'] = df['OBV_MA'].apply(lambda x: f'{x:.2f}' if pd.notnull(x) else '')

    # === CCI ===
    N = 14  # 通常为 14 天

    # 1. 计算典型价格 TP
    df['TP'] = (df['最高'] + df['最低'] + df['收盘']) / 3

    # 2. 计算 TP 的 N 日简单移动平均
    df['TP_MA'] = df['TP'].rolling(window=N).mean()

    # 3. 计算 TP 的 N 日平均绝对偏差
    df['MD'] = df['TP'].rolling(window=N).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)

    # 4. 计算 CCI
    df['CCI'] = (df['TP'] - df['TP_MA']) / (0.015 * df['MD'])

    # === ROC ===
    N = 12  # ROC 默认周期常用值为 12

    # 1. 计算 ROC
    df['ROC'] = (df['收盘'] - df['收盘'].shift(N)) / df['收盘'].shift(N) * 100

    # 2. 计算 ROC 的均线（如 6 日简单移动平均）
    df['ROC_MA'] = df['ROC'].rolling(window=6).mean()

    # === CR ===
    N = 26

    # 1. 前一天的中间价 MID
    df['MID'] = (df['最高'] + df['最低']) / 2
    df['MID_yesterday'] = df['MID'].shift(1)

    # 2. 计算 CR 指标
    P1 = (df['最高'] - df['MID_yesterday']).clip(lower=0)
    P2 = (df['MID_yesterday'] - df['最低']).clip(lower=0)

    df['CR'] = P1.rolling(window=N).sum() / P2.rolling(window=N).sum() * 100

    # 3. 计算 CR 均线 MA1~MA3
    df['MA1'] = df['CR'].rolling(window=10).mean().shift(1 + int(10 / 2.5))
    df['MA2'] = df['CR'].rolling(window=20).mean().shift(1 + int(20 / 2.5))
    df['MA3'] = df['CR'].rolling(window=40).mean().shift(1 + int(40 / 2.5))

    # === BOLL ===
    # 设置参数
    N = 20  # 移动平均周期
    K = 2  # 标准差倍数

    # 计算布林带
    df['BOLL_MID'] = df['收盘'].rolling(N).mean()  # 中轨
    df['BOLL_STD'] = df['收盘'].rolling(N).std()  # 标准差
    df['BOLL_UPPER'] = df['BOLL_MID'] + K * df['BOLL_STD']  # 上轨
    df['BOLL_LOWER'] = df['BOLL_MID'] - K * df['BOLL_STD']  # 下轨

    return df.iloc[[-1]].assign(symbol=symbol)






def compute_us_rsi(df, N, column='close'):
    delta = df[column].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / N, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / N, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_us_indicators(df:pandas.DataFrame,symbol: str):
    # 计算 MA5（5 日移动平均线），用收盘价计算
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA30'] = df['close'].rolling(window=30).mean()
    df['MA60'] = df['close'].rolling(window=60).mean()

    df["VOL"] = df["volume"]
    # 成交量的 MA5 和 MA10
    df["VOL_MA5"] = df["volume"].rolling(window=5).mean()
    df["VOL_MA10"] = df["volume"].rolling(window=10).mean()

    # === RSI 参数 ===
    df['RSI6'] = compute_us_rsi(df, 6)
    df['RSI12'] = compute_us_rsi(df, 12)
    df['RSI24'] = compute_us_rsi(df, 24)

    # === KDJ 参数 ===
    n = 9  # RSV周期，KDJ 通常用 9 日
    low_min = df['low'].rolling(window=n).min()
    high_max = df['high'].rolling(window=n).max()
    rsv = (df['close'] - low_min) / (high_max - low_min) * 100

    df['K'] = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    df['D'] = df['K'].ewm(alpha=1 / 3, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']

    # === MACD 参数 ===
    short = 12  # EMA短周期
    long = 26  # EMA长周期
    signal = 9  # DEA周期

    # 计算 EMA
    df['EMA12'] = df['close'].ewm(span=short, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=long, adjust=False).mean()

    # 计算 DIF（快线）
    df['DIF'] = df['EMA12'] - df['EMA26']

    # 计算 DEA（慢线）
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()

    # 计算 MACD（柱状图）
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])

    # === WR10 ===
    n1 = 10
    high_n1 = df['high'].rolling(window=n1).max()
    low_n1 = df['low'].rolling(window=n1).min()
    df['WR10'] = (high_n1 - df['close']) / (high_n1 - low_n1) * 100

    # === WR6 ===
    n2 = 6
    high_n2 = df['high'].rolling(window=n2).max()
    low_n2 = df['low'].rolling(window=n2).min()
    df['WR6'] = (high_n2 - df['close']) / (high_n2 - low_n2) * 100

    # === DMI 指标 ===
    N = 14  # 常用周期
    M = 6  # ADX 平滑周期
    # 计算 TR（True Range）
    df['H-L'] = df['high'] - df['low']
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)

    # 计算 +DM 和 -DM
    df['+DM'] = df['high'] - df['high'].shift(1)
    df['-DM'] = df['low'].shift(1) - df['low']

    df['+DM'] = df['+DM'].where((df['+DM'] > df['-DM']) & (df['+DM'] > 0), 0)
    df['-DM'] = df['-DM'].where((df['-DM'] > df['+DM']) & (df['-DM'] > 0), 0)

    # 对 TR、+DM、-DM 进行 N 日平滑
    df['TR_sum'] = df['TR'].rolling(window=N).sum()
    df['+DM_sum'] = df['+DM'].rolling(window=N).sum()
    df['-DM_sum'] = df['-DM'].rolling(window=N).sum()

    df['PDI'] = 100 * (df['+DM_sum'] / df['TR_sum'])
    df['MDI'] = 100 * (df['-DM_sum'] / df['TR_sum'])

    # 计算 DX（动向指数）
    df['DX'] = 100 * (abs(df['PDI'] - df['MDI']) / (df['PDI'] + df['MDI']))

    # 用Wilder平滑法计算ADX
    df['ADX'] = df['DX'].rolling(window=M).mean()

    # 计算 ADXR（平滑平均趋向指数）
    df['ADXR'] = (df['ADX'] + df['ADX'].shift(M)) / 2

    #     # === BIAS ===
    df['MA6'] = df['close'].rolling(window=6).mean()
    df['MA12'] = df['close'].rolling(window=12).mean()
    df['MA24'] = df['close'].rolling(window=24).mean()

    df['BIAS6'] = (df['close'] - df['MA6']) / df['MA6'] * 100
    df['BIAS12'] = (df['close'] - df['MA12']) / df['MA12'] * 100
    df['BIAS24'] = (df['close'] - df['MA24']) / df['MA24'] * 100
    # === OBV ===
    # 确保日期排序
    df = df.sort_values("date").reset_index(drop=True)

    # 计算 OBV
    df["close_diff"] = df["close"].diff()
    df["direction"] = np.where(df["close_diff"] > 0, 1, np.where(df["close_diff"] < 0, -1, 0))
    df["obv_change"] = df["volume"] * df["direction"]
    df["OBV"] = df["obv_change"].fillna(0).cumsum()
    df['OBV_MA'] = df['OBV'].rolling(window=30).mean()
    # 将 OBV_MA 转为非科学计数法，并保留两位小数
    df['OBV_MA'] = df['OBV_MA'].apply(lambda x: f'{x:.2f}' if pd.notnull(x) else '')

    # === CCI ===
    N = 14  # 通常为 14 天

    # 1. 计算典型价格 TP
    df['TP'] = (df['high'] + df['low'] + df['close']) / 3

    # 2. 计算 TP 的 N 日简单移动平均
    df['TP_MA'] = df['TP'].rolling(window=N).mean()

    # 3. 计算 TP 的 N 日平均绝对偏差
    df['MD'] = df['TP'].rolling(window=N).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)

    # 4. 计算 CCI
    df['CCI'] = (df['TP'] - df['TP_MA']) / (0.015 * df['MD'])

    # === ROC ===
    N = 12  # ROC 默认周期常用值为 12

    # 1. 计算 ROC
    df['ROC'] = (df['close'] - df['close'].shift(N)) / df['close'].shift(N) * 100

    # 2. 计算 ROC 的均线（如 6 日简单移动平均）
    df['ROC_MA'] = df['ROC'].rolling(window=6).mean()

    # === CR ===
    N = 26

    # 1. 前一天的中间价 MID
    df['MID'] = (df['high'] + df['low']) / 2
    df['MID_yesterday'] = df['MID'].shift(1)

    # 2. 计算 CR 指标
    P1 = (df['high'] - df['MID_yesterday']).clip(lower=0)
    P2 = (df['MID_yesterday'] - df['low']).clip(lower=0)

    df['CR'] = P1.rolling(window=N).sum() / P2.rolling(window=N).sum() * 100

    # 3. 计算 CR 均线 MA1~MA3
    df['MA1'] = df['CR'].rolling(window=10).mean().shift(1 + int(10 / 2.5))
    df['MA2'] = df['CR'].rolling(window=20).mean().shift(1 + int(20 / 2.5))
    df['MA3'] = df['CR'].rolling(window=40).mean().shift(1 + int(40 / 2.5))

    # === BOLL ===
    # 设置参数
    N = 20  # 移动平均周期
    K = 2  # 标准差倍数

    # 计算布林带
    df['BOLL_MID'] = df['close'].rolling(N).mean()  # 中轨
    df['BOLL_STD'] = df['close'].rolling(N).std()  # 标准差
    df['BOLL_UPPER'] = df['BOLL_MID'] + K * df['BOLL_STD']  # 上轨
    df['BOLL_LOWER'] = df['BOLL_MID'] - K * df['BOLL_STD']  # 下轨

    return df.iloc[[-1]].assign(symbol=symbol)