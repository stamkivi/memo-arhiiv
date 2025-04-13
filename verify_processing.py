#!/usr/bin/env python3
import os
import csv
import re
import logging
import glob
from pathlib import Path
import argparse
from config import (
    SOURCE_DIR,
    CONTENT_DIR,
    SMAILY_SOURCE_DIR,
    SUBSTACK_SOURCE_DIR,
    MARKDOWN_DIR,
    IMAGES_DIR
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def check_smaily_processing(csv_file):
    """
    Verify that all memos from the Smaily CSV have corresponding markdown files.
    Returns a list of missing memo numbers.
    """
    if not os.path.exists(csv_file):
        logging.error(f"CSV file {csv_file} not found")
        return []
    
    # Extract all memo numbers from the CSV
    csv_memo_numbers = set()
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get('title', '')
                memo_match = re.search(r'memo[- ](\d+)', title, re.IGNORECASE)
                if memo_match:
                    memo_number = memo_match.group(1)
                    csv_memo_numbers.add(memo_number)
    except Exception as e:
        logging.error(f"Error reading CSV file: {str(e)}")
        return []
    
    logging.info(f"Found {len(csv_memo_numbers)} memo numbers in CSV")
    
    # Get all markdown files
    markdown_files = glob.glob(os.path.join(MARKDOWN_DIR, "*.md"))
    
    # Extract memo numbers from markdown filenames
    markdown_memo_numbers = set()
    for md_file in markdown_files:
        filename = os.path.basename(md_file)
        memo_match = re.search(r'memo-(\d+)', filename)
        if memo_match:
            memo_number = memo_match.group(1)
            markdown_memo_numbers.add(memo_number)
    
    logging.info(f"Found {len(markdown_memo_numbers)} memo markdown files")
    
    # Find missing memo numbers
    missing_memo_numbers = csv_memo_numbers - markdown_memo_numbers
    return sorted(list(missing_memo_numbers), key=int)

def check_substack_processing():
    """
    Verify that all HTML files from Substack have corresponding markdown files.
    Returns a list of missing HTML files.
    """
    if not os.path.exists(SUBSTACK_SOURCE_DIR):
        logging.error(f"Substack directory {SUBSTACK_SOURCE_DIR} not found")
        return []
    
    # Get all HTML files
    html_files = glob.glob(os.path.join(SUBSTACK_SOURCE_DIR, "**/*.html"), recursive=True)
    
    # Extract memo numbers from HTML filenames
    html_memo_numbers = set()
    html_memo_map = {}  # Map memo numbers to full HTML files
    for html_file in html_files:
        filename = os.path.basename(html_file)
        # Updated pattern to handle numeric prefix
        memo_match = re.search(r'\d+\.memo-(\d+)', filename)
        if memo_match:
            memo_number = memo_match.group(1)
            html_memo_numbers.add(memo_number)
            html_memo_map[memo_number] = html_file
    
    logging.info(f"Found {len(html_memo_numbers)} memo numbers in Substack HTML files")
    
    # Get all markdown files
    markdown_files = glob.glob(os.path.join(MARKDOWN_DIR, "*.md"))
    
    # Extract memo numbers from markdown filenames
    markdown_memo_numbers = set()
    for md_file in markdown_files:
        filename = os.path.basename(md_file)
        memo_match = re.search(r'memo-(\d+)', filename)
        if memo_match:
            memo_number = memo_match.group(1)
            markdown_memo_numbers.add(memo_number)
    
    logging.info(f"Found {len(markdown_memo_numbers)} memo markdown files")
    
    # Find missing memo numbers
    missing_memo_numbers = html_memo_numbers - markdown_memo_numbers
    
    # Get the full HTML filenames that were missed
    missing_html_files = [html_memo_map[memo_num] for memo_num in missing_memo_numbers]
    
    return sorted(missing_html_files)

def check_image_references():
    """
    Check if all images referenced in markdown files exist in the image directory.
    Returns a list of missing image files.
    """
    # Get all markdown files
    markdown_files = glob.glob(os.path.join(MARKDOWN_DIR, "**/*.md"), recursive=True)
    
    # Find all image references in markdown files
    referenced_images = set()
    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract image references from markdown
            image_refs = re.findall(r'!\[.*?\]\((.*?)\)', content)
            for ref in image_refs:
                # Get just the filename part if it's a path
                image_name = os.path.basename(ref)
                referenced_images.add(image_name)
        except Exception as e:
            logging.error(f"Error processing {md_file}: {str(e)}")
    
    logging.info(f"Found {len(referenced_images)} unique image references in markdown files")
    
    # Get all image files in the image directory
    existing_images = set()
    for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        for image_path in glob.glob(os.path.join(IMAGES_DIR, f"**/*.{ext}"), recursive=True):
            image_name = os.path.basename(image_path)
            existing_images.add(image_name)
    
    logging.info(f"Found {len(existing_images)} images in the image directory")
    
    # Find missing images
    missing_images = referenced_images - existing_images
    return sorted(list(missing_images))

def main():
    """Main function to verify processing of files."""
    parser = argparse.ArgumentParser(description='Verify memo processing and find missing files')
    parser.add_argument('--csv', default=os.path.join(SMAILY_SOURCE_DIR, 'campaigns-2025-04-13.csv'), 
                       help='Path to Smaily CSV file')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    Path(MARKDOWN_DIR).mkdir(exist_ok=True, parents=True)
    
    logging.info("Starting verification process")
    
    # Check Smaily processing
    logging.info("Checking Smaily processing...")
    missing_smaily = check_smaily_processing(args.csv)
    if missing_smaily:
        logging.warning(f"Found {len(missing_smaily)} missing memos from Smaily: {', '.join(missing_smaily)}")
    else:
        logging.info("All Smaily memos have been processed successfully")
    
    # Check Substack processing
    logging.info("Checking Substack processing...")
    missing_substack = check_substack_processing()
    if missing_substack:
        logging.warning(f"Found {len(missing_substack)} missing HTML files from Substack:")
        for html_file in missing_substack:
            logging.warning(f"  - {html_file}")
    else:
        logging.info("All Substack HTML files have been processed successfully")
    
    # Check image references
    logging.info("Checking image references...")
    missing_images = check_image_references()
    if missing_images:
        logging.warning(f"Found {len(missing_images)} missing images referenced in markdown files:")
        for image in missing_images:
            logging.warning(f"  - {image}")
    else:
        logging.info("All image references in markdown files exist")
    
    # Overall summary
    if not missing_smaily and not missing_substack and not missing_images:
        logging.info("Verification complete - all files have been processed correctly!")
    else:
        logging.warning("Verification complete - issues were found. Please check the logs for details.")
        
        # Create a summary file
        summary_file = "verification_results.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# Verification Results\n\n")
            
            f.write("## Missing Smaily Memos\n")
            if missing_smaily:
                f.write(", ".join(missing_smaily) + "\n")
            else:
                f.write("None\n")
            
            f.write("\n## Missing Substack Files\n")
            if missing_substack:
                for html_file in missing_substack:
                    f.write(f"- {html_file}\n")
            else:
                f.write("None\n")
            
            f.write("\n## Missing Images\n")
            if missing_images:
                for image in missing_images:
                    f.write(f"- {image}\n")
            else:
                f.write("None\n")
        
        logging.info(f"Summary written to {summary_file}")

if __name__ == "__main__":
    main() 