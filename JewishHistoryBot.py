import json
import random
import os
import httpx
from datetime import datetime
from datetime import date
from convertdate import hebrew
from openai import OpenAI
import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, Any

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
        
        response = requests.post(url, json=payload, verify=False)  # Disable SSL verification
        return response.json()

def get_today_hebrew_date(today):
    """Returns today's Hebrew date in the specified language (day and month only)."""

    # Get today's Hebrew date (day, month)
    _ , heb_month, heb_day = hebrew.from_gregorian(today.year, today.month, today.day)  
    # Hebrew month names
    hebrew_months = [
        'ניסן', 'אייר', 'סיוון', 'תמוז', 'אב', 'אלול',
        'תשרי', 'חשוון', 'כסלו', 'טבת', 'שבט', 'אדר' ]
    hebrew_days = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י', 'יא', 'יב', 'יג', 'יד', 'טו', 'טז', 'יז', 'יח', 'יט', 'כ', 'כא', 'כב', 'כג', 'כד', 'כה', 'כו', 'כז', 'כח', 'כט', 'ל']
    hebrew_day = f"{hebrew_days[heb_day - 1]}"
    hebrew_month = f"{hebrew_months[heb_month - 1]}"
    return hebrew_day, hebrew_month

def read_hebrew_events(filename="hebrew_events.json"):
    """Reads the Hebrew events from the JSON file"""
    with open(filename, 'r', encoding='utf-8') as f:
        events = json.load(f)
    return events

def find_random_event(events, hebrew_day, hebrew_month):
    """Finds a random event that matches the Hebrew date"""
    matching_events = [event for event in events if event['day'] == hebrew_day and event['month'] == hebrew_month]
    if matching_events:
        return random.choice(matching_events)
    return None

def fetch_wikipedia_content(url: str) -> str:
    """
    Fetch the main content from a Wikipedia page
    
    Args:
        url (str): Wikipedia URL to scrape
    
    Returns:
        str: Extracted text content
    """
    try:
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }        
        response = requests.get(url, headers=headers, verify=False)
        response.encoding = 'utf-8'
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract main content
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        
        if not content_div:
            raise ValueError("Could not find main content")
        
        # Extract text paragraphs
        paragraphs = content_div.find_all(['p', 'h2'])
        full_text = ' '.join([p.get_text() for p in paragraphs])
        
        return full_text
    
    except Exception as e:
        print(f"Error fetching content: {e}")
        return ""

def summarize_with_openai(text: str, ai: str = 'deepseek') -> Dict[str, Any]:
    """
    Use OpenAI's API to generate a summary based on specific requirements
    
    Args:
        text (str): Input text to summarize
        language (str): Target language for summary
    
    Returns:
        dict: Structured summary 
    """
    if ai == 'deepseek':
        api_key = os.getenv('DEEPSEEK_API_KEY')
        model = 'deepseek-chat'
        base_url = "https://api.deepseek.com"
    else:
        api_key = os.getenv('OPENAI_API_KEY')
        model = 'gpt-4o'
        base_url = 'https://api.openai.com'
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': model,
        'messages': [
            {
                'role': 'system', 
                'content': f'Create a historical post for Telegram social network in Hebrew from this text following these guidelines:' + 
                           '- Total ~280 chrars in 3-4 paragraph' +
                           '- Include key figures' +
                           '- Add context of the period' +
                           '- Highlight historical impact' +
                           '- Use emojis and bold with * for main subjects' +
                           '- Educational storytelling tone' +
                           '- Keep strict historical accuracy'
            },
            {
                'role': 'user', 
                'content': text
            }
        ]
    }
    
    try:
        url = f'{base_url}/v1/chat/completions'
        print (url)
        response = requests.post(
            url, 
            headers=headers, 
            json=payload,
            verify=False
        )
        response.raise_for_status()
        
        result = response.json()
        summary = result['choices'][0]['message']['content']
        
        return {
            'summary': summary,
            'ai': ai,
            'model': model,
            'tokens_used': result.get('usage', {}).get('total_tokens', 0)
        }
    
    except Exception as e:
        print(f"API Error: {e}")
        return {'summary': '', 'tokens_used': 0}

