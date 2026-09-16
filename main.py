import os
import time
import requests
import feedparser
import schedule
from crewai import Agent, Task, Crew, Process, LLM

# ==================== 1. THÔNG TIN CẤU HÌNH CỦA BẠN ====================
import os
API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = "8605115616:AAHleFY6deA8apHaqyXJ_9yDDFdfZSNmjzg"
TELEGRAM_CHAT_ID = "5637028995"

os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# Khởi tạo LLM chuẩn hóa cho Key dạng mới
LLM_MODEL = LLM(
    model="gemini-3.6-flash",
    api_key=GEMINI_API_KEY
)

# Danh sách RSS Feed từ các trang báo chính thống
RSS_SOURCES = [
    "https://vnexpress.net/rss/thoi-su.rss",
    "https://tuoitre.vn/rss/thoi-su.rss",
    "https://thanhnien.vn/rss/thoi-su.rss",
    "https://dantri.com.vn/rss/xahoi.rss"
]

# ==================== 2. THU THẬP DỮ LIỆU BÁO CHÍ ====================
def fetch_all_news():
    articles = []
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.summary if hasattr(entry, 'summary') else ""
                })
        except Exception as e:
            print(f"Lỗi khi cào RSS {url}: {e}")
    return articles

# ==================== 3. KHỞI TẠO CREWAI AGENTS ====================
editor_agent = Agent(
    role="Biên tập viên kiểm duyệt",
    goal="Loại bỏ các bài báo đưa cùng một sự kiện trùng lặp.",
    backstory="Bạn là biên tập viên giàu kinh nghiệm.",
    verbose=True,
    llm=LLM_MODEL
)

writer_agent = Agent(
    role="Chuyên viên tóm tắt tin tức",
    goal="Tóm tắt các tin tức độc nhất thành bản tin sáng cô đọng, giữ lại link gốc.",
    backstory="Bạn là một biên tập viên điểm tin sáng chuyên nghiệp.",
    verbose=True,
    llm=LLM_MODEL
)

def run_ai_pipeline():
    print("🚀 Đang cào dữ liệu báo chí mới nhất...")
    raw_articles = fetch_all_news()

    task_dedup = Task(
        description=f"""
        Dưới đây là danh sách các bài báo thô vừa thu thập được:
        {raw_articles}

        Nhiệm vụ:
        1. Phân tích tiêu đề và tóm tắt.
        2. Nếu có 2 hoặc nhiều bài cùng nói về 1 sự kiện, CHỈ GIỮ LẠI 1 bài viết đầy đủ nhất.
        3. Trả về danh sách bài báo không trùng lặp (giữ nguyên title, link, summary).
        """,
        expected_output="Danh sách các bài báo đã lọc sạch trùng lặp.",
        agent=editor_agent
    )

    task_summarize = Task(
        description="""
        Từ danh sách bài báo đã lọc, hãy tạo thành 1 Bản Tin Sáng theo đúng định dạng Markdown sau:

        📰 **BẢN TIN SÁNG NÓNG HỔI**

        1. **[Tiêu đề bài viết]**
        - **Tóm tắt:** [Tóm tắt 2-3 câu ngắn gọn về sự kiện]
        - **Nguồn:** [Đường link gốc]

        (Lặp lại cho các bài tin tiếp theo)
        """,
        expected_output="Bản tin hoàn chỉnh bằng Markdown sẵn sàng gửi đi.",
        agent=writer_agent
    )

    news_crew = Crew(
        agents=[editor_agent, writer_agent],
        tasks=[task_dedup, task_summarize],
        process=Process.sequential
    )

    print("🤖 AI Agent đang tiến hành lọc tin trùng và tóm tắt...")
    result = news_crew.kickoff()
    send_telegram(str(result))

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    max_length = 3500
    
    # Chia nhỏ tin nhắn nếu vượt quá 3500 ký tự
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk
        }
        res = requests.post(url, json=payload)
        print(f"Phản hồi Telegram (Phần {i//max_length + 1}):", res.json())
        time.sleep(1)
# ==================== 4. THỰC THI CHƯƠNG TRÌNH ====================
if __name__ == "__main__":
    print("🤖 Khởi động hệ thống AI Agent...")
    run_ai_pipeline()