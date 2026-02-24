import json
import sys
import re
from bs4 import BeautifulSoup

def xhtml_to_json(xhtml_file, json_file):
    # Read the XHTML file
    with open(xhtml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')
    
    result = []
    
    # Find all entry divs of BOTH types
    for entry in soup.find_all('div', class_=['entry', 'minorentryvariant']):
        # Extract headword by looking for elements where class contains 'headword' or 'mainheadword'
        headword_span = entry.find('span', class_=re.compile(r'headword|mainheadword'))
        if headword_span:
            a_tag = headword_span.find('a')
            if a_tag and a_tag.text:
                headword = a_tag.text
                
                # Get all content after the headword span we just found
                value = ""
                found_headword = False
                
                # Iterate through all children of the entry div
                for child in entry.children:
                    # Skip the headword span (whichever one it was)
                    if child == headword_span:
                        found_headword = True
                        continue
                    
                    # Add all content after the headword
                    if found_headword:
                        value += str(child)
                
                # Process the HTML:
                # 1. Replace double quotes with single quotes
                value = value.replace('"', "'")
                # 2. Remove line breaks and extra whitespace
                value = ' '.join(value.split())
                
                # Now process the value to remove internal links
                # Parse the value HTML again
                value_soup = BeautifulSoup(value, 'html.parser')
                
                # Find all a tags
                for a in value_soup.find_all('a'):
                    href = a.get('href', '')
                    # If it's an internal link (starts with #), replace with just the text
                    if href.startswith('#'):
                        a.replace_with(a.text)
                
                # Convert back to string and replace double quotes with single quotes
                processed_value = str(value_soup).replace('"', "'")
                
                # Add to result list
                result.append([headword, processed_value])
    
    # Write to JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

# The main() function remains the same
def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file>")
        print("Example: python script.py dictionary.xhtml")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = input_file.rsplit('.', 1)[0] + '.json'
    
    try:
        xhtml_to_json(input_file, output_file)
        print(f"Successfully converted {input_file} to {output_file}")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()