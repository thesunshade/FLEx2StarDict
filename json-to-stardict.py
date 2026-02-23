import json
import sys
import os
import struct
import re
import shutil
from bs4 import BeautifulSoup

def apply_css_to_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Apply italic formatting to elements with specific classes
    italic_elements = soup.find_all(class_=re.compile(r'morphosyntaxanalysis|scientificname|sensetype|abbreviation|translation|example'))
    for element in italic_elements:
        # Create new <em> tag
        em_tag = soup.new_tag("em")
        # Move all children to em_tag
        while len(element.contents) > 0:
            em_tag.append(element.contents[0])
        # Add the em_tag to the element
        element.append(em_tag)
    
    # Apply bold formatting to elements with specific classes
    bold_elements = soup.find_all(class_=re.compile(r'mainheadword|headword|letter|sensenumber'))
    for element in bold_elements:
        # Create new <strong> tag
        strong_tag = soup.new_tag("strong")
        # Move all children to strong_tag
        while len(element.contents) > 0:
            strong_tag.append(element.contents[0])
        # Add the strong_tag to the element
        element.append(strong_tag)
    
    # Apply before and after content based on specific patterns
    # Handle lexsensereferences
    for element in soup.find_all(class_='lexsensereferences'):
        if element.contents:
            element.insert(0, ' [')
            element.append('].')
    
    # Handle sensenumber
    for element in soup.find_all(class_='sensenumber'):
        if element.contents:
            element.append(') ')
    
    # Convert second-and-subsequent sensecontent spans to divs for line breaks
    # This mirrors the CSS rule: .sensecontent + .sensecontent { display: block }
    senses_containers = soup.find_all(class_='senses')
    for senses_container in senses_containers:
        sensecontents = senses_container.find_all(class_='sensecontent', recursive=False)
        for i, sc in enumerate(sensecontents):
            if i > 0:
                sc.name = 'div'
    
    # Handle usages
    for element in soup.find_all(class_='usages'):
        if element.contents:
            element.insert(0, '{')
            element.append('} ')
    
    # Handle visiblecomplexformbackrefs
    for element in soup.find_all(class_='visiblecomplexformbackrefs'):
        if element.contents:
            element.insert(0, ' (')
            element.append(')')
    
    # Handle complexformentryrefs
    for element in soup.find_all(class_='complexformentryrefs'):
        if element.contents:
            element.insert(0, '(')
            element.append(') ')
    
    # Handle variantformentrybackrefs
    for element in soup.find_all(class_='variantformentrybackrefs'):
        if element.contents:
            element.insert(0, '(')
            element.append(') ')
    
    # Handle minimallexreferences
    for element in soup.find_all(class_='minimallexreferences'):
        if element.contents:
            element.insert(0, '(')
            element.append('.)')
    
    # Handle etymologies
    for element in soup.find_all(class_='etymologies'):
        if element.contents:
            element.insert(0, '(')
            element.append(') ')
    
    # Handle scientificname
    for element in soup.find_all(class_='scientificname'):
        if element.contents:
            element.insert(0, ' [')
            element.append(']')
    
    # Handle dialectlabelsrs
    for element in soup.find_all(class_='dialectlabelsrs'):
        if element.contents:
            element.insert(0, ' [')
            element.append(']')
    
    # Convert examplescontents spans to <ul> tags
    for element in soup.find_all(class_='examplescontents'):
        element.name = 'ul'
    
    # Convert examplescontent spans to <li> tags
    for element in soup.find_all(class_='examplescontent'):
        element.name = 'li'
    
    # Add a space before translationcontents so example and translation are separated
    for element in soup.find_all(class_='translationcontents'):
        element.insert(0, ' ')
    
    # Handle adjacent sibling selectors for commas and spaces
    handle_adjacent_sibling_selectors(soup)
    
    # Add spaces after abbreviations and before certain elements
    add_missing_spaces(soup)
    
    # Add colons after abbreviation elements where needed
    add_colons_after_abbreviations(soup)

    # Add a space after the content of any element with a class containing 'ownertype_abbreviation'
    add_space_after_ownertype_abbreviations(soup)
    
    # Add a space after the content of any element with class 'variantentrytype' or 'reverseabbr'
    add_space_after_variantentrytype_or_reverseabbr(soup)
    
    return str(soup)

