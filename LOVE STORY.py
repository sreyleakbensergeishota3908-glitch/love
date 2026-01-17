import streamlit as st
import pandas as pd
from datetime import datetime
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests
import os  # 👈 补上了这个库，不然 load_data 会报错

# --- 📢 微信推送配置 ---
WX_APP_TOKEN = "AT_psrPX3EAbGqwNeSfFWpqXDfNrJclO5wv" 

# 2. 填入 UID (注意格式，后面加了右中括号)
TARGET_UIDS = [
    "UID_I6L6ANL0Il86r4JDYIOaezEEEcdR", 
    "UID_hVfLqv8hvIjtfcKUsM5ViXhDR3xN"
] # 👈 之前这里漏了 ]

# --- 📨 发送微信消息的函数 (之前漏了这段) ---
def send_wechat_msg(content):
    url = "https://wxpusher.zjiecode.com/api/send/message"
    body = {
        "appToken": WX_APP_TOKEN,
        "content": content,
        "contentType": 1, 
        "uids": TARGET_UIDS
    }
    try:
        # 默默发送，不阻塞主程序
        requests.post(url, json=body)
    except Exception as e:
        print(f"推送失败: {e}")

# --- ⚙️ 页面配置 ---
st.set_page_config(page_title="上岸养成计划", page_icon="🎓", layout="centered")

# --- 🛠️ 核心功能函数 ---
@st.cache_resource
def get_connection():
    # 检查是否配置了 Secrets
    if "gcp_service_account" in st.secrets:
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # 手动修复私钥格式
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open("LoveBank").sheet1 
            return sheet
        except Exception as e:
            st.error(f"连接数据库失败: {e}")
            return None
    else:
        st.warning("未检测到 Secrets 配置")
        return None

def load_data():
    sheet = get_connection()
    if sheet:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    else:
        if not os.path.exists("local_backup.csv"):
            return pd.DataFrame(columns=["时间", "类型", "项目", "积分变动", "备注"])
        return pd.read_csv("local_backup.csv")

def save_record(record_type, item, points, note=""):
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet = get_connection()
    
    if sheet:
        sheet.append_row([time_str, record_type, item, points, note])
    else:
        df = load_data()
        new_row = {"时间": time_str, "类型": record_type, "项目": item, "积分变动": points, "备注": note}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv("local_backup.csv", index=False)

# --- 变量配置 ---
USER_NAME = "未来的李总裁"
TASKS = {"🧘‍♀️ 专注学习 45 分钟": 15, "📝 完成一套教综真题": 50, "🧠 背诵 10 个简答题": 20, "☀️ 早上 8:00 前打卡": 10}
REWARDS = [("🥤 半糖奶茶", 60), ("🍗 疯狂星期四", 120), ("💆 专属按摩", 200), ("❓ 惊喜盲盒", 100)]

# --- UI 逻辑 ---
st.title(f"📚 {USER_NAME} 的备考金库")

# 获取数据
df = load_data()
if not df.empty and "积分变动" in df.columns:
    total_score = df["积分变动"].sum()
else:
    total_score = 0

st.metric(label="当前积分", value=total_score, delta="加油！")

tab1, tab2, tab3 = st.tabs(["赚积分", "花积分", "查账单"])

# --- Tab 1: 赚积分 (已集成微信推送) ---
with tab1:
    for task, p in TASKS.items():
        if st.button(f"{task} (+{p})"):
            # 1. 存数据
            save_record("收入", task, p)
            
            # 2. 发微信通知 (这里调用了函数！)
            msg = f"🎉 宝贝太棒了！完成了【{task}】，积分 +{p}！\n💰 当前总分：{total_score + p}"
            send_wechat_msg(msg)
            
            # 3. 界面反馈
            st.toast(f"积分 +{p} 已入账！", icon="🎉")
            st.balloons()
            st.rerun()

# --- Tab 2: 花积分 (也集成微信推送) ---
with tab2:
    for item, cost in REWARDS:
        col1, col2 = st.columns([3,1])
        col1.write(f"{item} ({cost}分)")
        if col2.button("兑换", key=item):
            if total_score >= cost:
                if "盲盒" in item:
                    gift = random.choice(["免做家务", "亲一口", "再接再厉"])
                    real_item = f"盲盒：{gift}"
                    save_record("支出", real_item, -cost)
                    
                    # 发送盲盒通知
                    send_wechat_msg(f"🎁 刺激！她抽中了盲盒：{gift}！(-{cost}分)")
                    
                    st.success(f"盲盒结果：{gift}")
                else:
                    save_record("支出", item, -cost)
                    
                    # 发送兑换通知
                    send_wechat_msg(f"💸 消费提醒：她兑换了【{item}】！(-{cost}分)\n快去准备礼物吧！")
                    
                    st.success("兑换成功！")
                st.rerun()
            else:
                st.error("积分不足")

with tab3:
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    
