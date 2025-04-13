#!/usr/bin/env python3
import os
import re
import logging
import glob
import csv
from pathlib import Path
from bs4 import BeautifulSoup
import html2text
from datetime import datetime
import pandas as pd
from config import SUBSTACK_SOURCE_DIR, MARKDOWN_DIR, IMAGES_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def clean_filename(title):
    """Create a safe filename from title."""
    return re.sub(r'[^\w\s-]', '', title).strip().lower().replace(' ', '-')

def extract_memo_number(title):
    """Extract memo number from title using regex."""
    match = re.search(r'memo[- ](\d+)', title.lower())
    if match:
        return match.group(1)
    return None

def count_deliveries(memo_id):
    """Count the number of deliveries for a memo from its CSV file."""
    csv_path = os.path.join(SUBSTACK_SOURCE_DIR, "posts", f"{memo_id}.delivers.csv")
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            return sum(1 for _ in reader)
    except Exception as e:
        logging.warning(f"Could not read deliveries for memo {memo_id}: {str(e)}")
        return "0"

def get_substack_send_date(memo_id):
    """Get the correct send date from Substack posts.csv for a given memo ID."""
    try:
        posts_df = pd.read_csv(os.path.join(SUBSTACK_SOURCE_DIR, 'posts.csv'))
        memo_row = posts_df[posts_df['post_id'].str.startswith(memo_id, na=False)]
        if not memo_row.empty:
            date_str = memo_row['email_sent_at'].iloc[0]
            if pd.notna(date_str):
                # Convert ISO format to date and time
                dt = datetime.strptime(date_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                return dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M')
    except Exception as e:
        logging.warning(f"Could not get send date for memo {memo_id}: {str(e)}")
    return None, None

def format_metadata(title, memo_number, date, time="12:44", memo_id=None):
    """Format metadata for markdown files."""
    deliveries = count_deliveries(memo_id) if memo_id else "0"
    
    # Get correct send date from Substack if available
    if memo_id:
        send_date, send_time = get_substack_send_date(memo_id)
        if send_date:
            date = send_date
            time = send_time
    
    return f"""---
title: "{title}"
memo_number: {memo_number}
date: {date}
time: {time}
deliveries: {deliveries}
---

"""

def clean_markdown(content):
    """Clean up markdown content."""
    # Remove unnecessary elements
    content = re.sub(r'<div><hr></div>', '', content)
    content = re.sub(r'<p><em>Kui Sul tekkis kiire vastulause.*?</em></p>', '', content, flags=re.DOTALL)
    content = re.sub(r'<p><em>Memo on iganädalane kiri.*?</em></p>', '', content, flags=re.DOTALL)
    
    # Process section headers
    content = re.sub(r'<h1>MEMO</h1>', '# MEMO\n\n', content)
    content = re.sub(r'<h1>1\.</h1>', '## 1\n\n', content)
    content = re.sub(r'<h1>2\.</h1>', '## 2\n\n', content)
    content = re.sub(r'<h1>3\.</h1>', '## 3\n\n', content)
    
    # Clean up remaining HTML
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    h.ignore_images = False
    h.protect_links = True
    h.unicode_snob = True
    h.mark_code = True
    content = h.handle(content)
    
    # Final cleanup
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()
    
    return content

def process_html_file(file_path, output_dir):
    """Process a single HTML file into markdown."""
    try:
        # Extract filename and memo number from file path
        filename = os.path.basename(file_path)
        filename_match = re.search(r'(\d+)\.memo-(\d+)', filename)
        
        if filename_match:
            memo_id = filename_match.group(1)
            memo_number = filename_match.group(2)
        else:
            # Alternative pattern for different naming conventions
            memo_match = re.search(r'memo-(\d+)', filename)
            if memo_match:
                memo_number = memo_match.group(1)
                memo_id = None
            else:
                logging.warning(f"Could not extract memo number from {filename}")
                memo_number = "unknown"
                memo_id = None
        
        # Read HTML content
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # First, try to extract title from the CSV file metadata if available
        title = None
        csv_path = os.path.join(SUBSTACK_SOURCE_DIR, "posts.csv")
        if os.path.exists(csv_path):
            try:
                memo_id_match = re.search(r'(\d+)\.memo-', filename)
                if memo_id_match:
                    memo_id = memo_id_match.group(1)
                    with open(csv_path, 'r', encoding='utf-8') as csvfile:
                        csv_content = csvfile.read()
                        # Look for the title in CSV line starting with memo ID
                        csv_line_match = re.search(rf'{memo_id}\.memo-{memo_number}[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,([^,]*),', csv_content)
                        if csv_line_match and csv_line_match.group(1) and csv_line_match.group(1) != "":
                            title = csv_line_match.group(1).replace('Memo #' + memo_number + ':', '').strip()
            except Exception as e:
                logging.warning(f"Error extracting title from CSV: {str(e)}")
        
        # If no title from CSV, try to find an h1 element that's not "MEMO", a number, or "TEADETETAHVEL"
        if not title:
            for h1 in soup.find_all('h1'):
                h1_text = h1.text.strip()
                if h1_text not in ["MEMO", "1.", "2.", "3.", "TEADETETAHVEL", "TEADETETAHVEL:"]:
                    title = h1_text
                    break
        
        # If still no title, try to derive from filename
        if not title:
            title_match = re.search(r'memo-(\d+)-(.*?)\.html', filename)
            if title_match:
                title = title_match.group(2).replace('-', ' ').title()
            else:
                # Extract from filename directly for older naming pattern
                name_parts = filename.split('.')
                if len(name_parts) > 1 and 'memo-' in name_parts[1]:
                    title_parts = name_parts[1].split('-')[2:]
                    if title_parts:
                        title = ' '.join(title_parts).title()
                    else:
                        title = f"Memo {memo_number}"
                else:
                    title = f"Memo {memo_number}"
        
        # Extract date from filename or use file modification time
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            date = date_match.group(1)
        else:
            # Use file modification time
            mtime = os.path.getmtime(file_path)
            date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        
        # Clean the markdown content
        markdown_content = clean_markdown(str(soup))
        
        # Ensure we have some content (not just headers)
        if len(markdown_content.strip()) < 10:
            # Try to extract content directly from paragraphs
            paragraphs = []
            for p in soup.find_all('p'):
                paragraphs.append(p.get_text())
            
            if paragraphs:
                markdown_content = "\n\n".join(paragraphs)
        
        # Format metadata
        metadata = format_metadata(title, memo_number, date, memo_id=memo_id)
        
        # Combine metadata and content
        full_content = metadata + markdown_content
        
        # Create output file
        output_file = os.path.join(output_dir, f"memo-{memo_number}.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        logging.info(f"Processed {output_file}")
        return True
    
    except Exception as e:
        logging.error(f"Error processing {file_path}: {str(e)}")
        # If we have a memo number, save error info
        if 'memo_number' in locals():
            error_file = os.path.join(output_dir, f"memo-{memo_number}.error")
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(f"Error processing {file_path}: {str(e)}")
        return False

def process_substack_html(input_dir=SUBSTACK_SOURCE_DIR, output_dir=MARKDOWN_DIR):
    """Process all HTML files in input_dir and save markdown to output_dir."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all HTML files
    html_files = glob.glob(os.path.join(input_dir, '**', '*.html'), recursive=True)
    logging.info(f"Found {len(html_files)} HTML files to process")
    
    # Process each file
    success_count = 0
    for file_path in html_files:
        if process_html_file(file_path, output_dir):
            success_count += 1
    
    logging.info(f"Successfully processed {success_count} of {len(html_files)} files")
    return success_count

def main():
    """Main function to process Substack HTML files."""
    logging.info("Starting processing of Substack HTML files")
    processed_count = process_substack_html()
    logging.info(f"Completed processing. {processed_count} files processed.")

if __name__ == "__main__":
    main()
