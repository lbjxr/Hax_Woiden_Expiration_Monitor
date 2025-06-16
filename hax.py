#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import sys
import time
import datetime

def get_data_center_stats():
    """
    访问 Hax.co.id 并获取数据，返回一个包含结果字符串的列表。
    """
    url = "https://hax.co.id/data-center/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # 这个列表将用于存储我们要写入文件的每一行内容
    output_lines = []

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # 添加时间戳，这样就知道文件是什么时候更新的
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output_lines.append(f"--- HAX.CO.ID 数据中心状态 (更新于: {timestamp}) ---\n")

        data_center_cards = soup.find_all('div', class_='card h-100 bg-dark text-white')

        if not data_center_cards:
            output_lines.append("错误：在页面上没有找到数据中心信息卡片。\n")
            return output_lines

        found_data = False
        for card in data_center_cards:
            name_tag = card.find('h5', class_='card-title')
            count_tag = card.find('h1', class_='card-text')
            if name_tag and count_tag:
                name = name_tag.get_text(strip=True)
                count = count_tag.get_text(strip=True)
                if "在线VPS数量" not in name and "Online VPS" not in name:
                    # 将格式化的结果添加到列表中，并手动添加换行符 \n
                    output_lines.append(f"✅ 数据中心: {name},  VPS 数量: {count}\n")
                    found_data = True
        
        if not found_data:
             output_lines.append("未能解析出任何独立的数据中心信息。\n")

        return output_lines

    except requests.exceptions.RequestException as e:
        return [f"网络请求错误: {e}\n"]
    except Exception as e:
        return [f"发生未知错误: {e}\n"]

if __name__ == "__main__":
    try:
        while True:
            # 1. 打印提示信息到控制台，表示脚本正在工作
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在获取最新数据...")
            
            # 2. 调用函数获取数据
            results = get_data_center_stats()
            
            # 3. 将结果写入文件
            #    使用 'w' 模式会覆盖整个文件，'utf-8' 编码以支持中文
            with open("HaxDataCenter.txt", "w", encoding="utf-8") as f:
                f.writelines(results)
            
            print("数据已成功写入 HaxDataCenter.txt，将在60秒后重新获取。")
            
            # 4. 等待60秒
            time.sleep(60)

    except KeyboardInterrupt:
        # 允许用户通过按 Ctrl+C 来优雅地停止脚本
        print("\n脚本已停止。")
        sys.exit(0)
