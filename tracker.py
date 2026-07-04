import os
import sys
import json
import re
import pandas as pd
from datetime import datetime
from apify_client import ApifyClient

# Resolve encoding issues in Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration paths
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
OUTPUT_EXCEL = os.path.join(os.path.dirname(__file__), "odoo_tracker_results.xlsx")

if not os.path.exists(CONFIG_PATH):
    print(f"Error: Configuration file not found at {CONFIG_PATH}")
    exit(1)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

APIFY_TOKEN = config.get("apify_token", "")
if APIFY_TOKEN == "YOUR_APIFY_API_TOKEN" or not APIFY_TOKEN:
    print("Error: Please set your Apify API Token in config.json")
    exit(1)

client = ApifyClient(APIFY_TOKEN)

# Load existing results from Excel sheets to prevent duplicates
existing_data = {
    "Facebook Leads": [],
    "LinkedIn Jobs": [],
    "LinkedIn Posts": []
}

if os.path.exists(OUTPUT_EXCEL):
    try:
        xls = pd.ExcelFile(OUTPUT_EXCEL)
        for sheet in xls.sheet_names:
            if sheet in existing_data:
                df_old = pd.read_excel(xls, sheet_name=sheet)
                existing_data[sheet] = df_old.to_dict(orient="records")
                print(f"Loaded {len(existing_data[sheet])} existing items for sheet '{sheet}' from Excel.")
    except Exception as e:
        print(f"Warning: Could not read existing Excel file sheets: {e}. Starting fresh.")

def get_existing_keys(sheet_name, key_col):
    items = existing_data.get(sheet_name, [])
    return {item[key_col] for item in items if isinstance(item, dict) and key_col in item and item[key_col]}

# ==========================================
# 1. SCRAPE FACEBOOK GROUPS
# ==========================================
fb_config = config.get("facebook", {})
new_fb_items = []

if fb_config.get("enabled", False):
    groups = fb_config.get("groups", [])
    keywords = fb_config.get("keywords", [])
    limit = fb_config.get("limit_per_group", 10)
    actor_id = fb_config.get("actor_id", "apify/facebook-groups-scraper")
    existing_fb_keys = get_existing_keys("Facebook Leads", "post_url")

    print(f"\n--- Starting Facebook Groups Scraping ({len(groups)} groups) ---")
    
    run_input = {
        "startUrls": [{"url": url} for url in groups],
        "resultsLimit": limit,
    }
    
    try:
        run = client.actor(actor_id).call(run_input=run_input)
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "default_dataset_id", None) or run["defaultDatasetId"]
        
        keywords_regex = re.compile("|".join([re.escape(k.lower()) for k in keywords]), re.IGNORECASE)
        
        for item in client.dataset(dataset_id).iterate_items():
            post_text = item.get("text") or item.get("message") or item.get("postText") or ""
            post_url = item.get("url") or item.get("postUrl") or item.get("link") or ""
            
            author_url = ""
            user_obj = item.get("user") or item.get("author")
            if isinstance(user_obj, dict):
                author_url = user_obj.get("url") or user_obj.get("link") or user_obj.get("profileUrl") or ""
            if not author_url:
                author_url = item.get("authorUrl") or item.get("ownerLink") or item.get("profileUrl") or ""

            post_date = item.get("time") or item.get("date") or item.get("createdAt") or ""

            if not post_url or not post_text:
                continue
            if post_url in existing_fb_keys:
                continue

            if keywords_regex.search(post_text):
                new_fb_items.append({
                    "date": post_date,
                    "post_url": post_url,
                    "author_url": author_url,
                    "post_text": post_text.strip()
                })
        print(f"Facebook: Found {len(new_fb_items)} new matching posts.")
    except Exception as e:
        print(f"Error scraping Facebook Groups: {e}")
else:
    print("\nFacebook Groups Scraping is disabled.")

# ==========================================
# 2. SCRAPE LINKEDIN JOBS (curious_coder/linkedin-jobs-scraper)
# ==========================================
li_jobs_config = config.get("linkedin_jobs", {})
new_li_jobs = []

