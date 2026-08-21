import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment
load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.uploader.supabase_uploader import SupabaseStorageUploader

def test_meta_connections():
    print("=" * 60)
    print("1. TESTING META GRAPH API (INSTAGRAM & FACEBOOK)")
    print("=" * 60)
    
    token = os.getenv("META_SYSTEM_USER_TOKEN")
    page_id = os.getenv("MATCHDAY_FB_PAGE_ID")
    ig_id = os.getenv("MATCHDAY_IG_ACCOUNT_ID")
    
    print(f"Facebook Page ID: {page_id}")
    print(f"Instagram Account ID: {ig_id}")
    print(f"Token length: {len(token) if token else 0} chars\n")
    
    if not token or not page_id or not ig_id:
        print("[FAIL] Missing Meta credentials in .env")
        return False
        
    # A. Test Facebook Page Connection
    fb_url = f"https://graph.facebook.com/v26.0/{page_id}"
    fb_res = requests.get(fb_url, params={"fields": "id,name", "access_token": token})
    print(f"▶ Testing Facebook Page: {fb_url}")
    print(f"Status Code: {fb_res.status_code}")
    print(f"Response: {fb_res.json()}")
    if fb_res.status_code == 200:
        print("  ✓ Facebook Page Connection SUCCESSFUL!\n")
    else:
        print(f"  ✗ Facebook Page Connection FAILED: {fb_res.text}\n")

    # B. Test Instagram Account Connection
    ig_url = f"https://graph.facebook.com/v26.0/{ig_id}"
    ig_res = requests.get(ig_url, params={"fields": "id,username,name", "access_token": token})
    print(f"▶ Testing Instagram Account: {ig_url}")
    print(f"Status Code: {ig_res.status_code}")
    print(f"Response: {ig_res.json()}")
    if ig_res.status_code == 200:
        print("  ✓ Instagram Business Account Connection SUCCESSFUL!\n")
    else:
        print(f"  ✗ Instagram Business Account Connection FAILED: {ig_res.text}\n")


def test_supabase_connection():
    print("=" * 60)
    print("2. TESTING SUPABASE STORAGE CONNECTION & UPLOAD")
    print("=" * 60)
    
    uploader = SupabaseStorageUploader()
    print(f"Supabase URL: {uploader.supabase_url}")
    print(f"Supabase Bucket: {uploader.bucket_name}")
    print(f"Configured: {uploader.is_configured}\n")
    
    test_img = Path("dist/matchday/slide_1.png")
    if not test_img.exists():
        print(f"[FAIL] Test image not found at {test_img}")
        return False
        
    try:
        public_url = uploader.upload_file(test_img, remote_filename="test_verification_slide.png")
        print(f"  ✓ Upload Successful!")
        print(f"  ✓ Public URL: {public_url}")
        
        # Test if public URL is actually reachable over open internet
        res = requests.head(public_url, timeout=10)
        print(f"  ✓ Public Reachability Status: {res.status_code} ({res.headers.get('Content-Type', 'unknown')})")
        if res.status_code == 200:
            print("  ✓ Bucket is verified 100% PUBLIC and ready for Meta Instagram API!\n")
        else:
            print(f"  ⚠ Warning: Public URL returned status {res.status_code}\n")
    except Exception as e:
        print(f"  ✗ Supabase Upload Error: {e}\n")


if __name__ == "__main__":
    test_meta_connections()
    test_supabase_connection()
