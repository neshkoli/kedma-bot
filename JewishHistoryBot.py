import json
import random
import os
import httpx
from datetime import datetime
from datetime import date
from convertdate import hebrew
from openai import OpenAI
import requests

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}/"

    def send_message(self, chat_id, text):
        """
        Send a message to a channel
        Args:
            chat_id (str): Channel username (including @)
            text (str): Message to send
        Returns:
            dict: Telegram API response
        """
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
        'ניסן', 'אייר', 'סיון', 'תמוז', 'אב', 'אלול',
        'תשרי', 'חשוון', 'כסלו', 'טבת', 'שבט', 'אדר'
    ]
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
        - 3-4 paragraphs
        - Educational tone
        - Specific dates/names
        - Historical accuracy
        - Primary sources'''

    # client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    http_client = httpx.Client(verify=False)
    client = OpenAI(
        api_key=os.getenv('DEEPSEEK_API_KEY'), 
        base_url="https://api.deepseek.com", 
        http_client=http_client
    )

    try:
        # Add error handling and timeout
        completion = client.chat.completions.create(
            model="deepseek-chat",
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
    print(event)
    
    if event:
        post = create_post_from_event(event['event'])
        post = post.replace('```markdown', '').replace('```', '')
        post_str = f"*היום {hebrew_day} {hebrew_month}*\n{post}\n\n_בוט ה AI של קדמא_"
        with open("post.md", "w", encoding="utf-8") as f:
            f.write(post_str + "\n")
        result = publish_to_telegram(post_str)
        print(result)

    else:
        print(f"No event found for {hebrew_day} {hebrew_month}")

if __name__ == "__main__":
    main()