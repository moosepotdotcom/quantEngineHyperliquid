
import feedparser
import threading
import time
import re
import json
import os
from datetime import datetime
from utils.logger import log_to_journal

class NewsEngine(threading.Thread):
    def __init__(self, refresh_rate=300):
        super().__init__()
        self.feeds = [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cryptoslate.com/feed/",
            "https://www.reddit.com/r/Bitcoin/hot/.rss",
            "https://www.reddit.com/r/CryptoCurrency/hot/.rss",
            "https://cryptopanic.com/news/rss/" # Aggregates Twitter/X & Media
        ]
        self.refresh_rate = refresh_rate # 5 minutes default
        self.running = True
        self.seen_titles = set()
        self.cache_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'news_cache.json')
        self._load_cache()
        self.latest_news = None
        self.daemon = True 

    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.seen_titles = set(json.load(f))
                print(f"📰 News Engine: Loaded {len(self.seen_titles)} seen articles.")
        except Exception as e:
            print(f"⚠️ News Cache Load Error: {e}")

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(list(self.seen_titles), f)
        except Exception as e:
            print(f"⚠️ News Cache Save Error: {e}")

    def run(self):
        """Entry point for the thread"""
        print(f"📰 Starting News Engine (Sources: {len(self.feeds)})...")
        while self.running:
            try:
                self._fetch_news()
                # Sleep in small chunks to allow faster stopping
                for _ in range(self.refresh_rate):
                    if not self.running: break
                    time.sleep(1)
            except Exception as e:
                print(f"⚠️ News Engine Error: {e}")
                time.sleep(60)

    def _fetch_news(self):
        for url in self.feeds:
            if not self.running: break
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]: # Check top 3 from each
                    title = entry.title
                    link = entry.link
                    
                    # Clean title
                    clean_title = self._clean_html(title)
                    
                    if clean_title not in self.seen_titles:
                        self.seen_titles.add(clean_title)
                        
                        # Extract Source nicely
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc
                        source_name = domain.replace('www.', '').split('.')[0].capitalize()
                        
                        # Store for the bot main loop to see
                        self.latest_news = {
                            'title': clean_title,
                            'source': source_name,
                            'url': link,
                            'pay_attention': self._is_high_impact(clean_title)
                        }
                        
                        # Log immediately
                        self._log_news(self.latest_news)
                        self._save_cache()
                        
            except Exception:
                continue

    def _clean_html(self, raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    def _is_high_impact(self, text):
        keywords = [
            'SEC', 'Ban', 'Hack', 'Approve', 'ETF', 'Rate Hike', 'Powell', 'Binance', 'Collapse',
            'Moon', 'Rekt', 'Pump', 'YOLO', 'Gem', 'Bull run', 'Bear market', 'ATH'
        ]
        return any(k.lower() in text.lower() for k in keywords)

    def _log_news(self, news_item):
        emoji = "🚨" if news_item['pay_attention'] else "📰"
        title = "MARKET NEWS ALERT" if news_item['pay_attention'] else "News Update"
        
        details = f"- **Headline**: {news_item['title']}\n- **Source**: {news_item['source']}\n- **Link**: {news_item['url']}"
        log_to_journal(title, details, emoji)

    def stop(self):
        self.running = False
