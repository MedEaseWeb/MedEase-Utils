import asyncio
import json
import os
from urllib.parse import urlparse, urljoin
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# CONFIGURATION
BASE_URL = "https://accessibility.emory.edu/"
DOMAIN = "accessibility.emory.edu"
OUTPUT_FILE = "emory_data.json"
MAX_PAGES = 50  # Safety limit for testing
POLITENESS_DELAY = 2.0  # Seconds between requests

async def scrape_site():
    # 1. Setup the browser config (headless = True is faster)
    browser_conf = BrowserConfig(headless=True)
    
    # 2. Setup the crawler config
    # css_selector="main" focuses the scraper on the main content area, 
    # ignoring navbars/footers which improves RAG quality.
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="main", 
        word_count_threshold=10
    )

    # State management
    visited = set()
    queue = [BASE_URL]
    scraped_data = []

    print(f"🚀 Starting crawl of {BASE_URL}...")

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        while queue and len(visited) < MAX_PAGES:
            current_url = queue.pop(0)
            
            # Skip if already visited
            if current_url in visited:
                continue
            
            print(f"Processing: {current_url}")
            
            try:
                # 3. The actual scrape
                result = await crawler.arun(
                    url=current_url,
                    config=run_conf
                )

                if result.success:
                    # Store the data for your RAG system
                    scraped_data.append({
                        "url": current_url,
                        "title": result.media.get("title", "No Title"),
                        "markdown": result.markdown, # This is the gold for RAG
                        "last_scraped": "2026-01-18" # Or dynamic date
                    })
                    
                    visited.add(current_url)

                    # 4. Link Discovery (Naive implementation)
                    # Crawl4AI returns internal links automatically in result.links
                    internal_links = result.links.get("internal", [])
                    
                    for link_data in internal_links:
                        href = link_data.get("href")
                        if not href:
                            continue
                        
                        # Normalize the URL
                        full_url = urljoin(current_url, href)
                        parsed = urlparse(full_url)
                        
                        # Filter: strictly stay on accessibility.emory.edu
                        # and avoid files like .pdf or .jpg
                        if (parsed.netloc == DOMAIN and 
                            full_url not in visited and 
                            full_url not in queue and
                            not any(full_url.endswith(ext) for ext in ['.pdf', '.jpg', '.png'])):
                            
                            queue.append(full_url)

                else:
                    print(f"❌ Failed to scrape {current_url}: {result.error_message}")

            except Exception as e:
                print(f"⚠️ Error on {current_url}: {e}")

            # 5. Politeness Delay
            await asyncio.sleep(POLITENESS_DELAY)

    # 6. Save to "Database" (JSON file)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Crawl complete! {len(scraped_data)} pages saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(scrape_site())