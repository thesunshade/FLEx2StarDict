import json
import sys
import re
import os
from bs4 import BeautifulSoup

MINIMUM_ENTRY_WARNING = 7000
COLOR_RED = "\033[91m"
COLOR_RESET = "\033[0m"

def get_abbreviation_mapping(lists_xml_path):
    """Parses lists.xml. Raises error and exits if file is missing."""
    if not lists_xml_path or not os.path.exists(lists_xml_path):
        print(f"{COLOR_RED}Error: {lists_xml_path} not found. This file is required for variant synthesis.{COLOR_RESET}")
        sys.exit(1)
        
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

def parse_css_rules(css_path, html_classes):
    if not os.path.exists(css_path):
        return []
    with open(css_path, 'r', encoding='utf-8') as f:
        css_text = f.read()
    pattern = re.compile(r'([^{}]+)\s*\{\s*[^}]*?content\s*:\s*[\'"]([^\'"]*)[\'"][^}]*\}', re.MULTILINE | re.DOTALL)
    rules = []
    for selector_raw, content in pattern.findall(css_text):
        selectors = [s.strip() for s in selector_raw.split(',')]
        for full_selector in selectors:
            processed_content = content.encode().decode('unicode_escape') if '\\' in content else content
            rule_type = 'before' if ':before' in full_selector else 'after' if ':after' in full_selector else None
            if not rule_type: continue
            clean_selector = full_selector.replace(':before', '').replace(':after', '')
            words = re.split(r'([.#])', clean_selector)
            new_words = []
            for i, word in enumerate(words):
                if i > 0 and words[i-1] == '.':
                    class_name = re.match(r'^[a-zA-Z0-9_-]+', word)
                    if class_name:
                        cls = class_name.group(0)
                        if cls not in html_classes:
                            matches = [h for h in html_classes if h.startswith(cls)]
                            if matches:
                                best_match = min(matches, key=lambda x: len(x))
                                word = word.replace(cls, best_match, 1)
                new_words.append(word)
            rules.append(("".join(new_words), processed_content, rule_type))
    return rules

def apply_css_content(soup, css_rules):
    if not css_rules: return
    best_matches = {}
    for selector, content, side in css_rules:
        try:
            elements = soup.select(selector)
            for el in elements:
                best_matches[(id(el), side)] = (el, content)
        except Exception: pass
    for (el_id, side), (el, content) in best_matches.items():
        if side == 'before': el.insert(0, content)
        else: el.append(content)

def format_html(soup):
    italic_classes = re.compile(r'morphosyntaxanalysis|scientificname|sensetype|abbreviation|translation|example')
    for el in soup.find_all(class_=italic_classes): el.name = 'em'
    bold_classes = re.compile(r'mainheadword|headword|letter|sensenumber')
    for el in soup.find_all(class_=bold_classes): el.name = 'strong'
    for container in soup.find_all(class_='senses'):
        sensecontents = container.find_all(class_='sensecontent', recursive=False)
        for i, sc in enumerate(sensecontents):
            if i > 0: sc.name = 'div'
    for ex_contents in soup.find_all(class_='examplescontents'): ex_contents.name = 'ul'
    for ex_content in soup.find_all(class_='examplescontent'):
        ex_content.name = 'li'
        from bs4 import NavigableString
        for child in list(ex_content.children):
            if isinstance(child, NavigableString) and child.strip():
                child.extract()
                break
    for tc in soup.find_all(class_='translationcontents'):
        if not any(isinstance(c, str) and c.startswith(' ') for c in tc.contents): tc.insert(0, ' ')
    for pos in soup.find_all(class_='partofspeech'):
        leaf = pos
        while leaf.find():
            children = leaf.find_all(recursive=False)
            if children: leaf = children[-1]
            else: break
        text = leaf.get_text()
        if text and not text.endswith(' '): leaf.append(' ')
    for vvr in soup.find_all(class_='visiblevariantentryrefs'):
        if not any(isinstance(c, str) and c.startswith(' ') for c in vvr.contents): vvr.insert(0, ' ')
        if not vvr.get_text().endswith(' '): vvr.append(' ')

