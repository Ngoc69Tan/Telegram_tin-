import os
import time
import threading
import requests
import feedparser
from flask import Flask
import google.generativeai as genai

app = Flask(__name__)

# Lấy Biến môi trường từ Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def get_latest_news():
    feed_url = "https://thanhnien.vn/rss/home.rss"
    feed = feedparser.parse(feed_url)
    news_list = []
    for entry in feed.entries[:5]:
        news_list.append(f"- Tiêu đề: {entry.title}\n  Tóm tắt: {entry.summary}\n  Link: {entry.link}")
    return "\n\n".join(news_list)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    requests.post(url, json=payload)

def job():
    print("🤖 Đang thu thập tin tức...")
    try:
        raw_news = get_latest_news()
        prompt = f"Hãy tóm tắt ngắn gọn các tin tức sau đây theo dạng danh sách dễ đọc bằng tiếng Việt:\n\n{raw_news}"
        
        response = model.generate_content(prompt)
        send_telegram(response.text)
        print("✅ Đã gửi tin nhắn Telegram thành công!")
        return True, "Thành công"
    except Exception as e:
        print(f"❌ Lỗi xử lý: {e}")
        return False, str(e)

def run_scheduler():
    # Tự động gửi 1 lần sau khi khởi động 5 giây
    time.sleep(5)
    job()
    
    import schedule
    schedule.every(4).hours.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.route('/')
def home():
    return "Bot đang hoạt động! Muốn test gửi tin ngay hãy vào đường dẫn /test"

# Tạo đường dẫn /test để bạn tự kích hoạt gửi tin bằng trình duyệt
@app.route('/test')
def test_send():
    success, msg = job()
    if success:
        return "✅ Đã kích hoạt gửi tin nhắn Telegram thành công!"
    else:
        return f"❌ Lỗi khi gửi tin: {msg}"

if __name__ == "__main__":
    t = threading.Thread(target=run_scheduler)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
