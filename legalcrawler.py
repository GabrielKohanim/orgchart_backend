import requests
import json
import time
import os
from firecrawl import FirecrawlApp
from openai import OpenAI
from dotenv import load_dotenv
import datetime

load_dotenv()


def mapSite(url):
    app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
    map_result = app.map_url(url)
    return map_result


def filter_lawfirm_urls(urls, openai_client):
    """
    Filter URLs to maximize law firm relevant coverage using OpenAI
    """
    system_prompt = """You are the "firecrawl_filter" AI for WebsiteIntelligenceAgent.
● INPUT: JSON array of raw URLs (strings), all from the same law‑firm domain.
● OUTPUT: JSON array named "results" of URLs filtered to maximize firm‑relevant coverage—while still dropping purely utility pages.
TEMPORARY LIMIT: Maximum 50 URLs in output (this clause will be removed soon)

Always Include

The root/homepage URL (e.g. "https://example.com/") as the first entry.

Core Inclusion
Keep any URL whose path includes any of these segments:
• /about, /team, /leadership, /people, /attorney, /partner, /bio
• /careers, /jobs, /open-positions, /were-hiring
• /contact, /locations
• /services, /practice-areas, /solutions, /technology, /tech-stack
• /testimonials, /reviews, /case-studies, /success-stories
• /resources, .pdf, /brochures, /white-papers
Expanded News & Insights
Keep any URL under these sections, regardless of slug:
• /blog, /news, /updates, /insights, /publications, /news-resources, /victories
For blog/news slugs, still prefer those containing legal‑adjacent keywords (law, legal, firm, client, case, practice), but do not drop other posts unless obviously off‑topic.
Permissive Category/Tag
Allow category or tag pages only if their segment contains a legal term, e.g.:
• /category/legal-news, /tag/firm-announcements
Otherwise, drop generic auto‑tags like /category/*.
Strict Exclusions
Exclude any URL if the path includes or ends with:
• /login, /signup, /search, /events, /calendar, /privacy, /terms, /sitemap, /archive
• File extensions: .js, .css, .jpg, .png, .svg, .ico, .woff, .map
Final Rules

Preserve original order; remove exact duplicates.
If a URL matches both inclusion and exclusion, include it.
If filtered results exceed 50 URLs, prioritize in this order: homepage, core pages (about/team/services), then news/blog content, stopping at 50 total.
Output strictly valid JSON array named "results"—no comments or extra fields."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(urls)}
            ],
            response_format={"type": "json_object"},
            top_p=0.1
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("results", [])
    except Exception as e:
        print(f"Error filtering URLs with OpenAI: {e}")
        return urls[:50]  # Fallback to first 50 URLs


def batch_scrape_urls(urls, firecrawl_app):
    """
    Submit URLs for batch scraping
    """
    try:
        # Submit batch scrape request
        batch_response = firecrawl_app.async_batch_scrape_urls(urls, formats=['markdown'])
        return batch_response
    except Exception as e:
        print(f"Error submitting batch scrape: {e}")
        return None


def get_scrape_status(batch_id, firecrawl_app):
    """
    Check the status of a batch scrape operation
    """
    try:
        status_response = firecrawl_app.check_batch_scrape_status(batch_id)
        return status_response
    except Exception as e:
        print(f"Error getting batch status: {e}")
        return None


def get_scrape_results(batch_id, firecrawl_app):
    """
    Retrieve the results of a completed batch scrape
    """
    try:
        results_response = firecrawl_app.get_batch_results(batch_id)
        return results_response
    except Exception as e:
        print(f"Error getting batch results: {e}")
        return None


def crawl_lawfirm_website(url, max_wait_time=500, api_key_firecrawl=None, api_key_openai=None):
    """
    Complete law firm website crawling function that replicates the n8n workflow
    
    Args:
        url (str): The law firm website URL to crawl
        max_wait_time (int): Maximum time to wait for batch scrape completion (seconds)
    
    Returns:
        dict: Contains 'all_links' (original mapped URLs) and 'scraped' (scraped data)
    """
    try:
        # Initialize clients
        firecrawl_app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        #firecrawl_app = FirecrawlApp(api_key=api_key_firecrawl)
        #openai_client = OpenAI(api_key=api_key_openai)

        print(f"Starting crawl for: {url}")
        
        # Step 1: Map the website to get all URLs
        print("Step 1: Mapping website...")
        map_result = firecrawl_app.map_url(url)
        all_links = map_result.links
        print(f"Found {len(all_links)} URLs")
        
        if not all_links:
            return {"all_links": [], "scraped": []}
        
        # Step 2: Filter URLs using OpenAI
        print("Step 2: Filtering URLs with AI...")
        filtered_urls = filter_lawfirm_urls(all_links, openai_client)
        print(f"Filtered to {len(filtered_urls)} relevant URLs")
        
        if not filtered_urls:
            return {"all_links": all_links, "scraped": []}
        
        # Step 3: Submit batch scrape
        print("Step 3: Submitting batch scrape...")
        batch_response = batch_scrape_urls(filtered_urls, firecrawl_app)
        
        if not batch_response:
            return {"all_links": all_links, "scraped": []}
        
        batch_id = batch_response.id
        if not batch_id:
            print("No batch ID received")
            return {"all_links": all_links, "scraped": []}
        
        # Step 4: Wait for completion and get results
        print("Step 4: Waiting for scrape completion...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = get_scrape_status(batch_id, firecrawl_app)
            
            if status_response and status_response.status == "completed":
                print("Scrape completed, retrieving results...")
                results = get_scrape_status(batch_id, firecrawl_app)
                print(results)
                if results:
                    cleaned_results = []
                    for scraped in results.data:
                        cleaned_results.append({
                            "title": scraped.metadata.title,
                            "url": scraped.metadata.url,
                            "markdown": scraped.markdown
                        })
                    return {
                        "all_links": all_links,
                        "scraped": cleaned_results
                    }
                else:
                    print("No results received")
                    return {"all_links": all_links, "scraped": []}
            
            elif status_response and status_response.status == "failed":
                print("Batch scrape failed")
                return {"all_links": all_links, "scraped": []}
            
            # Wait 10 seconds before checking again (matching n8n workflow)
            time.sleep(10)
        
        print(f"Timeout reached after {max_wait_time} seconds")
        return {"all_links": all_links, "scraped": []}
        
    except Exception as e:
        print(f"Error in crawl_lawfirm_website: {e}")
        return {"all_links": [], "scraped": []}


# Example usage
if __name__ == "__main__":
    # Example law firm URL
    test_url = "https://www.quillarrowlaw.com/"
    result = crawl_lawfirm_website(test_url)

    
    # Write results to a timestamped text file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"crawl_results_{timestamp}.txt"
    
    with open(filename, "w") as f:
        f.write(f"Crawl Results for: {test_url}\n")
        f.write(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n")
        f.write(json.dumps(result, indent=2))
    
    print(f"Results written to: {filename}")
    





