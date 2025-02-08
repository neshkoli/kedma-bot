import requests
from bs4 import BeautifulSoup
import re
import urllib3
import json
import urllib.parse
from convertdate import hebrew

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

def get_all_hebrew_months_events():
    """
    Get events for all Hebrew months
    """
    hebrew_months = [
        'ניסן', 'אייר', 'סיוון', 'תמוז', 'אב', 'אלול',
        'תשרי', 'חשוון', 'כסלו', 'טבת', 'שבט', 'אדר' ]

    url_str = 'https://he.wikipedia.org/wiki/ויקיפדיה:אירועים_בלוח_העברי/'
    all_events = []
    
    # for month_name, url in months_urls.items():
    for month_name in hebrew_months:
        url = f"{url_str}{month_name}"
        print(f"Fetching events for {month_name}...")
        month_events = get_month_events(month_name, url)
        
        if isinstance(month_events, list):
            all_events.extend(month_events)
        else:
            print(month_events)
    
    return all_events

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

def save_events_to_file(events, filename='hebrew_events.json'):
    filtered_events = []
    try:
        for event in events:
            event_text = event['event']
            first_word = event_text.split()[0]
            # Check if the first word matches the Hebrew year format
            if re.match(r'^[א-ת]\'[א-ת]{1,3}"[א-ת]$', first_word):
                event['year'] = first_word
                heb_year = event['year']
                # Convert Hebrew year to Gregorian year
                gregorian_year = hebrew.to_gregorian(gematria(heb_year), 1, 1)[0]  # Convert using the first day of the Hebrew year
                event['gregorian_year'] = gregorian_year
                event['event'] = ' '.join(event_text.split()[1:])  # Remove the year from the event text
                event['event'] = event['event'][2:]  # Remove the leading '- '
                day = event['date'].split()[0]  # Extract the Hebrew day
                day = day.replace('"', '').replace("'", "")  # Remove " and ' characters
                event['day'] = day
                del event['date']  # Remove the original 'date' field
                if gregorian_year > -600 and gregorian_year < 1910:  # Filter out events outside this range
                    filtered_events.append(event)

        with open(filename, 'w', encoding='utf-8') as f:
            hebrew_month_order = ['תשרי', 'חשוון', 'כסלו', 'טבת', 'שבט', 'אדר', 'ניסן', 'אייר', 'סיוון', 'תמוז', 'אב', 'אלול']
            filtered_events.sort(key=lambda x: (hebrew_month_order.index(x['month']), x['day']))

            json.dump(filtered_events, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving events to file: {e}")

# Run the scraper
if __name__ == "__main__":
    all_events = get_all_hebrew_months_events()
    save_events_to_file(all_events)