if li_jobs_config.get("enabled", False):
    queries = li_jobs_config.get("queries", [])
    locations = li_jobs_config.get("locations", [])
    keywords = li_jobs_config.get("keywords", [])
    limit = li_jobs_config.get("limit", 10)
    actor_id = li_jobs_config.get("actor_id", "curious_coder/linkedin-jobs-scraper")
    existing_job_keys = get_existing_keys("LinkedIn Jobs", "job_url")

    print(f"\n--- Starting LinkedIn Jobs Scraping ({len(queries)} queries, {len(locations)} locations) ---")
    keywords_regex = re.compile("|".join([re.escape(k.lower()) for k in keywords]), re.IGNORECASE)

    # Construct search URLs
    urls_to_scrape = []
    for query in queries:
        for loc in locations:
            # Construct standard LinkedIn Jobs search URL
            search_url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={loc}"
            urls_to_scrape.append(search_url)

    print(f"Triggering LinkedIn Jobs Scraper for {len(urls_to_scrape)} search URLs...")
    run_input = {
        "urls": urls_to_scrape,
        "count": limit,
        "scrapeCompany": False # Disable company scrape for faster execution and lower cost
    }
    
    try:
        run = client.actor(actor_id).call(run_input=run_input)
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "default_dataset_id", None) or run["defaultDatasetId"]
        
        for item in client.dataset(dataset_id).iterate_items():
            job_title = item.get("title") or item.get("jobTitle") or ""
            job_url = item.get("link") or item.get("url") or item.get("jobUrl") or ""
            
            company = ""
            company_obj = item.get("company")
            if isinstance(company_obj, dict):
                company = company_obj.get("name") or company_obj.get("title") or ""
            else:
                company = item.get("companyName") or item.get("company") or ""

            location = item.get("location") or item.get("locationName") or ""
            description = item.get("descriptionText") or item.get("description") or item.get("jobDescription") or ""
            post_date = item.get("postedAt") or item.get("postDate") or item.get("date") or item.get("createdAt") or ""

            if not job_url or not job_title:
                continue
            if job_url in existing_job_keys:
                continue

            # Filter description or title with keywords
            text_to_check = f"{job_title} {description}"
            if keywords_regex.search(text_to_check):
                new_li_jobs.append({
                    "date": post_date,
                    "job_title": job_title,
                    "company": company,
                    "location": location,
                    "job_url": job_url,
                    "description": description[:300].strip() + "..." if len(description) > 300 else description.strip()
                })
        print(f"LinkedIn Jobs: Found {len(new_li_jobs)} new matching jobs.")
    except Exception as e:
        print(f"Error scraping LinkedIn Jobs: {e}")
else:
    print("\nLinkedIn Jobs Scraping is disabled.")

# ==========================================
# 3. SCRAPE LINKEDIN POSTS (apimaestro/linkedin-posts-search-scraper-no-cookies)
# ==========================================
li_posts_config = config.get("linkedin_posts", {})
new_li_posts = []

if li_posts_config.get("enabled", False):
    queries = li_posts_config.get("queries", [])
    keywords = li_posts_config.get("keywords", [])
    limit = li_posts_config.get("limit", 10)
    actor_id = li_posts_config.get("actor_id", "apimaestro/linkedin-posts-search-scraper-no-cookies")
    existing_post_keys = get_existing_keys("LinkedIn Posts", "post_url")

    print(f"\n--- Starting LinkedIn Posts Scraping ({len(queries)} queries) ---")
    keywords_regex = re.compile("|".join([re.escape(k.lower()) for k in keywords]), re.IGNORECASE)

    for query in queries:
        print(f"Running scraper for keyword: {query}...")
        run_input = {
            "keyword": query,
            "limit": limit,
            "sort_type": "date_posted",
            "date_filter": "past-month"
        }
        
        try:
            run = client.actor(actor_id).call(run_input=run_input)
            dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else getattr(run, "default_dataset_id", None) or run["defaultDatasetId"]
            
            for item in client.dataset(dataset_id).iterate_items():
                post_text = item.get("text") or item.get("message") or item.get("postText") or ""
                post_url = item.get("post_url") or item.get("url") or item.get("postUrl") or item.get("link") or ""
                
                author_name = ""
                author_url = ""
                author_obj = item.get("author") or item.get("user")
                if isinstance(author_obj, dict):
                    author_name = author_obj.get("name") or author_obj.get("title") or ""
                    author_url = author_obj.get("profile_url") or author_obj.get("url") or author_obj.get("link") or author_obj.get("profileUrl") or ""
                else:
                    author_name = item.get("authorName") or item.get("userName") or ""
                    author_url = item.get("authorUrl") or item.get("userUrl") or ""

                posted_at_obj = item.get("posted_at")
                if isinstance(posted_at_obj, dict):
                    post_date = posted_at_obj.get("date") or posted_at_obj.get("display_text") or ""
                else:
                    post_date = item.get("time") or item.get("date") or item.get("createdAt") or ""

                if not post_url or not post_text:
                    continue
                if post_url in existing_post_keys:
                    continue

                if keywords_regex.search(post_text):
                    new_li_posts.append({
                        "date": post_date,
                        "author_name": author_name,
                        "author_url": author_url,
                        "post_url": post_url,
                        "post_text": post_text.strip()
                    })
        except Exception as e:
            print(f"Error scraping LinkedIn Posts for keyword {query}: {e}")
            
    print(f"LinkedIn Posts: Found {len(new_li_posts)} new matching posts.")
