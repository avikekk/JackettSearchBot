import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import math

def get_jackett_search_url(jackett_url: str, jackett_api_key: str, query: str) -> str:

    if query.startswith("tt") and query[2:].isdigit():
        return f'{jackett_url}/api/v2.0/indexers/all/results/torznab/api?apikey={jackett_api_key}&imdbid={query}'
    else:
        query = requests.utils.quote(query)
        return f'{jackett_url}/api/v2.0/indexers/all/results/torznab/api?apikey={jackett_api_key}&t=search&q={query}'
    
def convert_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_pub_date(pub_date):
    date_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
    time_elapsed = datetime.now(date_obj.tzinfo) - date_obj

    if time_elapsed.days > 0:
        return f'{time_elapsed.days} d'
    else:
        hours, remainder = divmod(time_elapsed.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f'{hours} h'
        elif minutes > 0:
            return f'{minutes} m'
        else:
            return f'{seconds} s'

def parse_jackett_response(response_content, golden_popcorn=False):
    root = ET.fromstring(response_content)
    results = []

    for item in root.findall(".//item"):
        title = item.find('title').text
        
        # Skip if Golden Popcorn filter is active and title doesn't contain it
        if golden_popcorn and "Golden Popcorn" not in title:
            continue
            
        size_bytes = int(item.find('size').text)
        size_readable = convert_size(size_bytes)
        pub_date = item.find('pubDate').text
        formatted_pub_date = format_pub_date(pub_date)

        result_text = (
            f'<b>Title:</b> <code>{title}</code>\n'
            f'<b>Age:</b> {formatted_pub_date}\n'
            f'<b>Size:</b> {size_readable}\n'
        )
        results.append(result_text)

    return results

def parse_jackett_response_for_paste(response_content, golden_popcorn=False):
    root = ET.fromstring(response_content)
    results = []

    for item in root.findall(".//item"):
        title = item.find('title').text
        
        # Skip if Golden Popcorn filter is active and title doesn't contain it
        if golden_popcorn and "Golden Popcorn" not in title:
            continue
            
        size_bytes = int(item.find('size').text)
        size_readable = convert_size(size_bytes)
        pub_date = item.find('pubDate').text
        formatted_pub_date = format_pub_date(pub_date)

        result_text = (
            f'Title: {title}\n'
            f'Age: {formatted_pub_date}\n'
            f'Size: {size_readable}\n'
        )
        results.append(result_text)

    return results
