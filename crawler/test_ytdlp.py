import subprocess
import os
import glob

def test_ytdlp_transcript(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Testing yt-dlp transcript fetch for {video_id}...")
    
    # Try to fetch subtitles
    cmd = [
        "python3", "-m", "yt_dlp",
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang", "ko",
        "-o", "test_transcript",
        url
    ]
    
    try:
        subprocess.run(cmd, check=True)
        # Look for any subtitle files
        files = glob.glob("test_transcript*")
        if files:
            print(f"Success! Found files: {files}")
            # Filter for .vtt or .srt
            sub_file = next((f for f in files if f.endswith(('.vtt', '.srt'))), None)
            if sub_file:
                with open(sub_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"Content preview: {content[:100]}...")
            # Clean up
            for f in files:
                os.remove(f)
            return True
        else:
            print("No subtitle files found.")
            return False
    except Exception as e:
        print(f"yt-dlp failed: {e}")
        return False

if __name__ == "__main__":
    test_ytdlp_transcript("6SRmFEaHRu8") # Regular video
    test_ytdlp_transcript("WcZOSjCsxBs") # Shorts video
