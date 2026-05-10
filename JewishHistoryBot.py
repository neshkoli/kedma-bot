import json
import random
import os
import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from convertdate import hebrew
import urllib3
import sys
import logging

# Configure logging for GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def log_group(title: str):
    """Log a collapsible group in GitHub Actions."""
    print(f"::group::{title}")

def log_end_group():
    """End a collapsible group in GitHub Actions."""
    print("::endgroup::")


# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure constants
API_TIMEOUT = 30
MAX_CONTENT_LENGTH = 4000  # Truncate long Wikipedia content
REQUEST_RETRIES = 2
HEBREW_EVENTS_FILE = "hebrew_events.json"
TELEGRAM_CHANNEL = "@kedmachat"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

class HTTPSession:
    """Shared HTTP session with retries and common headers"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.session.verify = False  # Disable SSL verification

class TelegramBot:
    def __init__(self, token: str):
        if not token:
            raise ValueError("Telegram bot token is missing.")
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}/"
        self.http = HTTPSession().session

    def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Sends a message to a Telegram chat."""
        url = self.api_url + "sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        try:
            response = self.http.post(url, json=payload, timeout=API_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Telegram API error: {str(e)}")
            return {}

class WikipediaClient:
    def __init__(self):
        self.http = HTTPSession().session

    def fetch_content(self, url: str) -> str:
        """Fetches main content from a Wikipedia page."""
        try:
            response = self.http.get(url, timeout=API_TIMEOUT)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            content_div = soup.find('div', {'class': 'mw-parser-output'})
            
            if not content_div:
                raise ValueError("Wikipedia content structure changed")
            
            # Extract relevant content elements
            elements = content_div.find_all(['p', 'h2', 'h3'])
            cleaned_elements = [self._clean_element(e) for e in elements[:10]]  # First 10 elements
            return ' '.join(filter(None, cleaned_elements))
        
        except Exception as e:
            logging.error(f"Wikipedia fetch failed: {str(e)}")
            return ""

    def _clean_element(self, element) -> str:
        """Cleans HTML elements from unwanted content"""
        text = element.get_text().strip()
        
        # Remove citation references and edit links
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\[edit\]', '', text)
        
        return text if len(text) > 40 else ''  # Filter short elements

class AIClient:
    def __init__(self):
        self.http = HTTPSession().session
        self.providers = ['deepseek', 'openai']
        self.models = {
            'deepseek': 'deepseek-chat',
            'openai': 'gpt-4o'
        }

    def summarize(self, text: str) -> Dict[str, Any]:
        """Generates summary using available AI providers with fallback"""
        text = self._preprocess_content(text)
        
        for provider in self.providers:
            result = self._try_provider(provider, text)
            if result.get('summary'):
                result['summary'] = self._strip_meta_preamble(result['summary'])
                return result
        
        return {'summary': '', 'ai': 'none', 'model': 'none', 'tokens_used': 0}

    def _try_provider(self, provider: str, text: str) -> Dict[str, Any]:
        """Attempt summary generation with a specific provider"""
        api_key = os.getenv(f'{provider.upper()}_API_KEY')
        if not api_key:
            logging.warning(f"Missing API key for {provider}")
            return {}

        base_url = "https://api.deepseek.com" if provider == 'deepseek' else "https://api.openai.com"
        url = f"{base_url}/v1/chat/completions"
        
        system = (
            'You write the Hebrew body text for a Jewish-history Telegram post.\n'
            'Output ONLY the post paragraph(s): compact (roughly 200–450 characters), '
            'Telegram Markdown with **bold** on names and key terms, occasional emojis.\n'
            'Rules:\n'
            '- Start immediately with historical facts. No preamble or meta lines.\n'
            '- Forbidden: any line that describes the task (e.g. Hebrew phrases like '
            '"הנה פוסט", "פוסט היסטורי", "להלן", "זהו פוסט", "קצר ומדויק לטלגרם"), '
            'English task blurbs, horizontal rules (---), or section headers.\n'
            '- Do not repeat a calendar date line or the event title; they are added separately.'
        )
        user = (
            'נסח רק את גוף הפוסט מהקטע הבא (בלי משפטי פתיחה או הסבר על הפוסט):\n\n'
            + text[:MAX_CONTENT_LENGTH]
        )
        payload = {
            'model': self.models[provider],
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            'temperature': 0.7,
            'max_tokens': 300
        }

        try:
            response = self.http.post(
                url,
                headers={'Authorization': f'Bearer {api_key}'},
                json=payload,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            return {
                'summary': data['choices'][0]['message']['content'],
                'ai': provider,
                'model': self.models[provider],
                'tokens_used': data.get('usage', {}).get('total_tokens', 0)
            }
        except Exception as e:
            logging.warning(f"{provider.capitalize()} API failed: {str(e)}")
            return {}

    def _preprocess_content(self, text: str) -> str:
        """Clean and format content before sending to AI"""
        text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
        return text.strip()

    def _strip_meta_preamble(self, text: str) -> str:
        """Remove model meta-intros and separators sometimes echoed despite instructions."""
        t = text.strip()
        # Leading Hebrew/English task-framing lines (non-greedy through first newline block)
        t = re.sub(
            r'^(?:'
            r'הנה\s+פוסט[^\n]*|'
            r'פוסט\s+היסטורי[^\n]*|'
            r'להלן\s+פוסט[^\n]*|'
            r'זהו\s+פוסט[^\n]*|'
            r'(?:here\s+is|below\s+is)\s+a\s+(?:short\s+)?(?:historical\s+)?post[^\n]*'
            r')\s*\n+',
            '',
            t,
            flags=re.IGNORECASE | re.UNICODE,
        )
        t = re.sub(r'^(?:[-─–_•]\s*){3,}\s*\n+', '', t)
        return t.strip()

def validate_environment() -> bool:
    """Check required environment variables"""
    required = ['TELEGRAM_BOT_TOKEN', 'DEEPSEEK_API_KEY', 'OPENAI_API_KEY']
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        logging.error(f"Missing environment variables: {', '.join(missing)}")
        return False
    return True

def get_hebrew_date(today: datetime) -> tuple[str, str]:
    """Returns today's Hebrew date components"""
    _, heb_month, heb_day = hebrew.from_gregorian(today.year, today.month, today.day)
    months = ['ניסן', 'אייר', 'סיוון', 'תמוז', 'אב', 'אלול',
             'תשרי', 'חשוון', 'כסלו', 'טבת', 'שבט', 'אדר']
    days = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י', 
           'יא', 'יב', 'יג', 'יד', 'טו', 'טז', 'יז', 'יח', 'יט', 
           'כ', 'כא', 'כב', 'כג', 'כד', 'כה', 'כו', 'כז', 'כח', 'כט', 'ל']
    return days[heb_day - 1], months[heb_month - 1]

def load_events(filename: str = HEBREW_EVENTS_FILE) -> List[Dict[str, Any]]:
    """Load historical events from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Failed to load events: {str(e)}")
        return []

def select_event(events: List[Dict[str, Any]], day: str, month: str) -> Optional[Dict[str, Any]]:
    """Select random event matching date"""
    candidates = [e for e in events if e['day'] == day and e['month'] == month]
    return random.choice(candidates) if candidates else None

def format_post(event: Dict[str, Any], day: str, month: str, summary: str) -> str:
    """Format final Telegram post"""
    post = re.sub(r'^#+\s*(.+)$', r'*\1*', summary, flags=re.MULTILINE)
    return (
        f"*היום {day} {month}*\n\n"
        f"*{event['event']}*\n\n"
        f"{post}\n\n"
        f"[למידע נוסף]({event['subject_url']})\n\n"
        "_בוט ה AI של קדמא_"
    )

def main():
    log_group("Initializing Script")
    if not validate_environment():
        return

    date = datetime.now()
    hebrew_day, hebrew_month = get_hebrew_date(date)
    
    if not (events := load_events()):
        return
    
    if not (event := select_event(events, hebrew_day, hebrew_month)):
        logging.warning(f"No events found for {hebrew_day} {hebrew_month}")
        return

    wiki = WikipediaClient()
    if not (content := wiki.fetch_content(event['subject_url'])):
        return

    ai = AIClient()
    summary = ai.summarize(content)
    
    if not summary.get('summary'):
        logging.error("Failed to generate summary")
        return

    post = format_post(event, hebrew_day, hebrew_month, summary['summary'])
    bot = TelegramBot(os.getenv('TELEGRAM_BOT_TOKEN'))

    result = bot.send_message(TELEGRAM_CHANNEL, post)
    if result.get('ok'):
        logging.info("Post published successfully")
    else:
        logging.error("Failed to publish post to Telegram")

    # Save outputs
    with open('post.md', 'w', encoding='utf-8') as f:
        f.write(post)
    
    logging.info(f"Summary generated using {summary['ai']} ({summary['model']})")
    log_end_group()
    
if __name__ == "__main__":
    main()


