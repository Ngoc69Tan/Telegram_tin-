import os
import time
import threading
import requests
import feedparser
from flask import Flask
from google import genai

# Khởi tạo Flask app để Render không báo lỗi Port Binding
app = Flask(__name__)

# Cấu hình API Keys từ biến môi trường
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Khởi tạo Gemini Client chuẩn mới
client = genai.Client(api_key=GEMINI_API_KEY)

def get_latest_news():
    feed_url = "https://thanhnien.vn/rss/home.rss"
    feed = feedparser.parse(feed_url)
    news_list = []
    for entry in feed.entries[:5]:
        news_list.append(f"- Tiêu đề: {entry.title}\n  Tóm tắt: {entry.summary}\n  Link: {entry.link}")
    return "\n\n".join(news_list)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def job():
    print("🤖 Đang thu thập tin tức...")
    try:
        raw_news = get_latest_news()
        prompt = f"Hãy tóm tắt ngắn gọn các tin tức sau đây theo dạng danh sách dễ đọc bằng tiếng Việt:\n\n{raw_news}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        send_telegram(response.text)
        print("✅ Đã gửi tin nhắn Telegram thành công!")
    except Exception as e:
        print(f"❌ Lỗi trong quá trình xử lý: {e}")

def run_scheduler():
    # Gửi ngay 1 lần lúc vừa khởi động
    job()
    
    # Lặp lại mỗi 4 tiếng
    import schedule
    schedule.every(4).hours.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.route('/')
def home():
    return "Bot Telegram Tin Tức đang hoạt động!"

if __name__ == "__main__":
    # Chạy vòng lặp gửi tin trong một Thread riêng
    t = threading.Thread(target=run_scheduler)
    t.daemon = True
    t.start()
    
    # Chạy Flask Web Server ở luồng chính
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
