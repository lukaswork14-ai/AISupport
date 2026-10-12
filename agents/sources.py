"""Danh sách nguồn tin. Sửa tự do: thêm/bớt dòng, mỗi nguồn là (tên, url RSS/Atom).
Nguồn nào lỗi sẽ bị bỏ qua và được báo trong bản tin, không làm hỏng cả hệ thống."""

SOURCES = [
    # --- AI nói chung và AI cho công việc ---
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Ars Technica AI", "https://arstechnica.com/ai/feed/"),
    # --- Marketing / bán hàng / ecommerce ---
    ("Marketing Dive", "https://www.marketingdive.com/feeds/news/"),
    ("Modern Retail", "https://www.modernretail.co/feed/"),
    ("Practical Ecommerce", "https://www.practicalecommerce.com/feed"),
    ("Search Engine Land", "https://searchengineland.com/feed"),
    ("Ecommerce Fuel (Reddit r/ecommerce)", "https://www.reddit.com/r/ecommerce/top/.rss?t=day"),
    ("Reddit r/printondemand", "https://www.reddit.com/r/printondemand/top/.rss?t=day"),
    ("Reddit r/AmazonSeller", "https://www.reddit.com/r/AmazonSeller/top/.rss?t=day"),
    ("Reddit r/EtsySellers", "https://www.reddit.com/r/EtsySellers/top/.rss?t=day"),
    ("Reddit r/TikTokshop", "https://www.reddit.com/r/TikTokshop/top/.rss?t=day"),
    # --- Google News theo từ khóa (gom nhiều báo uy tín) ---
    ("GNews: TikTok Shop", "https://news.google.com/rss/search?q=%22TikTok+Shop%22+when:2d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: Amazon sellers", "https://news.google.com/rss/search?q=%22Amazon+sellers%22+when:2d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: Etsy", "https://news.google.com/rss/search?q=Etsy+sellers+when:2d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: Shopify", "https://news.google.com/rss/search?q=Shopify+merchants+when:2d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: print on demand", "https://news.google.com/rss/search?q=%22print+on+demand%22+when:3d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: cross-border ecommerce", "https://news.google.com/rss/search?q=%22cross-border+ecommerce%22+when:3d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: AI marketing", "https://news.google.com/rss/search?q=%22AI+marketing%22+OR+%22AI+for+marketing%22+when:2d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: AI agents business", "https://news.google.com/rss/search?q=%22AI+agents%22+business+when:2d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: TikTok ads", "https://news.google.com/rss/search?q=%22TikTok+ads%22+when:3d&hl=en-US&gl=US&ceid=US:en"),
    # --- Nguồn bổ sung (nền tảng lớn, cộng đồng AI/ecom) ---
    ("Hacker News (AI)", "https://hnrss.org/newest?q=AI+OR+LLM+OR+agent&points=100"),
    ("OpenAI News", "https://openai.com/news/rss.xml"),
    ("Shopify Blog", "https://www.shopify.com/blog.atom"),
    ("Reddit r/Etsy", "https://www.reddit.com/r/Etsy/top/.rss?t=day"),
    ("Reddit r/ChatGPT", "https://www.reddit.com/r/ChatGPT/top/.rss?t=day"),
    ("Reddit r/LocalLLaMA", "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day"),
    ("Reddit r/FulfillmentByAmazon", "https://www.reddit.com/r/FulfillmentByAmazon/top/.rss?t=day"),
    ("GNews: Amazon Seller Central updates", "https://news.google.com/rss/search?q=%22Seller+Central%22+OR+%22Amazon+seller+fees%22+when:3d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: Meta Instagram creators", "https://news.google.com/rss/search?q=Meta+OR+Instagram+creators+ads+when:2d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: X platform", "https://news.google.com/rss/search?q=%22X+platform%22+OR+Grok+when:2d&hl=en-US&gl=US&ceid=US:en"),
    ("GNews: Temu Shein TEMU sellers", "https://news.google.com/rss/search?q=Temu+OR+Shein+OR+%22TikTok+Shop%22+tariffs+sellers+when:3d&hl=en-US&gl=US&ceid=US:en"),
]

# Chủ đề người dùng quan tâm (đưa vào prompt chấm điểm)
TOPICS = (
    "AI nói chung; AI for work; AI for marketing; AI for sales; AI for operations; AI for creative; "
    "AI để xây sản phẩm; cross-border ecommerce; POD (print on demand); Amazon; Etsy; Shopify; "
    "TikTok Shop; TikTok Ads; TikTok Ecommerce"
)
