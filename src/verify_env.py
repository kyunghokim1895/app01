import os
import sys
import sqlite3
from dotenv import load_dotenv

def check_env():
    print(">>> Starting Environmental Verification...")
    load_dotenv()
    
    # 1. Check API Keys
    youtube_key = os.getenv("YOUTUBE_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not youtube_key:
        print("ERROR: YOUTUBE_API_KEY not found in .env")
        return False
    if not gemini_key:
        print("ERROR: GEMINI_API_KEY not found in .env")
        return False
    
    print("   [OK] API Keys are present.")

    # 2. Check Dependencies
    try:
        import google.generativeai as genai
        import youtube_transcript_api
        import yt_dlp
        print("   [OK] Essential Python libraries are installed.")
    except ImportError as e:
        print(f"ERROR: Missing dependency: {str(e)}")
        return False

    # 3. Check Workspace Directory
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, "src")):
        print(f"ERROR: 'src' directory not found in {cwd}. Are you in the project root?")
        return False
    print(f"   [OK] Working directory verified: {cwd}")

    print(">>> Verification Successful!")
    return True

if __name__ == "__main__":
    if not check_env():
        sys.exit(1)
    sys.exit(0)
