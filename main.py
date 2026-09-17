import os
import time
import threading
import requests
import feedparser
import schedule
import google.generativeai as genai
from flask import Flask

# ================= 1. CẤU HÌNH WEB SERVER (CHO RENDER) =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Telegram đang hoạt động 24/7!"

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Chạy Flask ở luồng riêng để đáp ứng cổng HTTP của Render
threading.Thread(target=run_flask, daemon=True).start()

# ================= 2. THÔNG TIN CẤU HÌNH API =================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8605115616:AAHleFY6deA8apHaqyXJ_9yDDfdfZSNmjzg")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5637028995")

# Khởi tạo Gemini AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("⚠️ Cảnh báo: Chưa cài đặt GEMINI_API_KEY trong Environment Variables!")

# Danh sách RSS Feed từ các trang báo
RSS_SOURCES = [
    "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "https://thanhnien.vn/rss/home.rss",
    "https://tuoitre.vn/rss/tin-moi-nhat.rss"
]

# ================= 3. HÀM GỬI TIN NHẮN TELEGRAM =================
def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Chia nhỏ tin nhắn nếu dài hơn 4000 ký tự (giới hạn Telegram)
    max_length = 4000
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown"
        }
        try:
            res = requests.post(url, json=payload)
            if res.status_code != 200:
                # Nếu gửi Markdown lỗi thì gửi lại dạng thường
                payload.pop("parse_mode", None)
                requests.post(url, json=payload)
        except Exception as e:
            print(f"Lỗi gửi Telegram: {e}")

# ================= 4. LUỒNG XỬ LÝ LẤY TIN & TÓM TẮT =================
def job():
    print("🤖 Đang thu thập tin tức...")
    articles = []
    
    for rss_url in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:3]:  # Lấy 3 tin mới nhất từ mỗi trang
                articles.append(f"- Tiêu đề: {entry.title}\n  Liên kết: {entry.link}")
        except Exception as e:
            print(f"Lỗi đọc RSS {rss_url}: {e}")

    if not articles:
        print("Không tìm thấy tin tức mới.")
        return

    news_text = "\n".join(articles)
    prompt = (
        "Bạn là một biên tập viên tin tức chuyên nghiệp. Hãy tóm tắt các tin tức dưới đây "
        "thành một bản tin ngắn gọn, súc tích, trình bày đẹp mắt bằng điểm tin (bullet points) "
        "và thêm biểu tượng cảm xúc (emoji) phù hợp để gửi qua Telegram:\n\n"
        f"{news_text}"
    )

    try:
        response = model.generate_content(prompt)
        summary = response.text
        send_telegram_message(f"📰 **BẢN TIN TỔNG HỢP MỚI NHẤT** 📰\n\n{summary}")
        print("✅ Đã gửi bản tin thành công về Telegram!")
    except Exception as e:
        print(f"Lỗi khi gọi Gemini AI: {e}")

# ================= 5. LẬP LỊCH CHẠY TỰ ĐỘNG =================
# Chạy thử 1 lần ngay khi khởi động
job()

# Lập lịch chạy định kỳ mỗi 4 tiếng
schedule.every(2).minutes.do(job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)
