from youtube_transcript_api import YouTubeTranscriptApi

def test_video(video_id):
    print(f"Testing video: {video_id}")
    try:
        # 가장 기본적인 메서드 사용
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'ko-KR'])
        print(f"Success! Fetched {len(data)} lines.")
        print(f"First line: {data[0]['text']}")
    except Exception as e:
        print(f"Error for {video_id}: {e}")

if __name__ == "__main__":
    test_video("aaQQVLljqx8")
    print("-" * 20)
    test_video("uz7-v5glyw0")
