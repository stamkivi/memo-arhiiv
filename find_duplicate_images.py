#!/usr/bin/env python3
import os
import re
import hashlib
import logging
from collections import defaultdict
import glob
from pathlib import Path
from config import MARKDOWN_DIR, IMAGES_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def calculate_file_hash(filepath):
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def find_duplicate_images(image_dir):
    """Find duplicate images based on file hash."""
    # Dictionary to store hash -> [file paths]
    hash_dict = defaultdict(list)
    
    # Get all image files
    image_files = []
    for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        image_files.extend(glob.glob(os.path.join(image_dir, f"**/*.{ext}"), recursive=True))
    
    logging.info(f"Found {len(image_files)} images to analyze")
    
    # Calculate hash for each file
    for image_path in image_files:
        try:
            file_hash = calculate_file_hash(image_path)
            hash_dict[file_hash].append(image_path)
        except Exception as e:
            logging.error(f"Error processing {image_path}: {str(e)}")
    
    # Filter to only duplicates
    duplicates = {h: files for h, files in hash_dict.items() if len(files) > 1}
    
    logging.info(f"Found {len(duplicates)} sets of duplicate images")
    return duplicates

def update_markdown_references(markdown_dir, duplicates):
    """Update markdown files to use consistent image paths for duplicates."""
    # For each set of duplicates, decide on a canonical path
    canonical_paths = {}
    for file_hash, file_paths in duplicates.items():
        # Sort paths to ensure consistent selection (use the first one alphabetically)
        sorted_paths = sorted(file_paths)
        canonical_path = sorted_paths[0]
        
        # Map all duplicates to the canonical path
        for path in file_paths:
            canonical_paths[os.path.basename(path)] = os.path.basename(canonical_path)
    
    # Update all markdown files
    markdown_files = glob.glob(os.path.join(markdown_dir, "**/*.md"), recursive=True)
    updated_count = 0
    
    for md_file in markdown_files:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Look for image references in Markdown
        for filename, canonical in canonical_paths.items():
            if filename == canonical:
                continue  # Skip if it's already the canonical path
                
            # Update the reference - match both relative and full paths
            content = re.sub(
                r'!\[.*?\]\((.*?)' + re.escape(filename) + r'\)',
                r'![](images/' + canonical + r')',
                content
            )
        
        # Only write if content changed
        if content != original_content:
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(content)
            updated_count += 1
            logging.info(f"Updated image references in {md_file}")
    
    logging.info(f"Updated {updated_count} markdown files with consistent image references")
    return updated_count

def remove_duplicate_files(duplicates):
    """Remove duplicate image files, keeping only the canonical ones."""
    removed_count = 0
    
    for file_hash, file_paths in duplicates.items():
        # Sort paths to ensure consistent selection (keep the first one alphabetically)
        sorted_paths = sorted(file_paths)
        canonical_path = sorted_paths[0]
        
        # Remove all but the canonical file
        for path in sorted_paths[1:]:
            try:
                os.remove(path)
                removed_count += 1
                logging.info(f"Removed duplicate: {path} (identical to {canonical_path})")
            except Exception as e:
                logging.error(f"Error removing {path}: {str(e)}")
    
    logging.info(f"Removed {removed_count} duplicate image files")
    return removed_count

def main():
    """Main function to find and handle duplicate images."""
    # Create directories if they don't exist
    Path(IMAGES_DIR).mkdir(exist_ok=True, parents=True)
    Path(MARKDOWN_DIR).mkdir(exist_ok=True, parents=True)
    
    logging.info("Starting duplicate image analysis")
    
    # Find duplicates
    duplicates = find_duplicate_images(IMAGES_DIR)
    
    if duplicates:
        # Update markdown references
        updated_files = update_markdown_references(MARKDOWN_DIR, duplicates)
        
        # Remove duplicate files
        removed_files = remove_duplicate_files(duplicates)
        
        logging.info(f"Completed. Updated {updated_files} markdown files and removed {removed_files} duplicate images.")
    else:
        logging.info("No duplicate images found.")

if __name__ == "__main__":
    main() 