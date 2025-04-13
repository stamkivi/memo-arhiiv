#!/usr/bin/env python3
import os
import csv
import logging
from pathlib import Path
from config import SUBSTACK_SOURCE_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def count_deliveries(csv_path):
    """Count the number of deliveries in a CSV file, excluding header."""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip header and count remaining lines
            reader = csv.reader(f)
            next(reader)  # Skip header
            return sum(1 for _ in reader)
    except Exception as e:
        logging.error(f"Error reading {csv_path}: {str(e)}")
        return 0

def find_delivery_files():
    """Find all .delivers.csv files in the Substack posts directory."""
    posts_dir = os.path.join(SUBSTACK_SOURCE_DIR, "posts")
    delivery_files = []
    
    for root, _, files in os.walk(posts_dir):
        for file in files:
            if file.endswith('.delivers.csv'):
                full_path = os.path.join(root, file)
                delivery_files.append(full_path)
    
    return delivery_files

def main():
    """Main function to count deliveries for all Substack memos."""
    logging.info("Starting delivery count analysis")
    
    # Find all delivery CSV files
    delivery_files = find_delivery_files()
    logging.info(f"Found {len(delivery_files)} delivery CSV files")
    
    # Process each file
    results = []
    for csv_path in delivery_files:
        # Extract memo ID from filename
        memo_id = os.path.basename(csv_path).split('.')[0]
        deliveries = count_deliveries(csv_path)
        results.append((memo_id, deliveries))
    
    # Sort results by memo ID
    results.sort(key=lambda x: int(x[0]))
    
    # Print results
    print("\nDelivery Counts:")
    print("Memo ID | Deliveries")
    print("--------|-----------")
    for memo_id, deliveries in results:
        print(f"{memo_id:7} | {deliveries:9}")
    
    # Print summary
    total_deliveries = sum(deliveries for _, deliveries in results)
    print(f"\nTotal memos: {len(results)}")
    print(f"Total deliveries: {total_deliveries}")
    print(f"Average deliveries per memo: {total_deliveries/len(results):.1f}")

if __name__ == "__main__":
    main() 