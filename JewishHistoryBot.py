import json
import random
import os
import requests
from datetime import datetime
from convertdate import hebrew
from bs4 import BeautifulSoup
import re

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}/"

    def send_message(self, chat_id, text):
        url = self.api_url + "sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload, verify=True)  # Disable SSL verification
        return response.json()

def get_today_hebrew_date(today):
    """Returns today's Hebrew date (day and month only)."""
    _, heb_month, heb_day = hebrew.from_gregorian(today.year, today.month, today.day)
    hebrew_months = [
        'ניסן', 'אייר', 'סיוון', 'תמוז', 'אב', 'אלול',
        'תשרי', 'חשוון', 'כסלו', 'טבת', 'שבט', 'אדר'
    ]
    hebrew_days = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י', 'יא', 'יב', 'יג', 'יד', 'טו', 'טז', 'יז', 'יח', 'יט', 'כ', 'כא', 'כב', 'כג', 'כד', 'כה', 'כו', 'כז', 'כח', 'כט', 'ל']
    hebrew_day = hebrew_days[heb_day - 1]
    hebrew_month = hebrew_months[heb_month - 1]
    return hebrew_day, hebrew_month

def gematria(hebrew_year):
    """
    Calculate the gematria value of a Hebrew year.
    """
    gematria_map = {
        'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
        'י': 10, 'כ': 20, 'ל': 30, 'מ': 40, 'נ': 50, 'ס': 60, 'ע': 70, 'פ': 80, 'צ': 90,
        'ק': 100, 'ר': 200, 'ש': 300, 'ת': 400
    }
    value = 0
    start_index = 0

    # Check if the second character is a '
    if len(hebrew_year) > 1 and hebrew_year[1] == "'":
        value += (ord(hebrew_year[0]) - ord('א') + 1) * 1000
        start_index = 2  # Start the loop from the 3rd character
    
    for char in hebrew_year[start_index:]:
        if char in gematria_map:  # Only process characters that exist in the map
            value += gematria_map[char]

    return value

def clean_event_text(text):
    """
    Clean event text by removing image descriptions in parentheses
    """
    # Remove (בתמונה) and similar photo references
    text = re.sub(r'\s*\(בתמונה\)\s*', ' ', text)
    text = re.sub(r'\s*\(בתמונה‏:\s*[^)]+\)\s*', ' ', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

def get_month_events(month_name, url):
    """
    Get events for a specific Hebrew month from Wikipedia
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=True)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return f"Error: Unable to fetch the webpage for {month_name}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        events = []
        
        rows = soup.find_all('tr')
        
        for row in rows:
            date_cell = row.find('td', style=lambda x: x and 'text-align:center' in x)
            content_cell = row.find('td', style=lambda x: x and 'text-align:right' in x)        
            if date_cell and content_cell:
                date_link = date_cell.find('a')
                if date_link and date_link.get('title'):
                    date = date_link.get('title')
                    events_list = content_cell.find('ul')
                    if events_list:
                        for event in events_list.find_all('li'):
                            b_tag = event.find('b')
                            if b_tag:
                                tag=b_tag.find('a')
                                if tag:
                                    subject_url = tag.get('href')
                                    subject_url = f'https://he.wikipedia.org{urllib.parse.unquote(subject_url)}'  # Decode the URL to Hebrew text
                                    subject = tag.get('title')
                                    event_text = clean_event_text(event.get_text().strip())
                                    events.append({
                                        'month': month_name,
                                        'date': date,
                                        'event': event_text,
                                        'subject_url': subject_url,
                                        'subject': subject
                                    })
        
        return events
    
    except Exception as e:
        return f"Error occurred for {month_name}: {str(e)}"

def read_hebrew_events(filename="hebrew_events.json"):
    """Reads the Hebrew events from the JSON file."""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_random_event(events, hebrew_day, hebrew_month):
    """Finds a random event that matches the Hebrew date."""
    matching_events = [event for event in events if event['day'] == hebrew_day and event['month'] == hebrew_month]
    return random.choice(matching_events) if matching_events else None

def fetch_wikipedia_content(url):
    """Fetches the main content from a Wikipedia page."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, verify=True)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        if not content_div:
            raise ValueError("Could not find main content")
        
        paragraphs = content_div.find_all(['p', 'h2'])
        return ' '.join(p.get_text() for p in paragraphs)
    
    except Exception as e:
        print(f"Error fetching content: {e}")
        return ""

def summarize_with_openai(text, ai='deepseek'):
    """Summarizes text using OpenAI or Deepseek API."""
    api_key = os.getenv('DEEPSEEK_API_KEY') if ai == 'deepseek' else os.getenv('OPENAI_API_KEY')
    model = 'deepseek-chat' if ai == 'deepseek' else 'gpt-4o'
    base_url = "https://api.deepseek.com" if ai == 'deepseek' else "https://api.openai.com"
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'system', 
                'content': 'Create a historical post for Telegram in Hebrew (~280 chars, 3-4 paragraphs). Include key figures, context, historical impact, emojis, and bold text for main subjects. Maintain historical accuracy.'
            },
            {
                'role': 'user', 
                'content': text
            }
        ]
    }
    
    try:
        response = requests.post(f'{base_url}/v1/chat/completions', headers=headers, json=payload, verify=True)
        response.raise_for_status()
        result = response.json()
        return {
            'summary': result['choices'][0]['message']['content'],
            'ai': ai,
            'model': model,
            'tokens_used': result.get('usage', {}).get('total_tokens', 0)
        }
    except Exception as e:
        print(f"API Error: {e}")
        return {'summary': '', 'tokens_used': 0}

def replace_headers_with_bold(text):
    """Replaces Markdown headers with bold text."""
    text = re.sub(r'^(## .+)$', r'*\1*', text, flags=re.MULTILINE)
    text = re.sub(r'^(# .+)$', r'*\1*', text, flags=re.MULTILINE)
    return text

def publish_to_telegram(post_str):
    """Publishes the post to Telegram."""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHANNEL = "@kedmachat"
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    return bot.send_message(CHANNEL, post_str)

def main():
    hebrew_day, hebrew_month = get_today_hebrew_date(datetime.now())
    events = read_hebrew_events()
    event = find_random_event(events, hebrew_day, hebrew_month)
    
    if event:
        print(event['event'])
        content = fetch_wikipedia_content(event['subject_url'])
        if content:
            summary_result = summarize_with_openai(content, ai='deepseek')
            if not summary_result['summary']:
                summary_result = summarize_with_openai(content, ai='openai')
            
            post = replace_headers_with_bold(summary_result['summary'])
            post_str = (
                f"* היום {hebrew_day} {hebrew_month} *\n"
                f"* {event['event']} *\n"
                f"{post}\n\n"
                f" [למידע נוסף]({event['subject_url']}) \n\n"
                "_בוט ה AI של קדמא_"
            )

            # result = publish_to_telegram(post_str)
            # print(result)
            
            with open("post.md", "w", encoding="utf-8") as f:
                f.write(post_str + "\n")

            sum_str = (
                "\nGenerated Summary:\n"
                f"*ai model:* {summary_result['model']}\n"
                f"*Tokens Used:* {summary_result['tokens_used']}"
            )
            with open("summary.md", "w", encoding="utf-8") as f:
                f.write(sum_str + "\n")

        else:
            print("Could not retrieve content")
    else:
        print(f"No event found for {hebrew_day} {hebrew_month}")

if __name__ == "__main__":
    main()