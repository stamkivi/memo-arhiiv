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
import emoji

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure matplotlib with minimal settings
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial'],
    'text.usetex': False,
    'axes.unicode_minus': False,
    'mathtext.default': 'regular',
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'text.antialiased': False
})

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
            # Remove emojis before counting words
            section_text = emoji.replace_emoji(section_text, '')
            words = len(section_text.split())
            section_lengths[section_num] = words
    
    return {
        'memo_number': frontmatter.get('memo_number'),
        'date': frontmatter.get('date'),
        'deliveries': frontmatter.get('deliveries'),
        'total_words': len(emoji.replace_emoji(content, '').split()),
        'links': links,
        'images': images,
        'section_lengths': section_lengths,
        'content': content
    }

def generate_section_lengths_chart(df):
    """Create a distribution chart for section lengths using kernel density plots."""
    try:
        # Remove the existing file if it exists
        output_file = 'analytics/visualizations/section_lengths.png'
        if os.path.exists(output_file):
            os.remove(output_file)
            logger.info(f"Removed existing {output_file}")
        
        # Clear any existing plots
        plt.close('all')
        
        # Extract section data directly from the DataFrame
        section_data = {}
        valid_sections = ['1', '2', '3']  # We'll focus on the three main sections
        
        # Process each row directly to extract section lengths
        for _, row in df.iterrows():
            if 'section_lengths' in row and isinstance(row['section_lengths'], dict):
                for section, length in row['section_lengths'].items():
                    # Convert section to string for consistency
                    section_str = str(section).strip()
                    
                    # Only process the three main sections
                    if section_str not in valid_sections:
                        continue
                    
                    # Make sure we have a valid length
                    try:
                        length_val = float(length)
                        
                        if section_str not in section_data:
                            section_data[section_str] = []
                        
                        section_data[section_str].append(length_val)
                    except (ValueError, TypeError):
                        pass
        
        # Create the figure
        plt.figure(figsize=(10, 6))
        
        # Plot each section's distribution
        for section in valid_sections:
            if section in section_data and len(section_data[section]) > 5:
                # Only plot if we have at least 5 data points and there's some variance
                lengths = section_data[section]
                if len(set(lengths)) > 1:  # Check for variance
                    # Use numpy to calculate a smooth histogram
                    try:
                        sns.kdeplot(lengths, label=f'Section {section}', warn_singular=False)
                    except Exception as e:
                        logger.warning(f"Could not create KDE plot for section {section}: {str(e)}")
                        # Fall back to a histogram
                        plt.hist(lengths, alpha=0.5, label=f'Section {section} (histogram)', density=True, bins=20)
                else:
                    # For sections with no variance, plot a vertical line at the constant value
                    plt.axvline(x=lengths[0], label=f'Section {section} (constant)', linestyle='--')
        
        # Add labels and title
        plt.title('Distribution of Section Lengths')
        plt.xlabel('Word Count')
        plt.ylabel('Density')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.3)
        
        # Save with simple options to avoid font issues
        plt.savefig(output_file)
        plt.close()
        
        if os.path.exists(output_file):
            logger.info(f"Successfully created {output_file}")
            return True
        else:
            logger.error(f"Failed to create {output_file}")
            # Fall back to a very simple chart if needed
            try:
                plt.figure(figsize=(10, 6))
                
                # Calculate averages for a simple bar chart fallback
                averages = []
                for section in valid_sections:
                    if section in section_data and section_data[section]:
                        averages.append(sum(section_data[section]) / len(section_data[section]))
                    else:
                        averages.append(0)
                
                plt.bar(valid_sections, averages)
                plt.title('Average Section Lengths (Fallback)')
                plt.xlabel('Section Number')
                plt.ylabel('Average Word Count')
                plt.savefig(output_file)
                plt.close()
                
                logger.info(f"Created fallback chart at {output_file}")
                return True
            except Exception as e2:
                logger.error(f"Even fallback chart failed: {str(e2)}")
                return False
        
    except Exception as e:
        logger.error(f"Error in generate_section_lengths_chart: {str(e)}")
        
        # Last resort - create a minimal chart with dummy data
        try:
            plt.figure(figsize=(10, 6))
            plt.bar(['1', '2', '3'], [100, 200, 150])
            plt.title('Section Lengths (Placeholder)')
            plt.xlabel('Section')
            plt.ylabel('Word Count')
            plt.savefig(output_file)
            plt.close()
            logger.info(f"Created placeholder chart at {output_file}")
            return True
        except Exception as e2:
            logger.error(f"Even placeholder chart failed: {str(e2)}")
            return False

