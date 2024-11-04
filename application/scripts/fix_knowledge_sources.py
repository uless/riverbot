import os
import sys
import re
import pandas as pd

# Add the parent directory to the Python path to access mappings
sys.path.append('..')

from mappings.knowledge_sources import knowledge_sources  # Import the dictionary

# Path to the newData folder and the Excel file
new_data_folder = '../newData'  # Adjusted path as script is in scripts/
csv_file_path = 'Resources.csv'  # Path to the Excel file
python_file_path = '../mappings/knowledge_sources.py'  # Path to the existing Python file


# Helper function to clean a filename by removing non-alphabetic characters
def clean_filename(filename):
    if isinstance(filename, str):  # Check if the filename is a string
        return re.sub(r'[^a-zA-Z]', '', filename)
    return ''  # Return empty string for non-string inputs

def load_existing_knowledge_sources(python_file):
    """Load existing knowledge sources from the Python file."""
    knowledge_sources_dict = {}
    with open(python_file, 'r') as f:
        exec(f.read(), knowledge_sources_dict)
    return knowledge_sources_dict.get('knowledge_sources', {})

def get_non_matching_files_and_extract_data(existing_sources):
    """Extract non-matching files from newData and CSV, appending to existing sources."""
    # List all PDF files in newData
    all_files_in_newdata = {f for f in os.listdir(new_data_folder) if f.endswith('.pdf')}
    
    # Read the CSV file
    df = pd.read_csv(csv_file_path)

    # Prepare a dictionary to store new entries
    new_entries = {}

    # Iterate over the DataFrame rows
    for index, row in df.iterrows():
        resource_name = row['Resource Name']
        link = row['Link']

        # Clean the resource name for comparison
        cleaned_resource_name = clean_filename(resource_name)

        # Proceed only if cleaned_resource_name is not empty
        if cleaned_resource_name:
            # Check if the cleaned resource name matches any PDF in newData
            for pdf in all_files_in_newdata:
                cleaned_pdf_name = clean_filename(pdf[:-4])  # Strip .pdf and clean
                
                if cleaned_pdf_name == cleaned_resource_name:
                    # Check if the PDF is already in existing sources
                    if pdf not in existing_sources:
                        # Create the entry for new sources
                        new_entries[pdf] = {
                            "url": link,
                            "description": resource_name
                        }
                    break  # Stop checking once a match is found

    print("Total files processed:", len(all_files_in_newdata))
    print("Total new matches found:", len(new_entries))

    return new_entries

def save_to_python_file(data, filename='knowledge_sources.py'):
    """Append new data to the existing Python file."""
    existing_sources = load_existing_knowledge_sources(filename)
    
    # Update existing sources with new entries
    existing_sources.update(data)

    # Write the updated knowledge sources back to the Python file
    with open(filename, 'w') as python_file:
        python_file.write("knowledge_sources = {\n")
        for key, value in existing_sources.items():
            python_file.write(f'    "{key}": {{\n')
            python_file.write(f'      "url": "{value["url"]}",\n')
            python_file.write(f'      "description": "{value["description"]}"\n')
            python_file.write('    },\n')
        python_file.write("}\n")
    print(f"Data has been saved to {filename}.")

# Example usage
if __name__ == "__main__":
    existing_sources = load_existing_knowledge_sources(python_file_path)
    new_entries = get_non_matching_files_and_extract_data(existing_sources)
    save_to_python_file(new_entries, python_file_path)