else:
    print("\nLinkedIn Posts Scraping is disabled.")

# ==========================================
# 4. CONSOLIDATE AND SAVE TO EXCEL
# ==========================================
def merge_and_get_df(sheet_name, new_items, key_col, default_cols):
    old_records = existing_data.get(sheet_name, [])
    # Combine existing and new records
    combined_records = old_records + new_items
    if not combined_records:
        return pd.DataFrame(columns=default_cols)
    
    df = pd.DataFrame(combined_records)
    # Deduplicate by key column
    if key_col in df.columns:
        df.drop_duplicates(subset=[key_col], inplace=True)
    return df

print("\n--- Saving All Results to Excel ---")
try:
    df_fb = merge_and_get_df("Facebook Leads", new_fb_items, "post_url", ["date", "post_url", "author_url", "post_text"])
    df_li_jobs = merge_and_get_df("LinkedIn Jobs", new_li_jobs, "job_url", ["date", "job_title", "company", "location", "job_url", "description"])
    df_li_posts = merge_and_get_df("LinkedIn Posts", new_li_posts, "post_url", ["date", "author_name", "author_url", "post_url", "post_text"])

    try:
        with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
            df_fb.to_excel(writer, sheet_name="Facebook Leads", index=False)
            df_li_jobs.to_excel(writer, sheet_name="LinkedIn Jobs", index=False)
            df_li_posts.to_excel(writer, sheet_name="LinkedIn Posts", index=False)
        print(f"Excel database successfully updated at: {OUTPUT_EXCEL}")
    except PermissionError:
        # File is locked, save to backup path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_excel = OUTPUT_EXCEL.replace(".xlsx", f"_temp_{timestamp}.xlsx")
        print(f"\n[WARNING] Permission denied: '{OUTPUT_EXCEL}' is currently open/locked (probably open in Excel).")
        print(f"Please close the file in Excel to allow updates next time.")
        print(f"Saving your new data to a backup file: {backup_excel}")
        with pd.ExcelWriter(backup_excel, engine='openpyxl') as writer:
            df_fb.to_excel(writer, sheet_name="Facebook Leads", index=False)
            df_li_jobs.to_excel(writer, sheet_name="LinkedIn Jobs", index=False)
            df_li_posts.to_excel(writer, sheet_name="LinkedIn Posts", index=False)
        print(f"Temporary backup file saved successfully.")

    # Save to leads.json
    LEADS_JSON_PATH = os.path.join(os.path.dirname(__file__), "leads.json")
    leads_data = {
        "facebook": df_fb.to_dict(orient="records"),
        "linkedin_jobs": df_li_jobs.to_dict(orient="records"),
        "linkedin_posts": df_li_posts.to_dict(orient="records")
    }
    try:
        with open(LEADS_JSON_PATH, "w", encoding="utf-8") as json_file:
            json.dump(leads_data, json_file, ensure_ascii=False, indent=2)
        print(f"JSON database successfully updated at: {LEADS_JSON_PATH}")
    except Exception as je:
        print(f"Error saving consolidation to JSON: {je}")

    # Optional Auto-Git Push to GitHub Pages
    if config.get("auto_git_push", False):
        print("\n--- Pushing Updates to GitHub ---")
        try:
            os.system("git add leads.json odoo_tracker_results.xlsx")
            os.system('git commit -m "Auto-update leads data"')
            os.system("git push")
            print("Successfully pushed latest data to GitHub!")
        except Exception as ge:
            print(f"Error executing git commands: {ge}")

    print(f"Current Row Counts:")
    print(f" - Facebook Leads: {len(df_fb)}")
    print(f" - LinkedIn Jobs: {len(df_li_jobs)}")
    print(f" - LinkedIn Posts: {len(df_li_posts)}")
except Exception as e:
    print(f"Error saving consolidation to Excel: {e}")
