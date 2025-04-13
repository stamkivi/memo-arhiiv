import os
import re
from collections import Counter, defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from wordcloud import WordCloud, STOPWORDS
import yaml
import numpy as np
from textblob import TextBlob
import seaborn as sns
from config import SOURCE_DIR, CONTENT_DIR
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Custom stopwords to exclude from wordcloud
CUSTOM_STOPWORDS = {
    'https', 'amazonaws', 's3', 'ja', 'et', 'aga', 'com', 'www', 'http', 'html', 'png', 'jpg', 'jpeg',
    'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', 'txt', 'csv', 'json',
    'xml', 'php', 'asp', 'aspx', 'jsp', 'js', 'css', 'htm', 'html', 'svg', 'ico', 'webp', 'mp4',
    'webm', 'ogg', 'mp3', 'wav', 'aac', 'flac', 'm4a', 'wma', 'mov', 'avi', 'mkv', 'flv', 'swf',
    'exe', 'dll', 'sys', 'bat', 'cmd', 'ps1', 'sh', 'bash', 'py', 'java', 'class', 'jar', 'war',
    'ear', 'apk', 'ipa', 'deb', 'rpm', 'msi', 'dmg', 'pkg', 'app', 'exe', 'dll', 'sys', 'bat',
    'cmd', 'ps1', 'sh', 'bash', 'py', 'java', 'class', 'jar', 'war', 'ear', 'apk', 'ipa', 'deb',
    'rpm', 'msi', 'dmg', 'pkg', 'app'
}

def parse_markdown_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split frontmatter and content
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not frontmatter_match:
        return None
    
    # Clean up the frontmatter by removing problematic quotes
    frontmatter_text = frontmatter_match.group(1)
    frontmatter_text = re.sub(r'""', '"', frontmatter_text)  # Fix double quotes
    frontmatter_text = re.sub(r'^title: ""', 'title: "', frontmatter_text, flags=re.MULTILINE)  # Fix title format
    
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.parser.ParserError:
        # If YAML parsing fails, try to extract key fields manually
        frontmatter = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key in ['memo_number', 'deliveries']:
                    try:
                        frontmatter[key] = int(value)
                    except ValueError:
                        frontmatter[key] = value
                elif key in ['date', 'time']:
                    frontmatter[key] = value
                else:
                    frontmatter[key] = value
    
    content = frontmatter_match.group(2)
    
    # Extract sections
    sections = re.split(r'^##\s+(\d+)\s*$', content, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]
    
    # Count links and images
    links = len(re.findall(r'\[.*?\]\(.*?\)', content))
    images = len(re.findall(r'!\[.*?\]\(.*?\)', content))
    
    # Count words in each section
    section_lengths = {}
    for i in range(0, len(sections), 2):
        if i + 1 < len(sections):
            section_num = sections[i]
            section_text = sections[i + 1]
            words = len(section_text.split())
            section_lengths[section_num] = words
    
    return {
        'memo_number': frontmatter.get('memo_number'),
        'date': frontmatter.get('date'),
        'deliveries': frontmatter.get('deliveries'),
        'total_words': len(content.split()),
        'links': links,
        'images': images,
        'section_lengths': section_lengths,
        'content': content
    }

def analyze_memos():
    memos_dir = os.path.join(CONTENT_DIR, 'markdown')
    memos_data = []
    
    # Process both markdown and processed files
    for filename in os.listdir(memos_dir):
        if filename.endswith('.md') or filename.endswith('.processed'):
            file_path = os.path.join(memos_dir, filename)
            try:
                memo_data = parse_markdown_file(file_path)
                if memo_data:
                    memos_data.append(memo_data)
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                continue
    
    if not memos_data:
        logger.error("No valid memo data found")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(memos_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Create analytics directory if it doesn't exist
    os.makedirs('analytics/visualizations', exist_ok=True)
    
    # Generate visualizations
    generate_visualizations(df)
    
    # Generate summary statistics
    generate_summary(df)

def generate_visualizations(df):
    # 1. Memo length over time
    plt.figure(figsize=(12, 6))
    plt.plot(df['date'], df['total_words'], marker='o')
    plt.title('Memo Length Over Time')
    plt.xlabel('Date')
    plt.ylabel('Word Count')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('analytics/visualizations/memo_length_over_time.png')
    plt.close()
    
    # 2. Deliveries distribution
    plt.figure(figsize=(10, 6))
    sns.histplot(df['deliveries'], bins=20)
    plt.title('Distribution of Memo Deliveries')
    plt.xlabel('Number of Deliveries')
    plt.ylabel('Count')
    plt.savefig('analytics/visualizations/deliveries_distribution.png')
    plt.close()
    
    # 3. Section length analysis
    section_lengths = defaultdict(list)
    for lengths in df['section_lengths']:
        for section, length in lengths.items():
            section_lengths[section].append(length)
    
    plt.figure(figsize=(10, 6))
    for section, lengths in section_lengths.items():
        sns.kdeplot(lengths, label=f'Section {section}')
    plt.title('Distribution of Section Lengths')
    plt.xlabel('Word Count')
    plt.ylabel('Density')
    plt.legend()
    plt.savefig('analytics/visualizations/section_lengths.png')
    plt.close()
    
    # 4. Links and images analysis
    plt.figure(figsize=(10, 6))
    plt.scatter(df['links'], df['images'])
    plt.title('Links vs Images in Memos')
    plt.xlabel('Number of Links')
    plt.ylabel('Number of Images')
    plt.savefig('analytics/visualizations/links_vs_images.png')
    plt.close()
    
    # 5. Word cloud of most common words
    all_text = ' '.join(df['content'])
    
    # Combine default stopwords with custom stopwords
    stopwords = set(STOPWORDS)
    stopwords.update(CUSTOM_STOPWORDS)
    
    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color='white',
        stopwords=stopwords,
        max_words=200,
        min_font_size=10
    ).generate(all_text)
    
    plt.figure(figsize=(10, 6))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.savefig('analytics/visualizations/wordcloud.png')
    plt.close()
    
    # 6. Sentiment analysis over time
    df['sentiment'] = df['content'].apply(lambda x: TextBlob(x).sentiment.polarity)
    plt.figure(figsize=(12, 6))
    plt.plot(df['date'], df['sentiment'], marker='o')
    plt.title('Memo Sentiment Over Time')
    plt.xlabel('Date')
    plt.ylabel('Sentiment Polarity')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('analytics/visualizations/sentiment_over_time.png')
    plt.close()

def generate_summary(df):
    # Generate summary statistics
    summary = {
        'total_memos': len(df),
        'avg_words_per_memo': df['total_words'].mean(),
        'avg_links_per_memo': df['links'].mean(),
        'avg_images_per_memo': df['images'].mean(),
        'avg_deliveries': df['deliveries'].mean(),
        'avg_sentiment': df['sentiment'].mean(),
        'time_span': {
            'start': df['date'].min().strftime('%Y-%m-%d'),
            'end': df['date'].max().strftime('%Y-%m-%d')
        }
    }
    
    # Save summary to file
    with open('analytics/summary.txt', 'w', encoding='utf-8') as f:
        f.write('Memo Archive Analytics Summary\n')
        f.write('=============================\n\n')
        for key, value in summary.items():
            if isinstance(value, dict):
                f.write(f'{key}:\n')
                for k, v in value.items():
                    f.write(f'  {k}: {v}\n')
            else:
                f.write(f'{key}: {value}\n')

if __name__ == '__main__':
    analyze_memos() 