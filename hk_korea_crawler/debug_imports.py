import os
import sys
print('Python Version:', sys.version)
print('CWD:', os.getcwd())
try:
    print('Importing youtube_transcript_api...')
    from youtube_transcript_api import YouTubeTranscriptApi
    print('Imported youtube_transcript_api')
    
    print('Importing google.generativeai...')
    import google.generativeai as genai
    print('Imported google.generativeai')
    
    print('All imports done!')
except Exception as e:
    print(f'Error: {e}')
