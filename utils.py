import json
import os
import threading
import time
from datetime import datetime
from time import sleep

import pandas as pd
from pybroker.ext.data import AKShare
import akshare as ak

from compute_utils import compute_indicators, compute_hk_indicators
from excel import generateExcel, generateTxt
import concurrent.futures


def startWithThread(items, onFinish, onError, output_format, crawlThreadCount):
    # 记录开始时间
    start_time = time.time()

    os.makedirs("temp", exist_ok=True)

    # 记录创建temp目录的时间
    step1 = time.time()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=crawlThreadCount) as executor:
            futures = []
            for item in items:
                stockCode = item.split(":")[0]
                # 将浏览器对象传递给线程任务
                futures.append(executor.submit(getData, stockCode, onError, 0))
            concurrent.futures.wait(futures)
    finally:
        # 记录线程任务完成的时间
        step2 = time.time()

    updateStockList()
    step3 = time.time()

    with open("stock_list.json", "r", encoding="utf-8") as f:
        stockList = json.load(f)
        for i in stockList:
            if ":" not in i:
                continue
            if output_format == "excel":
                generateExcel(i.split(":")[1], i.split(":")[0], onError)
            else:
                generateTxt(i.split(":")[1], i.split(":")[0], onError)
    step4 = time.time()

    # 计算每一步的耗时
    print(f"创建temp目录耗时: {step1 - start_time:.2f} 秒")
    print(f"线程任务完成耗时: {step2 - step1:.2f} 秒")
    print(f"保存stock_list.json耗时: {step3 - step2:.2f} 秒")
    print(f"生成{output_format}耗时: {step4 - step3:.2f} 秒")
    # 完整执行时间
    print(f"总执行时间: {step4 - start_time:.2f} 秒")

    onFinish()


def startGetData(items, onFinish, onError, output_format, crawlThreadCount):
    threading.Thread(target=startWithThread,
                     args=(items, onFinish, onError, output_format, crawlThreadCount)).start()


