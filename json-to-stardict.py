import json
import sys
import os
import struct
import re
import shutil

def create_stardict(json_file, dict_name):
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
        
        for word, processed_html in entries:
            print(f"\rBuilding dictionary: {word[:40]}...", end='', flush=True)
            
            # Encode to UTF-8
            definition_bytes = processed_html.encode('utf-8')
            definition_size = len(definition_bytes)
            
            # Write only the definition to .dict file
            f_dict.write(definition_bytes)
            
            # Store index data
            idx_data.append((word, current_offset, definition_size))
            
            # Update offset for next entry
            current_offset += definition_size
        print() # New line after finishing word loop
    
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
    # It usually look in the same directory as the json file
    json_dir = os.path.dirname(os.path.abspath(json_file))
    png_file = os.path.join(json_dir, f"{dict_name}.png")
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