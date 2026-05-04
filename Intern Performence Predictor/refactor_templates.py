import os
import re

BASE_DIR = r"c:\Users\acer\Desktop\College\PROJECT\backend"
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
BASE_HTML_PATH = os.path.join(TEMPLATES_DIR, "base.html")
ADVANCED_BASE_HTML_PATH = os.path.join(TEMPLATES_DIR, "advanced_base.html")

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def get_block_content(text, block_name):
    # Retrieve the content INSIDE the block tags
    pattern = re.compile(r'{%\s*block\s+' + re.escape(block_name) + r'\s*%}(.*?){%\s*endblock\s*%}', re.DOTALL)
    match = pattern.search(text)
    return match.group(1) if match else None  # Return None if block not found

def process_file(filename):
    filepath = os.path.join(TEMPLATES_DIR, filename)
    content = read_file(filepath)

    base_content_raw = ""
    if '{% extends "base.html" %}' in content or "{% extends 'base.html' %}" in content:
        base_content_raw = read_file(BASE_HTML_PATH)
    elif '{% extends "advanced_base.html" %}' in content or "{% extends 'advanced_base.html' %}" in content:
        base_content_raw = read_file(ADVANCED_BASE_HTML_PATH)
    else:
        print(f"Skipping {filename} (no known extends)")
        return

    print(f"Processing {filename}...")

    # Blocks to process
    # We map 'head' -> 'extra_css' effectively, but we process them separately first
    blocks_of_interest = ['title', 'extra_css', 'content', 'scripts', 'head']
    
    # Get base defaults
    base_defaults = {}
    for b in ['title', 'extra_css', 'content', 'scripts']:
        val = get_block_content(base_content_raw, b)
        base_defaults[b] = val if val is not None else ""
    
    # 'head' doesn't exist in base, so default is empty
    base_defaults['head'] = ""

    # Get child overrides
    child_blocks = {}
    for b in blocks_of_interest:
        val = get_block_content(content, b)
        child_blocks[b] = val # can be None

    # Resolve content for each block (handling super)
    resolved_blocks = {}
    for b in blocks_of_interest:
        child_val = child_blocks[b]
        base_val = base_defaults.get(b, "")
        
        if child_val is not None:
            # Replace super() with base content
            # super() might be {{ super() }}
            resolved = child_val.replace('{{ super() }}', base_val)
            resolved_blocks[b] = resolved
        else:
            # Child didn't override, use base default
            resolved_blocks[b] = base_val

    # Merge head into extra_css
    # If child had head content, it's now in resolved_blocks['head']
    # We append it to resolved_blocks['extra_css']
    if resolved_blocks.get('head'):
        resolved_blocks['extra_css'] = resolved_blocks.get('extra_css', "") + "\n" + resolved_blocks['head']

    # Now construct the new page
    # Start with base content
    new_page_content = base_content_raw
    
    # Replace blocks with resolved content
    # Note: 'head' block doesn't exist in base, so we don't need to replace it there.
    # We only replace blocks that exist in base: title, extra_css, content, scripts.
    
    target_base_blocks = ['title', 'extra_css', 'content', 'scripts']
    
    for block in target_base_blocks:
        # Find the block in the base content (which is now new_page_content)
        pattern = re.compile(r'{%\s*block\s+' + re.escape(block) + r'\s*%}.*?{%\s*endblock\s*%}', re.DOTALL)
        
        # If block exists in base, replace it with resolved content
        if pattern.search(new_page_content):
            new_page_content = pattern.sub(resolved_blocks[block], new_page_content)
    
    # Write back
    write_file(filepath, new_page_content)
    print(f"Refactor complete for {filename}")

if __name__ == "__main__":
    files = os.listdir(TEMPLATES_DIR)
    for f in files:
        if f.endswith(".html") and f not in ["base.html", "advanced_base.html", "login.html"]:
            process_file(f)
