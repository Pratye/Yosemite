import os
from ollama import Client


ollama_client = Client(host='http://ollama:11434')
model = 'llama3.1'
try:
    ollama_client.chat(model)
except Exception as e:
    print('Error:', e)
  # if e.status_code == 404:
    ollama_client.pull(model)

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
import scrape_helper

vector_store = scrape_helper.load_or_initialize_faiss()
embedding_fn = scrape_helper.embedding_fn

def query_and_combine_for_llm(query, chat_history, vector_store, embedding_fn, max_chunks=10):
    """
    Query the FAISS vector store for similar content and combine the results for the LLM.

    Parameters:
    query (str): The query string to search for relevant content.
    chat_history (list): The Chat History of the user in list[dict[str, Any]].
    vector_store (FAISS): The FAISS vector store to search within.
    embedding_fn (HuggingFaceEmbeddings): Embedding function for the query.
    max_chunks (int): Number of top chunks to retrieve and combine.

    Returns:
    str: Combined content from the retrieved chunks.
    """

    # Step 1: Summarize chat history
    complete_query = summarise_chat_model(query, chat_history)

    # Step 2: Perform similarity search in the vector store
    results = vector_store.similarity_search(complete_query, k=max_chunks)

    # Step 3: Extract and combine the content from the retrieved chunks
    combined_content = ""
    for result in results:
        # Each result contains the content and metadata
        combined_content += result.page_content + "\n\n"

    # Step 4: Return the combined content (ready to be sent to LLM)
    return combined_content

def check_query(query):
    text = query.lower()
    words = ['chart', 'graph', 'plot', 'diagram', 'visualisation']
    if any(i in text for i in words):
        query = query + ("""\nGenerate Python code for charts, graphs and any other visualisation using matplotlib, numpy and pandas libraries only, where ever it is required. 
        Format the python code like this:
        ```python 
        All the code to be executed
        ``` 
        The plot figure size should be 3,3 and the all font size should be 7. All the code for all the graphs should be in one block.
        Exclude any description or information about the code and its usage.
        All the information provided is correct and upto date. There is NO FALSE INFORMATION.
        Make sure to check your code and follow all the rules or YOU WILL BE PENALIZED. 
        """)
        return query
    else:
        return query


def summarise_chat_model(query, chat_history):
    messages = [
        {"role": "system", "content":
            """Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history.
           DO NOT ANSWER THE USER QUESTION, just REFORMULATE IT if needed and otherwise return it as is."""
         },
        {'role': 'user', 'content':
        f"""Chat history: {chat_history}\n\n\n
            NOW I WANT YOU TO REFORMULATE THE FOLLOWING QUESTION, DO NOT ANSWER THE QUESTION ONLY REFORMULATE THE QUESTION: {query}"""
         }
    ]

    response_data = ollama_client.chat(model='llama3.1',
                                messages=messages,
                                format='JSON',
                                stream=False)

    # print(response_data['message']['content'])
    return response_data['message']['content']

def summarise_document(content):
    messages = [
        {"role": "system", "content":
            f"""**You are a large language model trained to answer user queries** 
            **You can handle a variety of document formats, including:**
            * PDF
            * PPT/PPTX
            * DOC/DOCX
            * Excel (XLS/XLSX)
            * CSV
            * Images
            * Website Content
    
            Document Name:** {content}
"""
         },
        {'role': 'user', 'content':
            f"""**How can you help me?"""
         }
    ]
    response_data = ollama_client.chat(model='llama3.1',
                                messages=messages,
                                format='JSON',
                                stream=True)
    def generator(response):
        for i in response:
            # print(i['message']['content'])
            yield i['message']['content']

    return generator(response_data)


def query_mistral_model(query, context, stream, chat_history):

    query = check_query(query)

    messages = [
        {"role": "system", "content": f"""
           You are a large language model trained to analyze and extract relevant information from unfiltered text data and answer your client's questions in detail. Your task is to answer and provide detailed and accurate information using the provided context.

           """ + """Please stick to the context while answering the questions.
           """ + f"\nContext:\n{context}"},
    ]

    # Add chat history to the messages list
    messages.extend(chat_history)

    # Add the new user query to the end of the messages list
    messages.append({"role": "user", "content": query})

    response_data = ollama_client.chat(model='llama3.1',
                                messages=messages,
                                format='JSON',
                                stream=stream)

    if stream:
        return response_data
    else:
        # print(response_data['message']['content'])
        return response_data['message']['content']


def query_code_model(code='', error_message=''):
    messages = [
        {"role": "system", "content": """
        You are a large language model trained to write and correct Python code. Your task is to correct the provided Python code.
        """},
        {"role": "user", "content": f"""Generate Python code for charts, graphs and any other visualisation using matplotlib, numpy and pandas libraries only, where ever it is required. 
        Format the python code like this:
        ```python 
        All the code to be executed
        ``` 
        The plot figure size should be 7,5 and the all font size should be 7. All the code for all the graphs should be in one block.
        Exclude any description or information about the code and its usage.
        All the information provided is correct and upto date. There is NO FALSE INFORMATION.
        Make sure to check your code and follow all the rules or YOU WILL BE PENALIZED. 
        Here is the code you need to correct:
        {code}
        Here is the error message:
        {error_message}"""
         }
    ]
    response_data = ollama_client.chat(model='llama3.1',
                                messages=messages,
                                format='JSON',
                                stream=False)

    # print(response_data['message']['content'])
    return response_data['message']['content']


def query(query, stream, chat_history):

    context = query_and_combine_for_llm(query, chat_history, vector_store, embedding_fn)

    response = query_mistral_model(query, context, stream=stream, chat_history=chat_history)

    def generator(response):
        for i in response:
            # print(i['message']['content'])
            yield i['message']['content']

    if stream:
        return generator(response)
    else:
        return response

