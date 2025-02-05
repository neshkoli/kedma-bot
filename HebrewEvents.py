import requests
from bs4 import BeautifulSoup
import re
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        response = requests.get(url, headers=headers, verify=False)
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
                            event_text = clean_event_text(event.get_text().strip())
                            events.append({
                                'month': month_name,
                                'date': date,
                                'event': event_text
                            })
        
        return events
    
    except Exception as e:
        return f"Error occurred for {month_name}: {str(e)}"

def get_all_hebrew_months_events():
    """
    Get events for all Hebrew months
    """
    months_urls = {
        'תשרי': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/תשרי',
        'חשון': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/חשוון',
        'כסלו': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/כסלו',
        'טבת': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/טבת',
        'שבט': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/שבט',
        'אדר': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/אדר',
        'ניסן': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/ניסן',
        'אייר': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/אייר',
        'סיון': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/סיוון',
        'תמוז': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/תמוז',
        'אב': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/אב',
        'אלול': 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/אלול'
    }
    
    all_events = []
    
    for month_name, url in months_urls.items():
        print(f"Fetching events for {month_name}...")
        month_events = get_month_events(month_name, url)
        
        if isinstance(month_events, list):
            all_events.extend(month_events)
        else:
            print(month_events)
    
    return all_events

def save_events_to_file(events, filename="hebrew_events.json"):
    """
    Save events to a JSON file
    """
    if not isinstance(events, list):
        print(events)
        return

    try:
        filtered_events = []
        for event in events:
            event_text = event.get('event', '')
            if event_text:
                first_word = event_text.split()[0]
                # Check if the first word matches the Hebrew year format
                if re.match(r'^[א-ת]\'[א-ת]{1,3}"[א-ת]$', first_word):
                    event['year'] = first_word
                    event['event'] = ' '.join(event_text.split()[1:])  # Remove the year from the event text
                    day = event['date'].split()[0]  # Extract the Hebrew day
                    day = day.replace('"', '').replace("'", "")  # Remove " and ' characters
                    event['day'] = day
                    del event['date']  # Remove the original 'date' field
                    filtered_events.append(event)

        with open(filename, 'w', encoding='utf-8') as f:
            hebrew_month_order = ['תשרי', 'חשון', 'כסלו', 'טבת', 'שבט', 'אדר', 'ניסן', 'אייר', 'סיון', 'תמוז', 'אב', 'אלול']
            filtered_events.sort(key=lambda x: (hebrew_month_order.index(x['month']), x['day']))

            json.dump(filtered_events, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving events to file: {e}")

# Run the scraper
if __name__ == "__main__":
    import prettytable  # Import needed for table styling
    all_events = get_all_hebrew_months_events()
#    display_events_table(all_events)
    save_events_to_file(all_events)