def handle_adjacent_sibling_selectors(soup):
    # Handle .entrytype + .entrytype:before (content: ',')
    entrytypes = soup.find_all(class_='entrytype')
    for i, entrytype in enumerate(entrytypes):
        if i > 0 and entrytypes[i-1].parent == entrytype.parent:
            entrytype.insert(0, ', ')
    
    # Handle .configtarget + .configtarget:before (content: ', ')
    configtargets = soup.find_all(class_='configtarget')
    for i, configtarget in enumerate(configtargets):
        if i > 0 and configtargets[i-1].parent == configtarget.parent:
            configtarget.insert(0, ', ')
    
    # Handle .headwor + .headwor:before (content: ' ')
    headwords = soup.find_all(class_=re.compile(r'headwor'))
    for i, headword in enumerate(headwords):
        if i > 0 and headwords[i-1].parent == headword.parent:
            headword.insert(0, ' ')
    
    # Handle .abbreviatio + .abbreviatio:before (content: ' ')
    abbreviations = soup.find_all(class_=re.compile(r'abbreviatio'))
    for i, abbreviation in enumerate(abbreviations):
        if i > 0 and abbreviations[i-1].parent == abbreviation.parent:
            abbreviation.insert(0, ' ')
    
    # Handle .partofspeec + .partofspeec:before (content: ' ')
    partofspeeches = soup.find_all(class_=re.compile(r'partofspeec'))
    for i, partofspeech in enumerate(partofspeeches):
        if i > 0 and partofspeeches[i-1].parent == partofspeech.parent:
            partofspeech.insert(0, ' ')
    
    # Handle .definitionorglos + .definitionorglos:before (content: ' ')
    definitionorglosses = soup.find_all(class_=re.compile(r'definitionorglos'))
    for i, definitionorgloss in enumerate(definitionorglosses):
        if i > 0 and definitionorglosses[i-1].parent == definitionorgloss.parent:
            definitionorgloss.insert(0, ' ')
    
    # Handle .sensecontent + span:before (content: '  ')
    sensecontents = soup.find_all(class_='sensecontent')
    for sensecontent in sensecontents:
        spans = sensecontent.find_all('span')
        for i, span in enumerate(spans):
            if i > 0 and spans[i-1].parent == span.parent:
                span.insert(0, '  ')
    
    # Handle .exampl + .exampl:before (content: ' ')
    examples = soup.find_all(class_=re.compile(r'exampl'))
    for i, example in enumerate(examples):
        if i > 0 and examples[i-1].parent == example.parent:
            example.insert(0, ' ')
    
    # Handle .translatio + .translatio:before (content: ' ')
    translations = soup.find_all(class_=re.compile(r'translatio'))
    for i, translation in enumerate(translations):
        if i > 0 and translations[i-1].parent == translation.parent:
            translation.insert(0, ' ')
    
    # Handle .referencedentry + .referencedentry:before (content: ', ')
    referencedentries = soup.find_all(class_=re.compile(r'referencedentry'))
    for i, referencedentry in enumerate(referencedentries):
        if i > 0 and referencedentries[i-1].parent == referencedentry.parent:
            referencedentry.insert(0, ', ')
    
    # Handle .visiblecomplexformbackref + .visiblecomplexformbackref:before (content: ', ')
    visiblecomplexformbackrefs = soup.find_all(class_=re.compile(r'visiblecomplexformbackref'))
    for i, visiblecomplexformbackref in enumerate(visiblecomplexformbackrefs):
        if i > 0 and visiblecomplexformbackrefs[i-1].parent == visiblecomplexformbackref.parent:
            visiblecomplexformbackref.insert(0, ', ')
    
    # Handle .complexformentryref + .complexformentryref:before (content: ', ')
    complexformentryrefs = soup.find_all(class_=re.compile(r'complexformentryref'))
    for i, complexformentryref in enumerate(complexformentryrefs):
        if i > 0 and complexformentryrefs[i-1].parent == complexformentryref.parent:
            complexformentryref.insert(0, ', ')
    
    # Handle .variantformentrybackref + .variantformentrybackref:before (content: ', ')
    # Only add comma if previous sibling is also a variantformentrybackref
    variantformentrybackrefs = soup.find_all(class_=re.compile(r'variantformentrybackref'))
    for vfb in variantformentrybackrefs:
        prev_sibling = vfb.previous_sibling
        # Skip text nodes and comments by checking for the 'get' attribute, which only Tags have
        while prev_sibling and not hasattr(prev_sibling, 'get'):
            prev_sibling = prev_sibling.previous_sibling
        if prev_sibling and 'variantformentrybackref' in prev_sibling.get('class', []):
            vfb.insert(0, ', ')
    
    # Handle .usage + .usage:before (content: ', ')
    usages = soup.find_all(class_=re.compile(r'usage'))
    for i, usage in enumerate(usages):
        if i > 0 and usages[i-1].parent == usage.parent:
            usage.insert(0, ', ')
    
    # Handle .minimallexreference + .minimallexreference:before (content: '; ')
    minimallexreferences = soup.find_all(class_=re.compile(r'minimallexreference'))
    for i, minimallexreference in enumerate(minimallexreferences):
        if i > 0 and minimallexreferences[i-1].parent == minimallexreference.parent:
            minimallexreference.insert(0, '; ')

