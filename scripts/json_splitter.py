#!/usr/bin/env python3
# dependencies = [
#   "click==8.1.7",
# ]

import json
import os
import sys
import click


@click.command()
@click.argument('json_file', type=click.Path(exists=True))
@click.argument('key_name', type=str)
@click.argument('dest_dir', type=click.Path())
@click.option('--id-key', default='id', help='Name of the ID field in each object (default: "id")')
@click.option('--clean', is_flag=True, help='Delete and recreate the destination directory')
def main(json_file, key_name, dest_dir, id_key, clean):
    """
    Process a JSON file by extracting objects from a specified key and saving each object
    to its own file named after its ID.
    
    JSON_FILE: Path to the input JSON file
    KEY_NAME: Key in the JSON file containing the array of objects
    DEST_DIR: Directory where individual JSON files will be saved
    
    If --clean is specified, the destination directory will be deleted and recreated.
    """
    try:
        # Handle the destination directory
        if clean and os.path.exists(dest_dir):
            import shutil
            print(f"Cleaning destination directory: {dest_dir}")
            shutil.rmtree(dest_dir)
        
        # Create destination directory
        os.makedirs(dest_dir, exist_ok=True)
        
        # Load the JSON file
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Check if the key exists in the JSON
        if key_name not in data:
            print(f"Error: Key '{key_name}' not found in the JSON file.")
            sys.exit(1)
        
        # Get the array of objects
        items = data[key_name]
        
        if not isinstance(items, list):
            print(f"Error: '{key_name}' does not contain a list of objects.")
            sys.exit(1)
        
        # Process each item
        for i, item in enumerate(items):
            # Check if the item has the ID key
            if id_key not in item:
                print(f"Warning: Item at index {i} does not have '{id_key}' key. Skipping.")
                continue
            
            # Get the ID
            item_id = item[id_key]
            
            # Create the output file path
            output_file = os.path.join(dest_dir, f"{item_id}.json")
            
            # Write the item to a new file
            with open(output_file, 'w') as f:
                json.dump(item, f, indent=2)
            
            print(f"Created: {output_file}")
        
        print(f"Processed {len(items)} items from '{key_name}'")
        
    except json.JSONDecodeError:
        print(f"Error: '{json_file}' is not a valid JSON file.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
