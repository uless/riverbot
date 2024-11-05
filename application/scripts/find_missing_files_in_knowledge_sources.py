import os
import sys
import re

# Add the parent directory to the Python path to access mappings
sys.path.append('..')

from mappings.knowledge_sources import knowledge_sources  # Import the dictionary

# Path to the newData folder and the second text file
new_data_folder = '../newData'  # Adjusted path as script is in scripts/
second_file_path = 'master_file.txt'  # Text file with filenames without extensions

# Helper function to clean a filename by removing non-alphabetic characters
def clean_filename(filename):
    return re.sub(r'[^a-zA-Z]', '', filename)

def get_non_matching_files():
    # Get a set of all PDF file names in knowledge_sources
    known_files = set(knowledge_sources.keys())

    # List all PDF files in newData
    all_files_in_newdata = {f for f in os.listdir(new_data_folder) if f.endswith('.pdf')}
    
    # Read filenames from the second file (without extensions) and clean them
    with open(second_file_path, 'r') as f:
        filenames_without_extension = {clean_filename(line.strip()) for line in f}

    # Find files in newData that do not match any cleaned filename in the second file
    non_matching_files = {
        f for f in all_files_in_newdata
        if clean_filename(f[:-4]) not in filenames_without_extension  # Remove .pdf and clean for comparison
    }

    print("Out of", len(all_files_in_newdata), "files in newData,", len(non_matching_files), "files have no match in the second file.")
    return non_matching_files

# Example usage
if __name__ == "__main__":
    non_matching_files = get_non_matching_files()
    print("Files in newData with no match in the second file:", non_matching_files)
