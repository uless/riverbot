import os
import re
import uuid
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings

def add_document_with_metadata(db, text_splitter, file_path, splits):
    file_name = os.path.basename(file_path)

    # Check if it's a PDF file
    if bool(re.match(r".*\.pdf$", file_path, re.IGNORECASE)):
        loader = PyPDFLoader(file_path)
    else:
        print(f"Unsupported file type: {file_path}")
        return

    # Load the document
    data = loader.load()
    print("Data length:", len(data))

    # Process each document in the loaded data (PDFs can contain multiple documents)
    for doc in data:
        print("Adding: ", file_path)
        doc.metadata['id'] = str(uuid.uuid4())  # Adding unique ID
        doc.metadata['source'] = file_path      # Adding file path
        doc.metadata['name'] = file_name        # Adding file name

        # Split the document into chunks
        chunks = text_splitter.split_documents([doc])

        # Propagate metadata to each chunk
        for chunk in chunks:
            chunk.metadata = doc.metadata.copy()  # Ensure each chunk gets a copy of the metadata
            splits.append(chunk)

def main():
    # Initialize components
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    embeddings = OpenAIEmbeddings()
    db = Chroma(persist_directory='docs/chroma/', embedding_function=embeddings)

    # Specify the PDF file path to process
    file_path = "newData/100+ Water Saving Tips.pdf"  # Replace with the path to your PDF file

    # Validate the file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    # Prepare to store document splits
    splits = []
    
    # Process the PDF file
    add_document_with_metadata(db, text_splitter, file_path, splits)

    # Add the processed documents (splits) to the database
    try:
        db.add_documents(documents=splits)
        print(f"Successfully added {len(splits)} document chunks to ChromaDB.")
    except Exception as e:
        print(f"Failed to add documents to ChromaDB: {e}")

if __name__ == "__main__":
    main()
