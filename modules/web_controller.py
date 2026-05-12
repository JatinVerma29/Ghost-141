"""
modules/web_controller.py — Web browsing and news fetching
"""
import webbrowser
import urllib.parse
import requests
from bs4 import BeautifulSoup
import warnings
try:
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except ImportError:
    pass



class WebController:
    def __init__(self, settings):
        self.settings = settings
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def navigate(self, url: str):
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)

    def search(self, query: str):
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        webbrowser.open(url)

    def youtube(self, query: str):
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
        webbrowser.open(url)

    def open_gmail(self):
        webbrowser.open("https://mail.google.com")

    def get_news_headlines(self, topic: str = "") -> list:
        """Fetch news using HTML parser (no lxml/xml needed)."""
        try:
            q = urllib.parse.quote_plus(topic + " news") if topic else "top news"
            url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            r = requests.get(url, headers=self.headers, timeout=10)
            # Use html.parser — always available, no extra install needed
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.find_all("item")[:8]
            headlines = []
            for item in items:
                title = item.find("title")
                if title:
                    # Clean up the title (remove source name after " - ")
                    t = title.get_text().strip()
                    if " - " in t:
                        t = t.rsplit(" - ", 1)[0].strip()
                    headlines.append(t)
            return headlines if headlines else self._fallback_news(topic)
        except Exception as e:
            return self._fallback_news(topic)

    def _fallback_news(self, topic: str) -> list:
        """Fallback: scrape Google News search results."""
        try:
            q = urllib.parse.quote_plus(topic + " news today")
            url = f"https://www.google.com/search?q={q}&tbm=nws"
            r = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            headlines = []
            for tag in soup.find_all(["h3", "div"], class_=True)[:10]:
                text = tag.get_text().strip()
                if len(text) > 20 and len(text) < 200:
                    headlines.append(text)
            return headlines[:6] if headlines else [f"Search for '{topic} news' opened in browser."]
        except Exception:
            return [f"Could not fetch news. Try: search {topic} news today"]

    def get_weather(self, city: str) -> str:
        try:
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=3"
            r = requests.get(url, timeout=8)
            return r.text.strip()
        except Exception as e:
            return f"Weather unavailable: {e}"