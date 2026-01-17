import streamlit as st
import pandas as pd
from datetime import datetime
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- ⚙️ 配置区 ---
# 为了安全，我们通常把敏感信息放在 Streamlit 的 Secrets 里，这里为了演示方便，
# 依然采用 CSV 逻辑，但强烈建议你如果用 Google Sheets，参考下文的“秘钥配置”。
# 这里我提供一个“兼容版”，如果你不想配数据库，它默认还是存内存（重启会丢）。
# 🌟 强烈建议：为了数据不丢，请看教程第三阶段配置 Secrets！

# 页面配置
st.set_page_config(page_title="上岸养成计划", page_icon="🎓", layout="centered")

# --- 🛠️ 核心功能函数 ---
# 我们使用 st.cache_resource 保持连接，避免重复请求
@st.cache_resource
def get_connection():
    # 这里需要读取 Streamlit Secrets 里的配置
    # 具体怎么配，看教程第三阶段
    if "gcp_service_account" in st.secrets:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        # 打开表格：你需要把表格名称填在 secrets 或者这里
        sheet = client.open("LoveBank").sheet1 
        return sheet
    else:
        return None

def load_data():
    sheet = get_connection()
    if sheet:
        # 从 Google Sheet 读取所有记录
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    else:
        # 如果没配置云端，降级使用本地 CSV (仅供测试，重启会丢)
        if not os.path.exists("local_backup.csv"):
            return pd.DataFrame(columns=["时间", "类型", "项目", "积分变动", "备注"])
        return pd.read_csv("local_backup.csv")

def save_record(record_type, item, points, note=""):
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet = get_connection()
    
    if sheet:
        # 写入 Google Sheet (追加一行)
        sheet.append_row([time_str, record_type, item, points, note])
    else:
        # 降级本地保存
        df = load_data()
        new_row = {"时间": time_str, "类型": record_type, "项目": item, "积分变动": points, "备注": note}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv("local_backup.csv", index=False)

# --- 变量配置 ---
USER_NAME = "未来的陈老师"
TASKS = {"🧘‍♀️ 专注学习 45 分钟": 15, "📝 完成一套教综真题": 50, "🧠 背诵 10 个简答题": 20, "☀️ 早上 8:00 前打卡": 10}
REWARDS = [("🥤 半糖奶茶", 60), ("🍗 疯狂星期四", 120), ("💆 专属按摩", 200), ("❓ 惊喜盲盒", 100)]

# --- UI 逻辑 (和之前类似，精简版) ---
st.title(f"📚 {USER_NAME} 的备考金库")

# 获取数据
df = load_data()
# 计算总分 (防错处理)
if not df.empty and "积分变动" in df.columns:
    total_score = df["积分变动"].sum()
else:
    total_score = 0

st.metric(label="当前积分", value=total_score, delta="加油！")

tab1, tab2, tab3 = st.tabs(["赚积分", "花积分", "查账单"])

with tab1:
    for task, p in TASKS.items():
        if st.button(f"{task} (+{p})"):
            save_record("收入", task, p)
            st.toast(f"积分 +{p} 已入账！")
            st.rerun()

with tab2:
    for item, cost in REWARDS:
        col1, col2 = st.columns([3,1])
        col1.write(f"{item} ({cost}分)")
        if col2.button("兑换", key=item):
            if total_score >= cost:
                if "盲盒" in item:
                    gift = random.choice(["免做家务", "亲一口", "再接再厉"])
                    save_record("支出", f"盲盒：{gift}", -cost)
                    st.success(f"盲盒结果：{gift}")
                else:
                    save_record("支出", item, -cost)
                    st.success("兑换成功！")
                st.rerun()
            else:
                st.error("积分不足")

with tab3:
    st.dataframe(df)