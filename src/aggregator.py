#!/usr/bin/env python3
import asyncio
import os
import sys
import json
from concurrent.futures import ThreadPoolExecutor
from scraper import EventScraper, load_config, save_events_to_db
from dining import enrich_venues_dining

# ThreadPoolExecutor to run blocking Scrapling requests concurrently
executor = ThreadPoolExecutor(max_workers=5)

async def scrape_single_venue_task(venue_cfg):
    venue_name = venue_cfg.get("name")
    print(f"🚀 [AGGREGATOR] Dispatching scraper task for {venue_name}...")
    
    # Run the blocking scrape() function in the executor thread pool
    loop = asyncio.get_running_loop()
    scraper = EventScraper(venue_cfg)
    events = await loop.run_in_executor(executor, scraper.scrape)
    
    return {
        "name": venue_name,
        "category": venue_cfg.get("category"),
        "events": events
    }

async def main_async():
    config = load_config()
    venues = config.get("venues", [])
    
    print("\n=======================================================")
    print(f"🕷️ Starting concurrent crawls for {config.get('city_name')}...")
    print(f"   Venues: {len(venues)} total concurrent crawls")
    print("=======================================================\n")
    
    # Dispatch all scraper tasks concurrently
    tasks = [scrape_single_venue_task(v) for v in venues]
    results = await asyncio.gather(*tasks)
    
    print("\n=======================================================")
    print("💾 Crawls complete. Writing events to database sequentially...")
    print("=======================================================")
    
    # Write to SQLite sequentially to prevent database locks
    for r in results:
        venue_name = r["name"]
        category = r["category"]
        events = r["events"]
        
        if events:
            save_events_to_db(venue_name, category, events)
        else:
            print(f"⚠️ No events found for {venue_name} - skipped saving.")
            
    print("\n=======================================================")
    print("🍔 Starting dining and location enrichment...")
    print("=======================================================")
    enrich_venues_dining()
            
    print("\n🎉 Concurrent aggregation & dining enrichment finished successfully!")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
