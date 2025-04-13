import os

# Base paths
SOURCE_DIR = "source"
CONTENT_DIR = "content"

# Source paths
SMAILY_SOURCE_DIR = os.path.join(SOURCE_DIR, "smaily")
SUBSTACK_SOURCE_DIR = os.path.join(SOURCE_DIR, "substack")

# Output paths
MARKDOWN_DIR = os.path.join(CONTENT_DIR, "markdown")
IMAGES_DIR = os.path.join(CONTENT_DIR, "images")

# Ensure directories exist
for directory in [SOURCE_DIR, CONTENT_DIR, MARKDOWN_DIR, IMAGES_DIR]:
    os.makedirs(directory, exist_ok=True) 