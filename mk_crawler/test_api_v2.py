import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi

video_id = "aaQQVLljqx8"

print(f"Module file: {youtube_transcript_api.__file__}")
print(f"Top level dir: {dir(youtube_transcript_api)}")
print(f"YouTubeTranscriptApi dir: {dir(YouTubeTranscriptApi)}")

print("\n--- Testing get_transcript ---")
try:
    print("Method 1: YouTubeTranscriptApi.get_transcript(video_id)")
    YouTubeTranscriptApi.get_transcript(video_id)
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\nMethod 2: YouTubeTranscriptApi().get_transcript(video_id)")
    YouTubeTranscriptApi().get_transcript(video_id)
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")

print("\n--- Testing list_transcripts ---")
try:
    print("Method 3: YouTubeTranscriptApi.list_transcripts(video_id)")
    YouTubeTranscriptApi.list_transcripts(video_id)
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")

print("\n--- Testing 'list' method found in dir ---")
try:
    print("Method 4: YouTubeTranscriptApi.list(video_id)")
    YouTubeTranscriptApi.list(video_id)
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