def add_missing_spaces(soup):
    # Add spaces after variantentrytypes when followed by variantformentrybackref
    variantentrytypes = soup.find_all(class_='variantentrytypes')
    for vet in variantentrytypes:
        next_sibling = vet.next_sibling
        # Skip text nodes and comments by checking for the 'get' attribute
        while next_sibling and not hasattr(next_sibling, 'get'):
            next_sibling = next_sibling.next_sibling
        if next_sibling and hasattr(next_sibling, 'get') and next_sibling.get('class') and 'variantformentrybackref' in next_sibling.get('class'):
            vet.append(' ')
    
    # Add spaces after variantformentrybackref when followed by variantentrytypes
    variantformentrybackrefs = soup.find_all(class_=re.compile(r'variantformentrybackref'))
    for vfb in variantformentrybackrefs:
        next_sibling = vfb.next_sibling
        # Skip text nodes and comments by checking for the 'get' attribute
        while next_sibling and not hasattr(next_sibling, 'get'):
            next_sibling = next_sibling.next_sibling
        if next_sibling and hasattr(next_sibling, 'get') and next_sibling.get('class') and 'variantentrytypes' in next_sibling.get('class'):
            vfb.append(' ')
    
    # Add spaces after sharedgrammaticalinfo when followed by sensecontent
    sharedgrammaticalinfos = soup.find_all(class_='sharedgrammaticalinfo')
    for sgi in sharedgrammaticalinfos:
        next_sibling = sgi.next_sibling
        # Skip text nodes and comments by checking for the 'get' attribute
        while next_sibling and not hasattr(next_sibling, 'get'):
            next_sibling = next_sibling.next_sibling
        if next_sibling and hasattr(next_sibling, 'get') and next_sibling.get('class') and 'sensecontent' in next_sibling.get('class'):
            sgi.append(' ')
    
    # Add spaces after minimallexreferences when followed by senses
    minimallexreferences = soup.find_all(class_='minimallexreferences')
    for mlr in minimallexreferences:
        next_sibling = mlr.next_sibling
        # Skip text nodes and comments by checking for the 'get' attribute
        while next_sibling and not hasattr(next_sibling, 'get'):
            next_sibling = next_sibling.next_sibling
        if next_sibling and hasattr(next_sibling, 'get') and next_sibling.get('class') and 'senses' in next_sibling.get('class'):
            mlr.append(' ')

def add_colons_after_abbreviations(soup):
    # Add colons after ownertype_abbreviation elements in minimallexreferences
    minimallexreferences = soup.find_all(class_='minimallexreferences')
    for mlr in minimallexreferences:
        # Find all ownertype_abbreviation elements within this minimallexreference
        ownertype_abbreviations = mlr.find_all(class_=re.compile(r'ownertype_abbreviation'))
        for abbr in ownertype_abbreviations:
            # Check if this abbreviation is followed by a configtargets element
            parent = abbr.parent
            if parent:
                # Look for configtargets in the siblings after the abbreviation
                found_configtargets = False
                for sibling in abbr.next_siblings:
                    if hasattr(sibling, 'get') and sibling.get('class') and any('configtargets' in c for c in sibling.get('class')):
                        found_configtargets = True
                        break
                    # If we hit a non-element sibling, stop looking
                    elif not hasattr(sibling, 'get'):
                        continue
                    else:
                        break
                
                if found_configtargets:
                    # Add colon and space after the abbreviation
                    abbr.append(': ')

