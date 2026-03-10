import json
import sys
import re
import os
from bs4 import BeautifulSoup

def get_abbreviation_mapping(lists_xml_path):
    """
    Parses lists.xml to create a mapping of abbreviations to their reverse names.
    Example: 'pst.' -> 'Past of'
    """
    if not os.path.exists(lists_xml_path):
        print(f"Warning: {lists_xml_path} not found. Variation generation will be limited.")
        return {}
        
    with open(lists_xml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')
    
    mapping = {}
    items = soup.find_all(['letitem', 'lrtitem', 'positem'])
    for item in items:
        abbr_tag = item.find('abbr')
        revname_tag = item.find('revname')
        
        if abbr_tag and revname_tag:
            abbr_str_tag = abbr_tag.find('str')
            revname_str_tag = revname_tag.find('str')
            
            if abbr_str_tag and revname_str_tag:
                abbr = abbr_str_tag.text.strip()
                revname = revname_str_tag.text.strip()
                if abbr and revname:
                    mapping[abbr] = revname
    return mapping

def xhtml_to_json(xhtml_file, json_file, lists_xml_file=None):
    # Read the XHTML file
    with open(xhtml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')
    
    # Get abbreviation mapping if lists.xml is provided
    abbr_mapping = {}
    if lists_xml_file:
        abbr_mapping = get_abbreviation_mapping(lists_xml_file)
    
    # First pass: Collect all existing headwords
    existing_headwords = set()
    entries = soup.find_all('div', class_=['entry', 'minorentryvariant'])
    for entry in entries:
        headword_span = entry.find('span', class_=re.compile(r'headword|mainheadword'))
        if headword_span:
            a_tag = headword_span.find('a')
            if a_tag and a_tag.text:
                existing_headwords.add(a_tag.text.strip())
            elif headword_span.text:
                existing_headwords.add(headword_span.text.strip())
    
    result = []
    synthesized_entries = {} # headword -> list of "ReverseName Headword" strings

    # Second pass: Process entries and collect variations
    for entry in entries:
        # Extract headword
        headword_span = entry.find('span', class_=re.compile(r'headword|mainheadword'))
        if not headword_span:
            continue
            
        a_tag = headword_span.find('a')
        if not (a_tag and a_tag.text):
            # If no a-tag, use span text
            if not headword_span.text:
                continue
            headword = headword_span.text.strip()
        else:
            headword = a_tag.text.strip()
            
        # Get all content after the headword span
        value = ""
        found_headword = False
        for child in entry.children:
            if child == headword_span:
                found_headword = True
                continue
            if found_headword:
                value += str(child)
        
        # Process the HTML:
        value = value.replace('"', "'")
        value = ' '.join(value.split())
        value_soup = BeautifulSoup(value, 'html.parser')
        
        # Remove internal links
        for a in value_soup.find_all('a'):
            href = a.get('href', '')
            if href.startswith('#'):
                a.replace_with(a.text)
        
        processed_value = str(value_soup).replace('"', "'")
        result.append([headword, processed_value])

        # Find variations within this entry
        # Structure: <span class="variantformentrybackrefs">
        #   <span class="variantentrytypes"> <span class="variantentrytype"> <span class="abbreviation-2"> pst. </span> </span> </span>
        #   <span class="variantformentrybackref"> <span class="headword"> <span lang="si"> <a href="..."> ඇඬුවා </a> </span> </span> </span>
        # </span>
        variant_refs = entry.find_all('span', class_='variantformentrybackrefs')
        for vref in variant_refs:
            # We need to find pairs of (abbreviation, variant_headword)
            # A single abbreviation may apply to multiple headwords that follow it.
            current_abbr = None
            for child in vref.children:
                if not hasattr(child, 'get'):
                    continue
                classes = child.get('class', [])
                if 'variantentrytypes' in classes:
                    # Update current abbreviation
                    abbr_span = child.find('span', class_=re.compile(r'abbreviation'))
                    if abbr_span:
                        current_abbr = abbr_span.get_text().strip()
                elif 'variantformentrybackref' in classes:
                    # Found a variant headword, use current abbreviation
                    if not current_abbr or current_abbr not in abbr_mapping:
                        continue
                        
                    v_hw = child.find('span', class_='headword')
                    if not v_hw:
                        continue
                        
                    v_text = v_hw.get_text().strip()
                    if not v_text or v_text in existing_headwords:
                        continue
                        
                    rev_name = abbr_mapping[current_abbr]
                    entry_text = f"{rev_name} {headword}"
                    if v_text not in synthesized_entries:
                        synthesized_entries[v_text] = []
                    if entry_text not in synthesized_entries[v_text]:
                        synthesized_entries[v_text].append(entry_text)

    # Add synthesized entries to result
    for v_text, labels in synthesized_entries.items():
        # Combine multiple labels if necessary
        combined_label = ", ".join(labels)
        # Create a simple minor-entry-like HTML
        html = f'<div class="minorentryvariant"><span class="headword-2"><span lang="si">{v_text}</span></span><span class="visiblevariantentryrefs"><span class="variantentrytypes-2"><span class="variantentrytype"><span class="reversename"><span lang="en">{combined_label}</span></span></span></span></span></div>'
        result.append([v_text, html])

    # Write to JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file> [lists_xml_file]")
        print("Example: python script.py dictionary.xhtml lists.xml")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = input_file.rsplit('.', 1)[0] + '.json'
    
    lists_xml = None
    if len(sys.argv) >= 3:
        lists_xml = sys.argv[2]
    else:
        # Try to find lists.xml in the same directory
        potential_path = os.path.join(os.path.dirname(os.path.abspath(input_file)), "lists.xml")
        if os.path.exists(potential_path):
            lists_xml = potential_path

    try:
        xhtml_to_json(input_file, output_file, lists_xml)
        print(f"Successfully converted {input_file} to {output_file}")
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error processing file: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
