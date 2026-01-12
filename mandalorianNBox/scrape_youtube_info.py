
import requests
import re
from bs4 import BeautifulSoup

url = "https://www.youtube.com/live/5vlU1DBnDlY?si=eAro4nFi5MQEEfjl"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Title
    title = soup.find('title').text
    if not title:
        match = re.search(r'"title":"(.*?)"', response.text)
        title = match.group(1) if match else "Unknown Title"
        
    print(f"TITLE: {title}")
    
    # Description (Meta)
    exclude_chars = ['\\n', '\\']
    desc_tag = soup.find('meta', {'name': 'description'})
    if desc_tag:
        desc = desc_tag['content']
        print(f"DESCRIPTION: {desc[:500]}...") # First 500 chars
    else:
        # Fallback Regex for description
        # "shortDescription":"..."
        match = re.search(r'"shortDescription":"(.*?)"', response.text)
        if match:
            print(f"DESCRIPTION (Regex): {match.group(1)[:500]}...")
        else:
            print("DESCRIPTION: Not found")
            
except Exception as e:
    print(f"Error: {e}")
