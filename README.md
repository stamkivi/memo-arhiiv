# Memo Archive Processing Scripts

A collection of Python scripts for processing and managing Memo archives from different sources.

To use, provide the following inputs
1) source/smaily - save the posts CSV file from Smaily (old memos), and the script auto-downloads all the post contents from web.
2) source/substack - export the HTML posts + metadata from Subsctack

## Scripts Overview

### Main Processing Scripts

- `process_smaily.py`: Processes memos from Smaily email campaigns, converting them to markdown format.
- `process_substack.py`: Converts Substack newsletter HTML files to markdown format.

### Verification and Recovery

- `verify_processing.py`: Checks for any missing memos, files, or images across the archive.
- `process_missing_files.py`: Automatically recovers missing content identified by the verification script.

## When to Run Each Script

1. Run `process_smaily.py` and `process_substack.py` first to process new content.
2. Run `verify_processing.py` to check if any content is missing.
3. If verification finds issues, run `process_missing_files.py` to recover the missing content.

## Usage Example

```bash
# Process new content
python3 process_smaily.py
python3 process_substack.py

# Verify everything is processed
python3 verify_processing.py

# If needed, recover missing content
python3 process_missing_files.py
```

You can also process specific types of missing content:
```bash
python3 process_missing_files.py --only smaily    # Only process missing Smaily memos
python3 process_missing_files.py --only substack  # Only process missing Substack files
python3 process_missing_files.py --only images    # Only download missing images
```