def getData(stockCode, onError, retryTime):
    try:
        if (stockCode.startswith("sh") or stockCode.startswith("sz") or stockCode.startswith(
                "SZ")) or stockCode.startswith("SH") or stockCode.startswith("bj") or stockCode.startswith("BJ"):
            # 切割前两位
            symbol = stockCode[2:]

            # 获取股票数据
            stock_individual_info_em_df = ak.stock_individual_info_em(symbol=symbol)
            info_dict = {row['item']: row['value'] for _, row in stock_individual_info_em_df.iterrows()}

            today = datetime.today().strftime('%Y%m%d')
            stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="18000101",
                                                    end_date=today,
                                                    adjust="")
            stock_zh_a_hist_df_load = json.loads(
                stock_zh_a_hist_df.to_json(orient='records', date_format='iso', force_ascii=False))

            last_record = stock_zh_a_hist_df_load[-1]
            previous_close = stock_zh_a_hist_df_load[-2]["收盘"]
            last_record["昨收"] = previous_close

            # 获取数据
            today = datetime.today().strftime('%m/%d/%Y')

            akshare = AKShare()
            df = akshare.query(
                symbols=[symbol],
                start_date='3/1/1800',
                end_date=today,
                adjust="qfq",  # 也可以写成 "qfq" 或 "hfq"
                timeframe="1d",
            )
            df = compute_indicators(df, symbol=symbol)

            df_sub = df[[
                'MA5', 'MA10', 'MA20', 'MA30', 'MA60',
                'VOL', 'VOL_MA5', 'VOL_MA10',
                'RSI6', 'RSI12', 'RSI24',
                'K', 'D', 'J',
                'DIF', 'DEA', 'MACD',
                'WR10', 'WR6',
                'PDI', 'MDI', 'ADX', 'ADXR',
                'BIAS6', 'BIAS12', 'BIAS24',
                'OBV', 'OBV_MA',
                'CCI',
                'ROC', 'ROC_MA',
                'CR', 'MA1', 'MA2', 'MA3'
            ]]

            # 转成 JSON 字符串（列表形式，每一行是一个 dict）
            json_str = df_sub.to_json(orient='records', date_format='iso')
            records = json.loads(json_str)
            result = {
                "股票信息": info_dict,
                "今日概览": last_record,
                "数据指标": records[0]
            }
            json_str = json.dumps(result, ensure_ascii=False, indent=2)

            # 保存数据到文件
            temp_dir = os.path.join("temp")
            with open(os.path.join(temp_dir, stockCode + ".json"), "w", encoding="utf-8") as f:
                f.write(json_str)


        elif stockCode.startswith("HK") or stockCode.startswith("hk"):
            # 获取数据
            symbol = stockCode[2:]
            stock_hk_security_profile_em_df = ak.stock_hk_security_profile_em(symbol=symbol)

            # 假设你的 DataFrame 是 df
            json_str = stock_hk_security_profile_em_df.to_json(orient='records', force_ascii=False,
                                                               date_format='iso')  # 转成 JSON 字符串
            info_dict = json.loads(json_str)[0]  # 转成 Python 对象（list of dict）

            df = ak.stock_hk_hist(symbol=symbol,
                                  period="daily",
                                  start_date="19700101",
                                  end_date="22220101",
                                  adjust="qfq")
            df = compute_hk_indicators(df, symbol=symbol)
            df_sub = df[[
                'MA5', 'MA10', 'MA20', 'MA30', 'MA60',
                'VOL', 'VOL_MA5', 'VOL_MA10',
                'RSI6', 'RSI12', 'RSI24',
                'K', 'D', 'J',
                'DIF', 'DEA', 'MACD',
                'WR10', 'WR6',
                'PDI', 'MDI', 'ADX', 'ADXR',
                'BIAS6', 'BIAS12', 'BIAS24',
                'OBV', 'OBV_MA',
                'CCI',
                'ROC', 'ROC_MA',
                'CR', 'MA1', 'MA2', 'MA3',
                'BOLL_MID', 'BOLL_STD', 'BOLL_UPPER', 'BOLL_LOWER'
            ]]
            # 转成 JSON 字符串（列表形式，每一行是一个 dict）
            json_str = df_sub.to_json(orient='records', date_format='iso')
            records = json.loads(json_str)
            result = {
                "股票信息": info_dict,
                "数据指标": records[0]
            }
            json_str = json.dumps(result, ensure_ascii=False, indent=2)

            # 保存数据到文件
            temp_dir = os.path.join("temp")
            with open(os.path.join(temp_dir, stockCode + ".json"), "w", encoding="utf-8") as f:
                f.write(json_str)
        else:
            raise ValueError(f"不支持的股票代码格式: {stockCode}")


    except Exception as e:
        if retryTime < 10:
            print(f"{stockCode}:重试中 ({retryTime + 1}/10)")
            time.sleep(5)
            getData(stockCode, onError, retryTime + 1)
            return
        else:
            with open("error.log", "a", encoding="utf-8") as f:
                f.write(f"{stockCode} 错误：{str(e)}\n")
            onError(f"{stockCode} 获取数据失败")


def updateStockList():
    try:
        # 读取文件
        with open("stock_list.json", "r", encoding="utf-8") as f:
            stockList = json.load(f)

        # 处理数据
        tempStockList = []
        tempStockDir = os.path.join("temp")
        dirlist = os.listdir(tempStockDir)

        for stockCode in stockList:
            tempStockCode = stockCode + ".json"
            if tempStockCode in dirlist:
                #     打开data.json 获取 股票名称
                with open((os.path.join(tempStockDir, tempStockCode, )), "r", encoding="utf-8") as f:
                    dataJson = json.load(f)
                    stock_info = dataJson.get("股票信息", {})

                    # 优先取“证券简称”，如果没有就取“股票简称”，都没有就设为 None 或 ""
                    stockName = stock_info.get("证券简称") or stock_info.get("股票简称") or ""

                    tempStockList.append(stockCode + ":" + stockName)
            else:
                tempStockList.append(stockCode)

        # 写回文件
        with open("stock_list.json", "w", encoding="utf-8") as f:
            json.dump(tempStockList, f, ensure_ascii=False, indent=4)
    except Exception as e:
        with open("error.log", "a", encoding="utf-8") as f:
            f.write(str(e) + "\n")
