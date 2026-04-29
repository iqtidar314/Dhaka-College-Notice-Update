"""
Multi-page scraper for Dhaka College Notice Board
Scrapes up to 3 pages to detect page-1 notice removals
"""

import requests
from bs4 import BeautifulSoup
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple


class NoticeScraper:
    def __init__(self):
        self.base_url = "https://www.dhakacollege.edu.bd/en/notice"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = 10
        self.max_pages = 3
    
    def fetch_page(self, page_num: int = 1) -> Optional[str]:
        """Fetch a specific page of the notice board"""
        try:
            if page_num == 1:
                url = self.base_url
            else:
                url = f"{self.base_url}?page={page_num}"
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            print(f"❌ Timeout fetching page {page_num}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error fetching page {page_num}: {e}")
            return None
    
    def parse_notices(self, html_content: str) -> List[Dict]:
        """Parse notices from HTML content"""
        if not html_content:
            return []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            notices = []
            
            # Primary selector
            tbody = soup.select_one("body > main > section > div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6.lg\\:mt-10.lg\\:gap-8 > div > table > tbody")
            rows = []
            
            if tbody:
                rows = tbody.find_all('tr', class_='hover:bg-gray-50')
            
            # Fallback: look for any table with rows containing 4+ tds
            if not rows:
                for table in soup.find_all("table"):
                    for tr in table.find_all("tr"):
                        tds = tr.find_all("td")
                        if len(tds) >= 4:
                            rows = table.find_all("tr")
                            break
                    if rows:
                        print(f"Used fallback parser for page")
                        break
            
            if not rows:
                return []
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    serial = cells[0].get_text(strip=True)
                    title = cells[1].get_text(strip=True)
                    date = cells[2].get_text(strip=True)
                    download_link = ""
                    
                    link_element = cells[3].find('a')
                    if link_element and link_element.get('href'):
                        download_link = link_element.get('href')
                        # Handle relative URLs
                        if download_link.startswith('/'):
                            download_link = f"https://www.dhakacollege.edu.bd{download_link}"
                    
                    # Generate unique ID
                    notice_id = hashlib.md5(f"{title}{date}{download_link}".encode()).hexdigest()
                    
                    notice = {
                        "id": notice_id,
                        "serial": serial,
                        "title": title,
                        "date": date,
                        "download_url": download_link,
                        "timestamp": datetime.now(timezone(timedelta(hours=6))).isoformat()
                    }
                    notices.append(notice)
            
            return notices
        
        except Exception as e:
            print(f"❌ Error parsing notices: {e}")
            return []
    
    def scrape_all_pages(self) -> Tuple[List[Dict], Dict[int, List[Dict]]]:
        """
        Scrape all pages up to max_pages
        Returns: (all_notices, page_notices_dict)
        """
        all_notices = []
        page_notices = {}
        
        for page_num in range(1, self.max_pages + 1):
            print(f"📄 Scraping page {page_num}...")
            html_content = self.fetch_page(page_num)
            
            if not html_content:
                print(f"⚠️ Could not fetch page {page_num}, stopping")
                break
            
            notices = self.parse_notices(html_content)
            
            if not notices:
                print(f"📄 Page {page_num} has no notices, stopping")
                break
            
            page_notices[page_num] = notices
            all_notices.extend(notices)
            print(f"✅ Page {page_num}: {len(notices)} notices found")
        
        # Deduplicate by ID (keep first occurrence)
        seen_ids = set()
        unique_notices = []
        for notice in all_notices:
            if notice['id'] not in seen_ids:
                seen_ids.add(notice['id'])
                unique_notices.append(notice)
        
        print(f"📊 Total unique notices: {len(unique_notices)}")
        return unique_notices, page_notices
    
    def get_page_1_notices(self) -> List[Dict]:
        """Get only page 1 notices (for quick checks)"""
        html_content = self.fetch_page(1)
        if html_content:
            return self.parse_notices(html_content)
        return []


if __name__ == "__main__":
    # Test scraper
    scraper = NoticeScraper()
    all_notices, page_notices = scraper.scrape_all_pages()
    
    print("\n" + "="*50)
    print("SCRAPER TEST RESULTS")
    print("="*50)
    for page_num, notices in page_notices.items():
        print(f"\nPage {page_num}: {len(notices)} notices")
        for notice in notices[:3]:  # Show first 3
            print(f"  - [{notice['serial']}] {notice['title'][:50]}...")
