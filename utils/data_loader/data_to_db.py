###########################################################################
#####                   REQUIRES REFACTOR                             #####
###########################################################################


import os
import re
from langchain_experimental.agents.agent_toolkits import create_python_agent
from langchain_community.agents import load_tools, initialize_agent
from langchain_community.agents import AgentType
#from langchain_community.tools.python.tool import PythonREPLTool
from langchain_community.python import PythonREPL
from langchain_community.chat_models import ChatOpenAI
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.indexes import VectorstoreIndexCreator
from langchain_community.vectorstores import DocArrayInMemorySearch
from langchain_community.chains import RetrievalQA
from langchain_community.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_community.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader
api_key_file_path = 'openai_api_key.txt'

# Read the API key from the file
with open(api_key_file_path, 'r') as file:
    api_key = file.read().strip()

# Set the API key for OpenAI
os.environ['OPENAI_API_KEY'] = api_key
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 1500,
    chunk_overlap = 150
)

directory_path = "../Data/"
file_pattern_txt = "./*.txt"
file_pattern_pdf = "./*.pdf"

#loader = DirectoryLoader(directory_path, glob=file_pattern, loader_cls=PyPDFLoader)
#loader = DirectoryLoader("../Data/", glob = "./*.txt", loader_cls = TextLoader, encoding='utf-8')
persist_directory = 'docs/chroma/'

sample_file_path = "../Data/phx_waterquality_2022.pdf"
loader = PyPDFLoader(sample_file_path)
data = loader.load()
splits = text_splitter.split_documents(data)

# Walk through the directory and its subdirectories
for root, dirs, files in os.walk(directory_path):
    for file in files:
        # Get the full path of the current file
        file_path = os.path.join(root, file)
        print('file path', file_path)
        if bool(re.match(r".*\.txt$", file_path, re.IGNORECASE)):
            print('text file found')
            loader = TextLoader(file_path, encoding ='utf-8')
            data = loader.load()
        elif bool(re.match(r".*\.pdf$", file_path, re.IGNORECASE)):
            print('pdf file found')
            loader = PyPDFLoader(file_path)
            print('loader_type_pdf',type(loader))
            data = loader.load()


        splits.extend(text_splitter.split_documents(data))
# print(splits)
embeddings = OpenAIEmbeddings()

vectordb = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory=persist_directory
)
print('execution done')
