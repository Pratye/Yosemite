from uuid import uuid4
import requests
from bs4 import BeautifulSoup
import sqlite3
import time
from datetime import datetime
import pytesseract
import pdfplumber
import io
import os
import faiss
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore import InMemoryDocstore
from langchain.docstore.document import Document


# Initialize the HuggingFace model
model_name = 'sentence-transformers/all-MiniLM-L6-v2'
embedding_model = SentenceTransformer(model_name)


# Embeddings function for HuggingFace
class HuggingFaceEmbeddings:
    def __init__(self, model):
        self.model = model

    def embed(self, texts):
        return self.model.encode(texts, convert_to_tensor=True).cpu().numpy()


embedding_fn = HuggingFaceEmbeddings(embedding_model)

# Path for storing the FAISS index
FAISS_INDEX_PATH = "./instance/faiss_index_store.faiss"


# Initialize FAISS vectorstore with persistence handling
def load_or_initialize_faiss():
    """
    Load the FAISS index from the disk if it exists, otherwise initialize a new FAISS index.
    """
    dimension = 384  # Dimension size for 'all-MiniLM-L6-v2' embeddings

    if os.path.exists(FAISS_INDEX_PATH):
        # Load the existing FAISS index
        # print(f"Loaded existing FAISS index from {FAISS_INDEX_PATH}.")

        return FAISS.load_local('./instance/faiss_index_store.faiss', embedding_fn.embed, allow_dangerous_deserialization=True)
        # index = faiss.read_index(FAISS_INDEX_PATH)
    else:
        # Create a new FAISS index
        index = faiss.IndexFlatL2(dimension)
        # print(f"Initialized a new FAISS index.")

    # Return the FAISS VectorStore
        return FAISS(embedding_fn.embed, index, docstore=InMemoryDocstore(),index_to_docstore_id={},)


# Save the FAISS index to disk
def save_faiss_index(vector_store):
    """
    Save the FAISS index to disk for future use.
    """
    vector_store.save_local(FAISS_INDEX_PATH)
    # print(f"FAISS index saved to {FAISS_INDEX_PATH}.")


# Initialize the FAISS Vectorstore
vector_store = load_or_initialize_faiss()

# Text splitter for chunking content
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)


# Function to save data to vector DB with persistence
def save_to_vector_db(content, metadata):
    """
    Save the given content and metadata to FAISS vector store after chunking and embedding.

    Parameters:
    content (str): The content to be stored.
    metadata (dict): Metadata including URL and timestamp.
    """

    # Split the content into smaller chunks
    texts = text_splitter.split_text(content)

    # Embed each chunk using the sentence-transformer model
    # embeddings = embedding_fn.embed(texts)

    # Create Document objects with metadata
    docs = [Document(page_content=text, metadata=metadata) for text in texts]

    uuids = [str(uuid4()) for _ in range(len(docs))]

    # Add the texts and corresponding metadata to the FAISS vector store
    vector_store.add_documents(docs, ids=uuids)

    # print("Content and metadata added to vector DB.")

    # Save the updated FAISS index to disk for future use
    save_faiss_index(vector_store)

# SQLite setup for "to_scrape" and "scraped" databases
conn = sqlite3.connect('./instance/scraper.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS to_scrape (url TEXT PRIMARY KEY)''')
c.execute('''CREATE TABLE IF NOT EXISTS scraped (url TEXT PRIMARY KEY)''')
conn.commit()

# Add URL to "To Scrape" DB
def add_to_scrape_db(url):
    c.execute('INSERT OR IGNORE INTO to_scrape (url) VALUES (?)', (url,))
    conn.commit()

# Pop URL from "To Scrape" DB
def pop_from_scrape_db():
    c.execute('SELECT url FROM to_scrape LIMIT 1')
    result = c.fetchone()
    if result:
        url = result[0]
        c.execute('DELETE FROM to_scrape WHERE url=?', (url,))
        conn.commit()
        return url
    return None

# Check if URL is in "Scraped" DB
def is_scraped(url):
    c.execute('SELECT 1 FROM scraped WHERE url=?', (url,))
    return c.fetchone() is not None

# Mark URL as scraped
def mark_as_scraped(url):
    c.execute('INSERT OR IGNORE INTO scraped (url) VALUES (?)', (url,))
    conn.commit()

# Fetch HTML content
def fetch_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        # print(f"Failed to fetch {url}: {e}")
        return None

# Fetch PDF content
def fetch_pdf(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        # print(f"Failed to fetch PDF from {url}: {e}")
        return None

# Extract content from PDF using OCR
def extract_pdf_content(pdf_data):
    try:
        with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text()
        if not text:  # If text is empty, use OCR
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                for page in pdf.pages:
                    image = page.to_image()
                    text += pytesseract.image_to_string(image.original)
        return text
    except Exception as e:
        # print(f"Failed to extract content from PDF: {e}")
        return None

# Extract URLs from a webpage
def extract_urls(soup, base_url):
    urls = set()
    for link in soup.find_all('a', href=True):
        url = requests.compat.urljoin(base_url, link['href'])
        urls.add(url)
    return urls

# Save extracted content with metadata
def save_content_to_db(content, url, timestamp):
    metadata = {
        "url": url,
        "timestamp": timestamp,
        # "content": content
    }
    save_to_vector_db(content, metadata)


def extract_content_with_jina(url):
    jina_url = f'https://r.jina.ai/{url}'
    try:
        response = requests.get(jina_url)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        # print(f"Failed to fetch content from Jina AI for {url}: {e}")
        return None
def scrape_data(url):
    if url.endswith('.pdf'):
        # If it's a PDF link
        pdf_data = fetch_pdf(url)
        if pdf_data:
            content = extract_pdf_content(pdf_data)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_content_to_db(content, url, timestamp)
            return content
        else:
            return ''
    else:
        # Scrape webpage
        html_content = fetch_html(url)
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            page_content = extract_content_with_jina(url)
            save_content_to_db(page_content, url, timestamp)

            # Extract URLs and add to "To Scrape" DB
            new_urls = extract_urls(soup, url)
            for new_url in new_urls:
                add_to_scrape_db(new_url)

            return page_content
        else:
            return ''


def main_scraping_loop():
    sleep_time = 1
    max_sleep_time = 300  # 5 minutes in seconds
    while True:
        max_requests_per_minute = 20
        time_window = 60  # seconds
        request_times = []
        url = pop_from_scrape_db()
        if not url:
            # print("No URLs left to scrape.")
            time.sleep(sleep_time)
            sleep_time = min(sleep_time * 2, max_sleep_time)  # Increase sleep time gradually
            continue

        if is_scraped(url):
            # print(f"URL already scraped: {url}")
            continue

        # Rate limiting logic
        current_time = time.time()
        request_times = [t for t in request_times if current_time - t < time_window]

        if len(request_times) >= max_requests_per_minute:
            sleep_time_jina = time_window - (current_time - request_times[0])
            # print(f"Rate limit reached. Sleeping for {sleep_time_jina:.2f} seconds.")
            time.sleep(sleep_time_jina)

        # print(f"Scraping URL: {url}")
        scrape_data(url)
        mark_as_scraped(url)
        # Add delay to avoid rate limits
        request_times.append(time.time())
