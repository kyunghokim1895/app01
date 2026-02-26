import os
import json
from dotenv import load_dotenv
import googleapiclient.discovery
from datetime import datetime

def get_full_date(api_key, cid):
    youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
    res = youtube.search().list(part='snippet', channelId=cid, maxResults=1, order='date', type='video').execute()
    item = res['items'][0]['snippet']
    return item['title'], item['publishedAt']

def main():
    load_dotenv()
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    print("Sentv:", get_full_date(api_key, 'UC3p-0EWA8OXko2EUDUXAy5w'))
    print("HKGlobal:", get_full_date(api_key, 'UCWskYkV4c4S9D__rsfOl2JA'))

if __name__ == "__main__":
    main()
