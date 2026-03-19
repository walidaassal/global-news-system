import os
import json
import gspread
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials

# 1. Setup
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash') # The fast, free-tier workhorse

def process_and_filter():
    # Connect to Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT_KEY"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    db = client.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    raw_sheet = db.worksheet("Raw_Items")
    review_sheet = db.worksheet("Review")

    # Get all news from the raw tab
    records = raw_sheet.get_all_records()
    if not records:
        print("No news to filter.")
        return

    print(f"AI is analyzing {len(records)} articles...")

    for row_index, article in enumerate(records, start=2):
        prompt = f"""
        You are a senior news editor. Score this headline from 1-10 based on global significance, 
        geopolitical impact, and market importance.
        
        Headline: {article['Title']}
        Source: {article['Source']}
        
        Return ONLY a single number (e.g., 8).
        """
        
        response = model.generate_content(prompt)
        try:
            score = int(response.text.strip())
        except:
            score = 0 # Safety fallback
            
        print(f"Scored '{article['Title'][:30]}...': {score}")

        if score >= 7:
            # Move to Review tab: Title, URL, Source, Score
            review_sheet.append_row([article['Title'], article['URL'], article['Source'], score])
    
    # Optional: Clear the raw sheet so we don't process the same news twice tomorrow
    raw_sheet.delete_rows(2, len(records) + 1)
    print("Filtering complete. Check your 'Review' tab!")

if __name__ == "__main__":
    process_and_filter()
