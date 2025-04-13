#!/usr/bin/env python3
import pandas as pd
import requests
from bs4 import BeautifulSoup
import html2text
import os
import re
from datetime import datetime
import time
import logging
from pathlib import Path
import csv
from config import SMAILY_SOURCE_DIR, MARKDOWN_DIR, IMAGES_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def clean_filename(title):
    """Convert title to a safe filename."""
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s-]', '', title)
    filename = re.sub(r'[-\s]+', '-', filename).strip('-')
    return filename.lower()

def extract_memo_number(title):
    """Extract Memo number from title."""
    match = re.search(r'Memo #(\d+)', title)
    return match.group(1) if match else ''

def format_metadata(row):
    """Format metadata for the markdown file."""
    memo_number = extract_memo_number(row['Section name'])
    title = row['Section name'].replace(f'Memo #{memo_number}: ', '')
    date = datetime.strptime(row['Due at'], '%Y-%m-%d %H:%M:%S')
    
    metadata = f"---\n"
    metadata += f"title: {title}\n"
    metadata += f"memo_number: {memo_number}\n"
    metadata += f"date: {date.strftime('%Y-%m-%d')}\n"
    metadata += f"time: {date.strftime('%H:%M')}\n"
    metadata += f"deliveries: {row['Deliveries']}\n"
    metadata += f"---\n\n"
    
    return metadata

def clean_markdown(content):
    """Clean up the markdown content."""
    # Remove header about viewing email in browser
    content = re.sub(r'\|.*?Kui Sa seda kirja korralikult ei näe.*?\n', '', content)
    
    # Remove unnecessary table markers and horizontal rules
    content = re.sub(r'\|(?:\s*\|)+\s*\n', '', content)
    content = re.sub(r'^\s*[-\s|]+$\n', '', content, flags=re.MULTILINE)
    
    # Process content line by line with a simpler, more direct approach
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for MEMO image (main title)
        if '![](http' in line and 'screenshot.1554656709.png' in line:
            result.append('# MEMO')
            result.append('')
            i += 1
            continue
            
        # Check for section 1 image
        if '![](http' in line and 'screenshot(1)' in line:
            # Add section heading
            result.append('## 1')
            result.append('')
            
            # Skip this line and possible continuation lines
            i += 1
            while i < len(lines) and (lines[i].strip() == '' or '.png' in lines[i]):
                i += 1
            continue
                
        # Check for section 2 image
        if '![](http' in line and 'screenshot(2)' in line:
            # Add section heading
            result.append('## 2')
            result.append('')
            
            # Skip this line and possible continuation lines
            i += 1
            while i < len(lines) and (lines[i].strip() == '' or '.png' in lines[i] or '.1557680846.png' in lines[i]):
                i += 1
            continue
                
        # Check for section 3 image
        if '![](http' in line and 'screenshot(3)' in line:
            # Add section heading
            result.append('## 3')
            result.append('')
            
            # Skip this line and possible continuation lines
            i += 1
            while i < len(lines) and (lines[i].strip() == '' or '.png' in lines[i]):
                i += 1
            continue
                
        # Skip image continuation lines
        if (line.strip().startswith('.png') or 
            line.strip().startswith('.1557680846.png') or 
            line.strip() == '' and i > 0 and 'screenshot' in lines[i-1]):
            i += 1
            continue
            
        # Keep all other lines
        result.append(line)
        i += 1
    
    content = '\n'.join(result)
    
    # Remove tracking pixels and spacer images
    content = re.sub(r'!\[\]\(.*?spacer\.gif.*?\)\n', '', content)
    
    # Remove any remaining image patterns for sections 1, 2, 3
    content = re.sub(r'!\[\].*?screenshot\(1\).*?\n.*?\.png.*?\)', '', content, flags=re.DOTALL)
    content = re.sub(r'!\[\].*?screenshot\(2\).*?\n.*?\.png.*?\)', '', content, flags=re.DOTALL)
    content = re.sub(r'!\[\].*?screenshot\(3\).*?\n.*?\.png.*?\)', '', content, flags=re.DOTALL)
    
    # Remove footer links and unsubscribe text
    content = re.sub(r'Memo saajate hulgast lahkumiseks.*', '', content, flags=re.DOTALL)
    content = re.sub(r'PS: Varasemate Memode arhiiv.*', '', content, flags=re.DOTALL)
    content = re.sub(r'\[smaily\].*', '', content, flags=re.DOTALL)
    
    # Clean up any remaining table markers at start of lines
    content = re.sub(r'^\s*\|.*?\|\s*', '', content, flags=re.MULTILINE)
    
    # Add proper spacing around remaining images
    content = re.sub(r'(!\[.*?\].*?\))\s*([^\n])', r'\1\n\n\2', content)
    
    # Clean up multiple consecutive subheadings
    content = re.sub(r'#{2,}\s*#{2,}\s*', '## ', content)
    
    # Clean up empty subheadings
    content = re.sub(r'#{2,}\s*\n', '', content)
    
    # Final cleanup of any remaining screenshot images
    content = re.sub(r'!\[\]\(.*?screenshot\(1\).*?\)', '## 1\n\n', content, flags=re.DOTALL)
    content = re.sub(r'!\[\]\(.*?screenshot\(2\).*?\)', '## 2\n\n', content, flags=re.DOTALL)
    content = re.sub(r'!\[\]\(.*?screenshot\(3\).*?\)', '## 3\n\n', content, flags=re.DOTALL)
    
    return content.strip()

def download_and_convert(row):
    """Download HTML content, convert to markdown, and save to file."""
    title = row['title']
    url = row['url']
    
    # Clean the title for use as filename
    safe_title = clean_filename(title)
    memo_number = extract_memo_number(title)
    
    # Create output filename
    output_filename = f"memo-{memo_number}.md"
    output_path = os.path.join(MARKDOWN_DIR, output_filename)
    
    # Skip if file already exists
    if os.path.exists(output_path):
        logging.info(f"Skipping {output_filename} - already exists")
        return True
    
    try:
        # Download HTML content with retry logic
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == max_retries - 1:  # Last attempt
                    logging.error(f"Failed to download {url} after {max_retries} attempts: {str(e)}")
                    return False
                logging.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Convert to markdown
        h = html2text.HTML2Text()
        h.body_width = 0  # Disable line wrapping
        markdown_content = h.handle(str(soup))
        
        # Clean up markdown content
        markdown_content = clean_markdown(markdown_content)
        
        # Add metadata at the top
        metadata = format_metadata(row)
        final_content = f"{metadata}\n\n{markdown_content}"
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        logging.info(f"Successfully processed {output_filename}")
        
        # Be polite to the server
        time.sleep(1)
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing {title}: {str(e)}")
        return False

def main():
    """Main function to process memos."""
    csv_path = os.path.join(SMAILY_SOURCE_DIR, "campaigns-2025-04-13.csv")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        logging.info(f"Found {len(rows)} memos to process")
        
        success_count = 0
        for row in rows:
            if download_and_convert(row):
                success_count += 1
        
        logging.info(f"Successfully processed {success_count} of {len(rows)} memos")
        
    except Exception as e:
        logging.error(f"Error reading CSV file: {str(e)}")

if __name__ == "__main__":
    main() 