def create_post_from_event(event):
    prompt = f'''Create a historical post in Hebrew about {event} . 
        Required elements (~240 chars):
        - Event/person details
        - 3-4 historical facts
        - Key figures
        - Quotes if relevant
        - Period context
        - Location
        - Historical impact
        - Jewish tradition link

        Format:
        - Markdown
        - Rich Hebrew language with emojis and bold for the main subjects
        - Storytelling style
        - 3 paragraphs
        - Educational tone
        - Specific dates/names
        - Historical accuracy
        - Primary sources'''

    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    model = "gpt-4o"
    # client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com", http_client=httpx.Client(verify=False))
    # model = "deepseek-chat"

    try:
        # Add error handling and timeout
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a historian specializing in Jewish history"},
                {"role": "user", "content": prompt}
            ],
            timeout=30.0  # Add a timeout to prevent hanging
        )
        
        # Debug print to see the actual response type
        print(type(completion))
        
        # Try different methods to convert to dictionary
        try:
            # Method 1: Use object_to_dict function
            def object_to_dict(obj):
                if hasattr(obj, '__dict__'):
                    return {key: object_to_dict(value) for key, value in vars(obj).items()}
                elif isinstance(obj, (list, tuple)):
                    return [object_to_dict(item) for item in obj]
                else:
                    return obj

            response_dict = object_to_dict(completion)
            print(json.dumps(response_dict, indent=2))
            
            # Return the content
            return completion.choices[0].message.content.strip()
        
        except Exception as convert_error:
            print(f"Conversion error: {convert_error}")
            
            # Fallback method
            try:
                # If the above fails, try to manually extract content
                return completion.choices[0].message.content.strip()
            except Exception as extract_error:
                print(f"Content extraction error: {extract_error}")
                raise

    except Exception as e:
        print(f"API call error: {e}")
        raise

def replace_headers_with_bold(text):
    # Replace headers starting with # or ## with bold text
    text = re.sub(r'^(### .+)$', r'*\1*', text, flags=re.MULTILINE)
    text = re.sub(r'^(## .+)$', r'*\1*', text, flags=re.MULTILINE)
    text = re.sub(r'^(# .+)$', r'*\1*', text, flags=re.MULTILINE)
    
    return text

def publish_to_telegram(post_str):
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHANNEL = "@kedmachat"
    
    # Initialize bot
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    return bot.send_message(CHANNEL, post_str)

def main():
    hebrew_day, hebrew_month = get_today_hebrew_date(datetime.now())
    events = read_hebrew_events()
    event = find_random_event(events, hebrew_day, hebrew_month)
    print(event['event'])
    
    if event:
        content = fetch_wikipedia_content(event['subject_url'])
        # post = create_post_from_event(event['event'])
        # post = post.replace('```markdown', '').replace('```', '')
        if content:
            # Summarize content
            summary_result = summarize_with_openai(content,ai='deepseek')
            model= summary_result['model']
            post = summary_result['summary']

            post = replace_headers_with_bold(post)
            post_str = f"* היום {hebrew_day} {hebrew_month} *\n* {event['event']} *\n{post}\n\n_בוט ה AI של קדמא_"

            result = publish_to_telegram(post_str)
            print(result)
            with open(f"post.md", "w", encoding="utf-8") as f:
                f.write(post_str + "\n")

            print("Generated Summary:\n")
            print(f"ai model: {model}\n")
            print(f"Tokens Used: {summary_result['tokens_used']}")
        else:
            print("Could not retrieve content")

    else:
        print(f"No event found for {hebrew_day} {hebrew_month}")

if __name__ == "__main__":
    main()