#!/usr/bin/env python3
"""
Quina Lottery Results Fetcher
Scrapes winning numbers from megasena.com and updates the results.json file.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Configuration
QUINA_URL = "https://megasena.com/en/quina/results"
DATA_FILE = Path(__file__).parent.parent / "data" / "results.json"
MAX_RESULTS = 30  # Keep last 30 results


def fetch_quina_results():
    """Fetch Quina results from megasena.com"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        response = requests.get(QUINA_URL, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")
        return None


def parse_results(html_content):
    """Parse the HTML to extract lottery results"""
    soup = BeautifulSoup(html_content, "html.parser")
    results = []
    
    # Find all result tables (latest and previous)
    tables = soup.find_all("table", class_=re.compile(r"results.*archive.*quina", re.IGNORECASE))
    
    if not tables:
        # Try alternative selectors
        tables = soup.find_all("table")
    
    for table in tables:
        rows = table.find_all("tr")
        
        for row in rows:
            result = parse_result_row(row)
            if result:
                results.append(result)
    
    # Also try to parse individual result cards/divs
    result_divs = soup.find_all("div", class_=re.compile(r"result|draw", re.IGNORECASE))
    
    for div in result_divs:
        result = parse_result_div(div)
        if result and result not in results:
            # Check if this draw number already exists
            existing_numbers = [r["drawNumber"] for r in results]
            if result["drawNumber"] not in existing_numbers:
                results.append(result)
    
    return results


def parse_result_row(row):
    """Parse a table row for lottery result"""
    try:
        # Find draw number
        draw_text = row.get_text()
        draw_match = re.search(r"Draw\s*(?:Number)?:?\s*(\d{4,})", draw_text, re.IGNORECASE)
        
        if not draw_match:
            return None
            
        draw_number = int(draw_match.group(1))
        
        # Find numbers (lottery balls)
        numbers = []
        
        # Try to find balls in list items
        balls = row.find_all("li", class_=re.compile(r"ball", re.IGNORECASE))
        if balls:
            for ball in balls:
                num_text = ball.get_text().strip()
                if num_text.isdigit():
                    numbers.append(int(num_text))
        
        # If no balls found, try to find numbers in spans or divs
        if not numbers:
            num_elements = row.find_all(["span", "div"], class_=re.compile(r"number|ball", re.IGNORECASE))
            for elem in num_elements:
                num_text = elem.get_text().strip()
                if num_text.isdigit() and 1 <= int(num_text) <= 80:
                    numbers.append(int(num_text))
        
        if len(numbers) != 5:
            return None
        
        # Find date
        date_match = re.search(r"(\d{1,2})\s*(?:st|nd|rd|th)?\s*(\w+)\s*(\d{4})", draw_text)
        if date_match:
            day, month, year = date_match.groups()
            date_str = f"{day} {month} {year}"
            try:
                date_obj = datetime.strptime(date_str, "%d %B %Y")
                date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                date = datetime.now().strftime("%Y-%m-%d")
        else:
            date = datetime.now().strftime("%Y-%m-%d")
        
        return {
            "drawNumber": draw_number,
            "date": date,
            "numbers": sorted(numbers)
        }
        
    except Exception as e:
        print(f"Error parsing row: {e}")
        return None


def parse_result_div(div):
    """Parse a div element for lottery result"""
    try:
        text = div.get_text()
        
        # Find draw number
        draw_match = re.search(r"Draw\s*(?:Number)?:?\s*(\d{4,})", text, re.IGNORECASE)
        if not draw_match:
            draw_match = re.search(r"#?(\d{4,})", text)
        
        if not draw_match:
            return None
            
        draw_number = int(draw_match.group(1))
        
        # Find numbers
        numbers = []
        balls = div.find_all(["li", "span", "div"], class_=re.compile(r"ball|number", re.IGNORECASE))
        
        for ball in balls:
            num_text = ball.get_text().strip()
            if num_text.isdigit():
                num = int(num_text)
                if 1 <= num <= 80 and num not in numbers:
                    numbers.append(num)
        
        if len(numbers) != 5:
            return None
        
        # Find date
        date_match = re.search(r"(\d{1,2})\s*(?:st|nd|rd|th)?\s*(\w+)\s*(\d{4})", text)
        if date_match:
            day, month, year = date_match.groups()
            date_str = f"{day} {month} {year}"
            try:
                date_obj = datetime.strptime(date_str, "%d %B %Y")
                date = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                date = datetime.now().strftime("%Y-%m-%d")
        else:
            date = datetime.now().strftime("%Y-%m-%d")
        
        return {
            "drawNumber": draw_number,
            "date": date,
            "numbers": sorted(numbers)
        }
        
    except Exception as e:
        print(f"Error parsing div: {e}")
        return None


def load_existing_data():
    """Load existing results from JSON file"""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading existing data: {e}")
    
    return {
        "lastUpdated": None,
        "source": "megasena.com",
        "results": []
    }


def merge_results(existing_results, new_results):
    """Merge new results with existing ones, avoiding duplicates"""
    existing_draws = {r["drawNumber"]: r for r in existing_results}
    
    for result in new_results:
        draw_num = result["drawNumber"]
        if draw_num not in existing_draws:
            existing_draws[draw_num] = result
        else:
            # Update if numbers are different (correction)
            if existing_draws[draw_num]["numbers"] != result["numbers"]:
                existing_draws[draw_num] = result
    
    # Sort by draw number descending and limit
    merged = sorted(existing_draws.values(), key=lambda x: x["drawNumber"], reverse=True)
    return merged[:MAX_RESULTS]


def save_results(data):
    """Save results to JSON file"""
    # Ensure directory exists
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(data['results'])} results to {DATA_FILE}")


def main():
    """Main function"""
    print("=" * 50)
    print("Quina Results Fetcher")
    print("=" * 50)
    print(f"Fetching results from: {QUINA_URL}")
    
    # Fetch HTML
    html_content = fetch_quina_results()
    
    if not html_content:
        print("Failed to fetch page content")
        sys.exit(1)
    
    print(f"Fetched {len(html_content)} bytes of HTML")
    
    # Parse results
    new_results = parse_results(html_content)
    print(f"Parsed {len(new_results)} results from page")
    
    # Load existing data
    existing_data = load_existing_data()
    existing_results = existing_data.get("results", [])
    print(f"Loaded {len(existing_results)} existing results")
    
    # Merge results
    merged_results = merge_results(existing_results, new_results)
    
    # Check if there are any changes
    old_draws = set(r["drawNumber"] for r in existing_results)
    new_draws = set(r["drawNumber"] for r in merged_results)
    added_draws = new_draws - old_draws
    
    if added_draws:
        print(f"New draws added: {sorted(added_draws, reverse=True)}")
    else:
        print("No new draws found")
    
    # Update data
    data = {
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "source": "megasena.com",
        "results": merged_results
    }
    
    # Save results
    save_results(data)
    
    # Print latest result
    if merged_results:
        latest = merged_results[0]
        print(f"\nLatest Result:")
        print(f"  Draw #{latest['drawNumber']} ({latest['date']})")
        print(f"  Numbers: {latest['numbers']}")
    
    print("\n✅ Fetch completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

