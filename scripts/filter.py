import os
import json
import gspread
import re
from google import genai
from oauth2client.service_account import ServiceAccountCredentials

# 1. Setup Gemini with the 2026 STABLE model
client_ai = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_NAME = "gemini-2.5-flash" # Updated from 2.0 to 2.5

def process_and_filter():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    gc = gspread.authorize(creds)
    
    db = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    raw_sheet = db.worksheet("Raw_Items")
    review_sheet = db.worksheet("Review")

    # Get URLs to avoid duplicates
    existing_entries = review_sheet.get_all_records()
    existing_urls = [str(r.get('URL', '')) for r in existing_entries]

    # Get raw news and limit to the top 15 most recent to avoid "Quota Overload"
    records = raw_sheet.get_all_records()[:15] 
    if not records:
        print("No news to filter.")
        return

    headlines_list = "\n".join([f"{i+1}. {r['Title']}" for i, r in enumerate(records)])

    prompt = f"""
    Score these news headlines from 1-10 based on global significance.
    Return ONLY a JSON list of numbers. 
    Example: [5, 8, 2]

    Headlines:
    {headlines_list}
    """

    print(f"AI is analyzing {len(records)} articles using {MODEL_NAME}...")
    
    try:
        response = client_ai.models.generate_content(model=MODEL_NAME, contents=prompt)
        # Remove any markdown code blocks the AI might add
        clean_text = re.sub(r'```json|```', '', response.text).strip()
        scores = json.loads(clean_text)
        
        for i, score in enumerate(scores):
            article = records[i]
            if score >= 7 and article['URL'] not in existing_urls:
                review_sheet.append_row([article['Title'], article['URL'], article['Source'], score])
                print(f"✅ Kept: {article['Title'][:50]}")
        
        # Clear the processed rows
        raw_sheet.delete_rows(2, len(records) + 1)
        print("Success! High-quality news moved to Review.")

    except Exception as e:
        print(f"Error: {e}")
        print(f"AI Response was: {response.text if 'response' in locals() else 'No response'}")

if __name__ == "__main__":
    process_and_filter()