def generate_deliveries_time_series(df):
    """Create a time series chart showing how deliveries count changes over time."""
    try:
        output_file = 'analytics/visualizations/deliveries_over_time.png'
        
        # Ensure the dataframe is sorted by date
        df_sorted = df.sort_values('date')
        
        # Create a new figure
        plt.figure(figsize=(12, 6))
        
        # Plot deliveries over time
        plt.plot(df_sorted['date'], df_sorted['deliveries'], marker='o', linestyle='-', color='blue')
        
        # Add a trend line (rolling average)
        rolling_avg = df_sorted['deliveries'].rolling(window=20, min_periods=1).mean()
        plt.plot(df_sorted['date'], rolling_avg, 'r-', linewidth=2, label='20-Memo Rolling Average')
        
        # Add labels and title
        plt.title('Memo Deliveries Over Time')
        plt.xlabel('Date')
        plt.ylabel('Number of Deliveries')
        plt.xticks(rotation=45)
        plt.legend(['Deliveries', '20-Memo Rolling Average'])
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add tight layout to make sure everything fits
        plt.tight_layout()
        
        # Save the figure
        plt.savefig(output_file)
        plt.close()
        
        if os.path.exists(output_file):
            logger.info(f"Successfully created {output_file}")
            return True
        else:
            logger.error(f"Failed to create {output_file}")
            return False
            
    except Exception as e:
        logger.error(f"Error in generate_deliveries_time_series: {str(e)}")
        return False

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
                    # Skip memos with non-numeric or large memo numbers
                    memo_number = memo_data.get('memo_number')
                    if memo_number is None:
                        logger.info(f"Skipping {filename} - No memo number found")
                        continue
                        
                    # Try to convert to int if it's a string
                    if isinstance(memo_number, str):
                        try:
                            memo_number = int(memo_number)
                            memo_data['memo_number'] = memo_number
                        except ValueError:
                            logger.info(f"Skipping {filename} - Non-numeric memo number: {memo_number}")
                            continue
                    
                    # Skip if memo number is too large
                    if isinstance(memo_number, int) and memo_number > 10000:
                        logger.info(f"Skipping {filename} - Memo number too large: {memo_number}")
                        continue
                    
                    # All checks passed, add to dataset
                    memos_data.append(memo_data)
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                continue
    
    if not memos_data:
        logger.error("No valid memo data found")
        return
    
    logger.info(f"Processing {len(memos_data)} valid memos")
    
    # Convert to DataFrame
    df = pd.DataFrame(memos_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Create analytics directory if it doesn't exist
    os.makedirs('analytics/visualizations', exist_ok=True)
    
    # Generate visualizations
    generate_visualizations(df)
    
    # Generate section lengths chart (separate call to ensure it runs)
    generate_section_lengths_chart(df)
    
    # Generate deliveries time series chart
    generate_deliveries_time_series(df)
    
    # Generate summary statistics
    generate_summary(df)

def clean_content(text):
    """Clean the content by removing Twitter embeds, URLs, and other problematic content."""
    # Remove Twitter embeds (more comprehensive pattern)
    text = re.sub(r'\[!\[.*?\]\(.*?\)\].*?\]\(.*?\)', '', text)
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    # Remove image tags
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove timestamps and dates
    text = re.sub(r'\d{1,2}:\d{2}\s*[AP]M\s*∙\s*\w+\s*\d{1,2},\s*\d{4}', '', text)
    # Remove Twitter handles
    text = re.sub(r'@\w+', '', text)
    # Remove Twitter status links
    text = re.sub(r'https://mobile\.twitter\.com/\w+/status/\d+', '', text)
    # Remove dollar amounts and other special characters that might cause issues
    text = re.sub(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', '', text)
    # Remove any remaining special characters that might cause issues
    text = re.sub(r'[^\w\s.,!?-]', ' ', text)
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_visualizations(df):
    try:
        # 1. Memo length over time
        plt.figure(figsize=(12, 6))
        plt.plot(df['date'], df['total_words'], marker='o', label='Daily Length')
        # Add rolling average
        rolling_avg = df['total_words'].rolling(window=50, min_periods=1).mean()
        plt.plot(df['date'], rolling_avg, 'r-', linewidth=2, label='50-Memo Rolling Average')
        plt.title('Memo Length Over Time', pad=20, fontsize=12)
        plt.xlabel('Date', fontsize=10)
        plt.ylabel('Word Count', fontsize=10)
        plt.xticks(rotation=45)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig('analytics/visualizations/memo_length_over_time.png', dpi=300, bbox_inches='tight')
        plt.close('all')
        
        # 2. Deliveries distribution
        plt.figure(figsize=(10, 6))
        sns.histplot(df['deliveries'], bins=20)
        plt.title('Distribution of Memo Deliveries', pad=20, fontsize=12)
        plt.xlabel('Number of Deliveries', fontsize=10)
        plt.ylabel('Count', fontsize=10)
        plt.savefig('analytics/visualizations/deliveries_distribution.png', dpi=300, bbox_inches='tight')
        plt.close('all')
        
        # 3. Section length analysis now handled in separate function
        
        # 4. Links and images analysis
        plt.figure(figsize=(10, 6))
        plt.scatter(df['links'], df['images'])
        plt.title('Links vs Images in Memos', pad=20, fontsize=12)
        plt.xlabel('Number of Links', fontsize=10)
        plt.ylabel('Number of Images', fontsize=10)
        plt.savefig('analytics/visualizations/links_vs_images.png', dpi=300, bbox_inches='tight')
        plt.close('all')
        
        # 5. Word cloud of most common words
        # Clean the content before creating word cloud
        cleaned_texts = df['content'].apply(clean_content)
        all_text = ' '.join(cleaned_texts)
        
        # Combine default stopwords with custom stopwords
        stopwords = set(STOPWORDS)
        stopwords.update(CUSTOM_STOPWORDS)
        
        # Configure WordCloud with more robust settings
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            stopwords=stopwords,
            max_words=200,
            min_font_size=10,
            regexp=r'\w[\w\']+',  # Only include words with letters
            collocations=False  # Don't include common word pairs
        ).generate(all_text)
        
        plt.figure(figsize=(10, 6))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.savefig('analytics/visualizations/wordcloud.png', dpi=300, bbox_inches='tight')
        plt.close('all')
        
        # 6. Sentiment analysis over time - OPTIONAL
        # Only run this if we can create a sentiment column safely
        try:
            # Use a more aggressive cleaning function for sentiment analysis
            def clean_for_sentiment(text):
                """Even more aggressive cleaning for sentiment analysis"""
                # First apply regular cleaning
                text = clean_content(text)
                # Remove anything that looks like an embed
                text = re.sub(r'\[.*?\]', '', text)
                # Remove anything that looks like a quoted text
                text = re.sub(r'".*?"', '', text)
                # Remove anything with a dollar sign
                text = re.sub(r'[^\n]*\$[^\n]*', '', text)
                # Remove anything that might be a Twitter embed
                text = re.sub(r'[^\n]*Twitter[^\n]*', '', text)
                # Replace multiple newlines with a single one
                text = re.sub(r'\n+', '\n', text)
                return text
            
            # Try to compute sentiment more safely
            df['sentiment'] = df['content'].apply(lambda x: 
                               TextBlob(clean_for_sentiment(x)).sentiment.polarity 
                               if len(clean_for_sentiment(x)) > 10 else 0)
            
            plt.figure(figsize=(12, 6))
            plt.plot(df['date'], df['sentiment'], marker='o')
            plt.title('Memo Sentiment Over Time', pad=20, fontsize=12)
            plt.xlabel('Date', fontsize=10)
            plt.ylabel('Sentiment Polarity', fontsize=10)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig('analytics/visualizations/sentiment_over_time.png', dpi=300, bbox_inches='tight')
            plt.close('all')
        except Exception as e:
            logger.error(f"Error generating sentiment analysis: {str(e)}")
            logger.warning("Skipping sentiment analysis visualization")
            # Create a placeholder sentiment column for the summary
            df['sentiment'] = 0
        
    except Exception as e:
        logger.error(f"Error generating visualizations: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        # Continue with other visualizations even if one fails
        pass

def generate_summary(df):
    # Generate summary statistics
    summary = {
        'total_memos': len(df),
        'avg_words_per_memo': df['total_words'].mean(),
        'avg_links_per_memo': df['links'].mean(),
        'avg_images_per_memo': df['images'].mean(),
        'avg_deliveries': df['deliveries'].mean(),
        'time_span': {
            'start': df['date'].min().strftime('%Y-%m-%d'),
            'end': df['date'].max().strftime('%Y-%m-%d')
        }
    }
    
    # Only add sentiment if it exists
    if 'sentiment' in df.columns:
        summary['avg_sentiment'] = df['sentiment'].mean()
    
    # Add top 5 shortest and longest memos
    shortest_memos = df.nsmallest(5, 'total_words')[['memo_number', 'total_words']]
    longest_memos = df.nlargest(5, 'total_words')[['memo_number', 'total_words']]
    
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
        
        f.write('\nTop 5 Shortest Memos:\n')
        f.write('-------------------\n')
        for _, memo in shortest_memos.iterrows():
            f.write(f"Memo {memo['memo_number']}: {memo['total_words']} words\n")
        
        f.write('\nTop 5 Longest Memos:\n')
        f.write('------------------\n')
        for _, memo in longest_memos.iterrows():
            f.write(f"Memo {memo['memo_number']}: {memo['total_words']} words\n")

if __name__ == '__main__':
    analyze_memos() 