def add_space_after_ownertype_abbreviations(soup):
    """
    Adds a trailing space inside any element whose class name contains 'ownertype_abbreviation'.
    This ensures there is a space after the text content (e.g., "syn") and before the closing tag.
    """
    ownertype_abbreviations = soup.find_all(class_=re.compile(r'ownertype_abbreviation'))
    for abbr in ownertype_abbreviations:
        abbr.append(' ')

def add_space_after_variantentrytype_or_reverseabbr(soup):
    """
    Adds a trailing space inside any element with class 'variantentrytype' or 'reverseabbr'.
    This ensures there is a space after the text content (e.g., "pl. of") and before the closing tag.
    """
    variantentrytypes = soup.find_all(class_='variantentrytype')
    for vt in variantentrytypes:
        vt.append(' ')
    
    reverseabbrs = soup.find_all(class_='reverseabbr')
    for ra in reverseabbrs:
        ra.append(' ')

def create_stardict(json_file, dict_name):
    # Get base filename without extension
    base_name = os.path.splitext(json_file)[0]
    css_file = base_name + '.css'
    
    # Create output directory
    output_dir = dict_name
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare output filenames
    dict_file = os.path.join(output_dir, dict_name + '.dict')
    idx_file = os.path.join(output_dir, dict_name + '.idx')
    ifo_file = os.path.join(output_dir, dict_name + '.ifo')
    
    # Read JSON data (list of [word, html] pairs)
    with open(json_file, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    
    # Sort entries alphabetically by word
    entries.sort(key=lambda x: x[0])
    
    # Create .dict file (only definitions, no words)
    with open(dict_file, 'wb') as f_dict:
        current_offset = 0
        idx_data = []
        
        for word, original_html in entries:
            
            # Apply CSS rules to HTML
            processed_html = apply_css_to_html(original_html)
            
            # Encode to UTF-8
            definition_bytes = processed_html.encode('utf-8')
            definition_size = len(definition_bytes)
            
            # Write only the definition to .dict file
            f_dict.write(definition_bytes)
            
            # Store index data
            idx_data.append((word, current_offset, definition_size))
            
            # Update offset for next entry
            current_offset += definition_size
    
    # Create .idx file
    with open(idx_file, 'wb') as f_idx:
        for word, offset, size in idx_data:
            word_bytes = word.encode('utf-8')
            f_idx.write(word_bytes + b'\x00')  # Null-terminated word
            f_idx.write(struct.pack('>II', offset, size))  # Offset and size (big-endian)
    
    # Get actual idx file size
    idx_file_size = os.path.getsize(idx_file)
    
    # Create .ifo file with proper format
    with open(ifo_file, 'w', encoding='utf-8') as f_ifo:
        f_ifo.write("StarDict's dict ifo file\n")
        f_ifo.write("version=3.0.0\n")
        f_ifo.write(f"wordcount={len(entries)}\n")
        f_ifo.write(f"idxfilesize={idx_file_size}\n")
        f_ifo.write(f"bookname={dict_name}\n")
        f_ifo.write("sametypesequence=h\n")
    
    # Check for PNG file with the same name as the dictionary
    png_file = os.path.join(os.path.dirname(json_file), f"{dict_name}.png")
    if os.path.exists(png_file):
        # Copy PNG to output directory
        shutil.copy(png_file, os.path.join(output_dir, f"{dict_name}.png"))
        print(f"Copied {dict_name}.png to dictionary directory")
    
    print(f"\nSuccessfully created StarDict dictionary in directory: {output_dir}")
    print(f"Files created:")
    print(f"  - {dict_file}")
    print(f"  - {idx_file}")
    print(f"  - {ifo_file}")
    if os.path.exists(png_file):
        print(f"  - {os.path.join(output_dir, dict_name + '.png')}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <json_file> <dictionary_name>")
        print("Example: python script.py mydict.json SinhalaDictionary")
        sys.exit(1)
    
    json_file = sys.argv[1]
    dict_name = sys.argv[2]
    
    if not os.path.exists(json_file):
        print(f"Error: File {json_file} not found")
        sys.exit(1)
    
    create_stardict(json_file, dict_name)