#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import re
import time
from pathlib import Path
import subprocess
import json
import glob
from bs4 import BeautifulSoup
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

def run_verification():
    """
    Run the verification script and parse its results.
    Returns a dictionary with the verification results.
    """
    try:
        # Check if verification script exists
        if not os.path.exists('verify_processing.py'):
            logging.error("verify_processing.py not found")
            return None
        
        # Make script executable
        os.chmod('verify_processing.py', 0o755)
        
        # Run verification script
        logging.info("Running verification script...")
        result = subprocess.run(['python3', 'verify_processing.py'], 
                               capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logging.error(f"Verification script failed with exit code {result.returncode}")
            logging.error(f"Error: {result.stderr}")
            return None
        
        # Check if results file exists
        if os.path.exists('verification_results.txt'):
            with open('verification_results.txt', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse results
            results = {}
            
            # Parse missing Smaily memos
            smaily_match = re.search(r'## Missing Smaily Memos\n(.*?)(?=\n\n|\Z)', content, re.DOTALL)
            if smaily_match and smaily_match.group(1).strip() != 'None':
                results['missing_smaily'] = [s.strip() for s in smaily_match.group(1).split(',')]
            else:
                results['missing_smaily'] = []
            
            # Parse missing Substack files
            substack_match = re.search(r'## Missing Substack Files\n(.*?)(?=\n\n|\Z)', content, re.DOTALL)
            if substack_match and substack_match.group(1).strip() != 'None':
                results['missing_substack'] = [
                    line.strip()[2:] for line in substack_match.group(1).split('\n') 
                    if line.strip().startswith('- ')
                ]
            else:
                results['missing_substack'] = []
            
            # Parse missing images
            images_match = re.search(r'## Missing Images\n(.*?)(?=\n\n|\Z)', content, re.DOTALL)
            if images_match and images_match.group(1).strip() != 'None':
                results['missing_images'] = [
                    line.strip()[2:] for line in images_match.group(1).split('\n') 
                    if line.strip().startswith('- ')
                ]
            else:
                results['missing_images'] = []
            
            return results
        else:
            logging.warning("No verification results file found.")
            return None
    except Exception as e:
        logging.error(f"Error running verification: {str(e)}")
        return None

def process_missing_smaily(missing_numbers, process_script='process_smaily.py'):
    """
    Process missing memos from Smaily by running the process script with specific memo numbers.
    """
    if not missing_numbers:
        logging.info("No missing Smaily memos to process")
        return
    
    logging.info(f"Processing {len(missing_numbers)} missing Smaily memos...")
    
    # Check if process script exists
    if not os.path.exists(process_script):
        logging.error(f"{process_script} not found")
        return
    
    # Make script executable
    os.chmod(process_script, 0o755)
    
    # Process each missing memo
    for memo_number in missing_numbers:
        try:
            logging.info(f"Processing Smaily memo {memo_number}...")
            
            # Run process script with memo number filter
            result = subprocess.run(
                ['python3', process_script, '--memo-filter', memo_number],
                capture_output=True, text=True, check=False
            )
            
            if result.returncode != 0:
                logging.error(f"Failed to process Smaily memo {memo_number}")
                logging.error(f"Error: {result.stderr}")
            else:
                logging.info(f"Successfully processed Smaily memo {memo_number}")
                
            # Short pause to avoid overloading servers
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error processing Smaily memo {memo_number}: {str(e)}")

def process_missing_substack(missing_files, process_script='process_substack.py'):
    """
    Process missing HTML files from Substack by running the Substack process script.
    """
    if not missing_files:
        logging.info("No missing Substack files to process")
        return
    
    logging.info(f"Processing {len(missing_files)} missing Substack files...")
    
    # Check if process script exists
    if not os.path.exists(process_script):
        logging.error(f"{process_script} not found")
        return
    
    # Make script executable
    os.chmod(process_script, 0o755)
    
    # Process each missing file
    for html_file in missing_files:
        try:
            if not os.path.exists(html_file):
                logging.warning(f"Substack file not found: {html_file}")
                continue
                
            logging.info(f"Processing Substack file: {html_file}")
            
            # Extract memo number for filtering
            filename = os.path.basename(html_file)
            memo_match = re.search(r'memo-(\d+)', filename)
            memo_filter = memo_match.group(1) if memo_match else None
            
            # Run process script with specific file
            cmd = ['python3', process_script, '--input-file', html_file]
            if memo_filter:
                cmd.extend(['--memo-filter', memo_filter])
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                logging.error(f"Failed to process Substack file: {html_file}")
                logging.error(f"Error: {result.stderr}")
            else:
                logging.info(f"Successfully processed Substack file: {html_file}")
                
            # Short pause to avoid overloading servers
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error processing Substack file {html_file}: {str(e)}")

def fetch_missing_images(missing_images):
    """
    Attempt to fetch missing images referenced in markdown files.
    """
    if not missing_images:
        logging.info("No missing images to fetch")
        return
    
    logging.info(f"Attempting to fetch {len(missing_images)} missing images...")
    
    # Create image directory if it doesn't exist
    Path(IMAGES_DIR).mkdir(exist_ok=True, parents=True)
    
    # Find image URLs in markdown files
    image_urls = {}
    markdown_files = [f for f in Path(MARKDOWN_DIR).glob('**/*.md')]
    
    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for image references with URLs - handle multiple patterns
            for missing_img in missing_images:
                # Standard markdown pattern
                patterns = [
                    # Direct URL to image
                    r'!\[.*?\]\((https?://.*?/' + re.escape(missing_img) + r')\)',
                    # Substack CDN pattern
                    r'!\[.*?\]\((https?://substackcdn\.com/image/fetch/.*?/' + re.escape(missing_img) + r')\)',
                    # Alternative URL formats - more generic pattern
                    r'!\[.*?\]\((https?://[^)]+?[/=]' + re.escape(missing_img) + r'(?:\?[^)]*)?)\)',
                    # Handle cases where the image name is different in the URL
                    r'!\[.*?\]\((https?://[^)]+?)' + r'\).*?' + missing_img
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        image_urls[missing_img] = matches[0]
                        break
        except Exception as e:
            logging.error(f"Error processing markdown file {md_file}: {str(e)}")
    
    # Download missing images
    downloaded_count = 0
    for img_name, url in image_urls.items():
        try:
            output_path = os.path.join(IMAGES_DIR, img_name)
            logging.info(f"Downloading {img_name} from {url}")
            
            # Use curl to download the image
            result = subprocess.run(
                ['curl', '-s', '-L', '-o', output_path, url],
                capture_output=True, text=True, check=False
            )
            
            if result.returncode != 0:
                logging.error(f"Failed to download image {img_name}")
                logging.error(f"Error: {result.stderr}")
            else:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logging.info(f"Successfully downloaded {img_name}")
                    downloaded_count += 1
                else:
                    logging.warning(f"Downloaded file {img_name} is empty or invalid")
            
            # Short pause to avoid overloading servers
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error downloading image {img_name}: {str(e)}")
    
    logging.info(f"Successfully downloaded {downloaded_count} of {len(missing_images)} missing images")

def main():
    """Main function to process missing files."""
    parser = argparse.ArgumentParser(description='Process missing files identified by verification')
    parser.add_argument('--smaily-script', default='process_smaily.py', help='Path to Smaily processing script')
    parser.add_argument('--substack-script', default='process_substack.py', help='Path to Substack processing script')
    parser.add_argument('--only', choices=['smaily', 'substack', 'images'], help='Only process specific type of missing files')
    args = parser.parse_args()
    
    # Run verification first
    verification_results = run_verification()
    if not verification_results:
        logging.error("Verification failed or returned no results")
        sys.exit(1)
    
    # Process missing files based on verification results
    if not args.only or args.only == 'smaily':
        process_missing_smaily(verification_results['missing_smaily'], args.smaily_script)
    
    if not args.only or args.only == 'substack':
        process_missing_substack(verification_results['missing_substack'], args.substack_script)
    
    if not args.only or args.only == 'images':
        fetch_missing_images(verification_results['missing_images'])
    
    # Run verification again to check if we fixed everything
    final_results = run_verification()
    if final_results:
        remaining_count = (
            len(final_results['missing_smaily']) +
            len(final_results['missing_substack']) +
            len(final_results['missing_images'])
        )
        if remaining_count > 0:
            logging.warning(f"There are still {remaining_count} missing items after processing")
            logging.warning(f"Missing Smaily: {len(final_results['missing_smaily'])}")
            logging.warning(f"Missing Substack: {len(final_results['missing_substack'])}")
            logging.warning(f"Missing Images: {len(final_results['missing_images'])}")
        else:
            logging.info("All missing items have been processed successfully")
    else:
        logging.error("Final verification failed")

if __name__ == "__main__":
    main() 