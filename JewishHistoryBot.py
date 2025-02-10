import json
import random
import os
import requests
from datetime import datetime
from convertdate import hebrew
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, Any
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class TelegramBot:
    def __init__(self, token: str):
        if not token:
            raise ValueError("Telegram bot token is missing.")
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}/"

    def send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Sends a message to a Telegram chat."""
        url = self.api_url + "sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=payload, verify=False)  # Disable SSL verification
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to send Telegram message: {e}")
            return {}

def get_today_hebrew_date(today: datetime) -> tuple[str, str]:
    """Returns today's Hebrew date (day and month only)."""
    _, heb_month, heb_day = hebrew.from_gregorian(today.year, today.month, today.day)
    hebrew_months = [
        'ניסן', 'אייר', 'סיוון', 'תמוז', 'אב', 'אלול',
        'תשרי', 'חשוון', 'כסלו', 'טבת', 'שבט', 'אדר'
    ]
    hebrew_days = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י', 'יא', 'יב', 'יג', 'יד', 'טו', 'טז', 'יז', 'יח', 'יט', 'כ', 'כא', 'כב', 'כג', 'כד', 'כה', 'כו', 'כז', 'כח', 'כט', 'ל']
    return hebrew_days[heb_day - 1], hebrew_months[heb_month - 1]

def read_hebrew_events(filename: str = "hebrew_events.json") -> list[Dict[str, Any]]:
    """Reads the Hebrew events from the JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Failed to read events file: {e}")
        return []

def find_random_event(events: list[Dict[str, Any]], hebrew_day: str, hebrew_month: str) -> Dict[str, Any] | None:
    """Finds a random event that matches the Hebrew date."""
    matching_events = [event for event in events if event['day'] == hebrew_day and event['month'] == hebrew_month]
    return random.choice(matching_events) if matching_events else None

def fetch_wikipedia_content(url: str) -> str:
    """Fetches the main content from a Wikipedia page."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        if not content_div:
            raise ValueError("Could not find main content")
        
        paragraphs = content_div.find_all(['p', 'h2'])
        return ' '.join(p.get_text() for p in paragraphs)
    except Exception as e:
        logging.error(f"Error fetching Wikipedia content: {e}")
        return ""

def summarize_with_ai(text: str, ai: str = 'deepseek', timeout: int = 30) -> Dict[str, Any]:
    """
    Summarizes text using OpenAI or Deepseek API.
    If the API call times out or fails, retries with the alternative API (openai).
    
    Args:
        text (str): The text to summarize.
        ai (str): The AI service to use ('deepseek' or 'openai').
        timeout (int): Timeout in seconds for the API request.
    
    Returns:
        Dict[str, Any]: Contains 'summary', 'ai', 'model', and 'tokens_used'.
    """
    api_key = os.getenv('DEEPSEEK_API_KEY') if ai == 'deepseek' else os.getenv('OPENAI_API_KEY')
    if not api_key:
        logging.error(f"{ai.upper()} API key is missing.")
        return {'summary': '', 'ai': ai, 'model': 'N/A', 'tokens_used': 0}
    
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
        # Attempt API call with timeout
        response = requests.post(
            f'{base_url}/v1/chat/completions',
            headers=headers,
            json=payload,
            verify=False,
            timeout=timeout  # Set timeout for the request
        )
        response.raise_for_status()
        result = response.json()
        return {
            'summary': result['choices'][0]['message']['content'],
            'ai': ai,
            'model': model,
            'tokens_used': result.get('usage', {}).get('total_tokens', 0)
        }
    
    except requests.exceptions.Timeout:
        logging.warning(f"{ai.upper()} API request timed out. Retrying with OpenAI...")
        if ai == 'deepseek':
            return summarize_with_ai(text, ai='openai', timeout=timeout)  # Retry with OpenAI
        else:
            logging.error("OpenAI API also timed out. Aborting.")
            return {'summary': '', 'ai': ai, 'model': model, 'tokens_used': 0}
    
    except Exception as e:
        logging.error(f"API Error ({ai.upper()}): {e}")
        if ai == 'deepseek':
            return summarize_with_ai(text, ai='openai', timeout=timeout)  # Retry with OpenAI
        else:
            return {'summary': '', 'ai': ai, 'model': model, 'tokens_used': 0}

def replace_headers_with_bold(text: str) -> str:
    """Replaces Markdown headers with bold text."""
    text = re.sub(r'^(## .+)$', r'*\1*', text, flags=re.MULTILINE)
    text = re.sub(r'^(# .+)$', r'*\1*', text, flags=re.MULTILINE)
    return text

def publish_to_telegram(post_str: str) -> Dict[str, Any]:
    """Publishes the post to Telegram."""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TELEGRAM_BOT_TOKEN:
        logging.error("Telegram bot token is missing.")
        return {}
    
    CHANNEL = "@kedmachat"
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    return bot.send_message(CHANNEL, post_str)

def save_to_file(filename: str, content: str) -> None:
    """Saves content to a file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"Content saved to {filename}")
    except IOError as e:
        logging.error(f"Failed to save file {filename}: {e}")

def main():
    hebrew_day, hebrew_month = get_today_hebrew_date(datetime.now())
    events = read_hebrew_events()
    event = find_random_event(events, hebrew_day, hebrew_month)
    
    if not event:
        logging.warning(f"No event found for {hebrew_day} {hebrew_month}")
        return
    
    logging.info(f"Selected event: {event['event']}")
    content = fetch_wikipedia_content(event['subject_url'])
    if not content:
        logging.error("Could not retrieve content")
        return
    
    summary_result = summarize_with_ai(content, ai='deepseek')
    post = replace_headers_with_bold(summary_result['summary'])
    post_str = (
        f"*היום {hebrew_day} {hebrew_month}*\n\n"
        f"*{event['event']}*\n\n"
        f"{post}\n\n"
        f" [למידע נוסף]({event['subject_url']}) \n\n"
        "_בוט ה AI של קדמא_\n"
    )

    result = publish_to_telegram(post_str)
    if result:
        logging.info("Post published successfully.")
    
    save_to_file("post.md", post_str)
    sum_str = (
        "\nGenerated Summary:\n"
        f"*ai model:* {summary_result.get('model', 'N/A')}\n"
        f"*Tokens Used:* {summary_result.get('tokens_used', 0)}"
    )
    save_to_file("summary.md", sum_str)

if __name__ == "__main__":
    main()