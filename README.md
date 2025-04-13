# Memo Archive Analysis Tool

This tool analyzes and processes memo archives, providing insights and visualizations of the content.


To use, provide the following inputs
1) source/smaily - save the posts CSV file from Smaily (old memos), and the script auto-downloads all the post contents from web.
2) source/substack - export the HTML posts + metadata from Subsctack

## Features

- Analyzes Memo content and structure
- Generates visualizations of memo patterns
- Processes and categorizes memo data
- Creates word clouds and sentiment analysis
- Support scripts for:
  - Substack content processing (`process_substack.py`)
  - Delivery statistics (`count_substack_deliveries.py`)
  - Image deduplication (`find_duplicate_images.py`)
  - Processing verification (`verify_processing.py`)
  - Missing file handling (`process_missing_files.py`)
  - Smaily campaign processing (`process_smaily.py`)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the analysis script:
```bash
python analyze_memos.py
```

## Configuration

The tool uses a `config.py` file for configuration. Create this file based on your needs.

## Data Privacy

This tool is designed to handle sensitive data. Make sure to:
- Never commit sensitive data to the repository
- Use appropriate .gitignore rules
- Handle personal information according to privacy regulations

## License

MIT License