def xhtml_to_json(xhtml_file, json_file, lists_xml_file=None):
    with open(xhtml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    soup = BeautifulSoup(content, 'html.parser')
    
    html_classes = set()
    for tag in soup.find_all(class_=True):
        if isinstance(tag['class'], list):
            for cls in tag['class']: html_classes.add(cls)
        else: html_classes.add(tag['class'])

    css_path = xhtml_file.rsplit('.', 1)[0] + '.css'
    css_rules = parse_css_rules(css_path, html_classes)
    abbr_mapping = get_abbreviation_mapping(lists_xml_file)

    # Regex definitions for FLEx's versioned classes
    headword_regex = re.compile(r'headword|mainheadword')
    variant_ref_regex = re.compile(r'variantformentrybackrefs')
    variant_type_regex = re.compile(r'variantentrytypes')
    backref_regex = re.compile(r'variantformentrybackref')

    # Pass 1: Collect existing headwords
    existing_headwords = set()
    entries = soup.find_all('div', class_=['entry', 'minorentryvariant'])
    for entry in entries:
        hw_el = entry.find(class_=headword_regex)
        if hw_el:
            text = hw_el.get_text().replace('≻', '').strip()
            if text: existing_headwords.add(text)
    
    main_entries_count = len(existing_headwords)
    print(f"Identified {main_entries_count} unique existing headwords.")

    # Pass 2: Collect variations
    synthesized_entries = {}
    for entry in entries:
        headword_el = entry.find(class_=headword_regex)
        if not headword_el: continue
        main_hw_text = headword_el.get_text().strip()
            
        for container in entry.find_all(class_=variant_ref_regex):
            type_container = container.find(class_=variant_type_regex) or container.find_previous_sibling(class_=variant_type_regex)
            if not type_container: continue
                
            abbr_el = type_container.find(class_=re.compile(r'abbreviation'))
            if not abbr_el: continue
            abbr_text = abbr_el.get_text().strip()
            
            for ref_block in container.find_all(class_=backref_regex):
                v_hw_el = ref_block.find(class_=headword_regex)
                if not v_hw_el: continue
                
                v_text = v_hw_el.get_text().replace('≻', '').strip()
                if abbr_text in abbr_mapping and v_text not in existing_headwords:
                    rev_name = abbr_mapping[abbr_text]
                    entry_label = f"{rev_name} {main_hw_text}"
                    if v_text not in synthesized_entries:
                        synthesized_entries[v_text] = []
                    if entry_label not in synthesized_entries[v_text]:
                        synthesized_entries[v_text].append(entry_label)

    variant_entries_count = len(synthesized_entries)
    if variant_entries_count == 0:
        print(f"{COLOR_RED}Error: No variants found in the second pass. Something has broken.{COLOR_RESET}")
        sys.exit(1)
    
    print(f"Synthesized {variant_entries_count} minor variant entries.")

    # Pass 3: Formatting and Final Construction
    apply_css_content(soup, css_rules)
    format_html(soup)
    
    result = []
    formatted_entries = soup.find_all('div', class_=['entry', 'minorentryvariant'])
    for entry in formatted_entries:
        headword_el = entry.find(class_=headword_regex)
        if not headword_el: continue
        headword = headword_el.get_text().replace('≻', '').strip()
        
        value = ""
        found_headword = False
        for child in entry.children:
            if child == headword_el:
                found_headword = True
                continue
            if found_headword:
                value += str(child)
        
        value_soup = BeautifulSoup(value.replace('"', "'"), 'html.parser')
        for a in value_soup.find_all('a'):
            if a.get('href', '').startswith('#'):
                a.replace_with(a.text)
        
        result.append([headword, str(value_soup).replace('"', "'")])

    for v_text, labels in synthesized_entries.items():
        combined_label = ", ".join(labels)
        html = f'<div class="minorentryvariant"><span class="headword-2"><span lang="si">{v_text}</span></span><span class="visiblevariantentryrefs"><span class="variantentrytypes-2"><span class="variantentrytype"><span class="reversename"><span lang="en">{combined_label}</span></span></span></span></span></div>'
        v_soup = BeautifulSoup(html, 'html.parser').div
        apply_css_content(v_soup, css_rules)
        format_html(v_soup)
        result.append([v_text, str(v_soup).replace('"', "'")])
    
    total_entries = len(result)
    print(f"Total entries processed: {total_entries}")

    if total_entries < MINIMUM_ENTRY_WARNING:
        print(f"\n{COLOR_RED}[WARNING] Only {total_entries} entries found.{COLOR_RESET}")
        confirm = input("Proceed anyway? (y/n): ").lower()
        if confirm != 'y': sys.exit(0)

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file> [lists_xml_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = input_file.rsplit('.', 1)[0] + '.json'
    lists_xml = sys.argv[2] if len(sys.argv) >= 3 else os.path.join(os.path.dirname(os.path.abspath(input_file)), "lists.xml")

    try:
        xhtml_to_json(input_file, output_file, lists_xml)
        print(f"Successfully converted {input_file} to {output_file}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()