from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain.schema import Document
from langchain_community.embeddings import OllamaEmbeddings
from bs4 import BeautifulSoup
import tiktoken
import requests

def chunkIt(html_content, max_size=400, overlap=100):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # remove media and cosmetics
    for tag in soup.find_all(['img', 'video', 'audio', 'picture', 'iframe', 'object', 'embed', 'source', 'path']):
        tag.decompose()
    for tag in soup.find_all(['script', 'style', 'noscript']):
        tag.decompose()
    
    chunks = []
    current_chunk_elements = []
    current_chunk_size = 0


    ###############################################
    def get_top_level_elements(soup):
        body = soup.find('body')
        if body:
            return [child for child in body.children if hasattr(child, 'name')]
        else:
            return [child for child in soup.children if hasattr(child, 'name')]

    def create_chunk_from_elements(elements):
        if not elements:
            return ""
        
        wrapper = BeautifulSoup('<div></div>', 'html.parser').div
        for elem in elements:
            wrapper.append(elem.__copy__())
        return str(wrapper)
    ###############################################

    
    top_elements = get_top_level_elements(soup)
    
    if not top_elements:
        return [str(soup)]
    
    for element in top_elements:
        element_html = str(element)
        element_size = len(element_html)
        
        if element_size > max_size:
            if current_chunk_elements:
                chunk_html = create_chunk_from_elements(current_chunk_elements)
                chunks.append(chunk_html)
                current_chunk_elements = []
                current_chunk_size = 0

            
            chunks.append(element_html)
            continue

        
        if current_chunk_size + element_size > max_size and current_chunk_elements:
            chunk_html = create_chunk_from_elements(current_chunk_elements)
            chunks.append(chunk_html)

            if overlap > 0 and current_chunk_elements:
                current_chunk_elements = [current_chunk_elements[-1], element]
                current_chunk_size = len(str(current_chunk_elements[-2])) + element_size
            else:
                current_chunk_elements = [element]
                current_chunk_size = element_size
        else:
            current_chunk_elements.append(element)
            current_chunk_size += element_size

    
    if current_chunk_elements:
        chunk_html = create_chunk_from_elements(current_chunk_elements)
        chunks.append(chunk_html)
    
    return chunks

# store both the plain text representation and the html structured chunks.
# search on the plain text and work with html documents.
class DualRepresentationVectorDB:
    def __init__(self, p_d='./chroma'):
        self.embeddings = OllamaEmbeddings(
            base_url="http://localhost:11434",
            model="mxbai-embed-large"
        )
        self.vectorstore = None
        self.persist_directory = p_d

    def extract_plain_text(self, html_chunk):
        soup = BeautifulSoup(html_chunk, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    
    def extract_plain_text_with_key_attrs(self, html_chunk):
        soup = BeautifulSoup(html_chunk, "html.parser")
        texts = []
    
        for text in soup.get_text(separator=" ", strip=True).split():
            texts.append(text)
    
        # Important attributes, maybe helpful while searching.
        key_attrs = ["title", "alt", "onclick", "aria-label", "data-tooltip"]
        for tag in soup.find_all(attrs={attr: True for attr in key_attrs}):
            for attr in key_attrs:
                if tag.has_attr(attr):
                    val = tag[attr]
                    if isinstance(val, list):
                        texts.extend(val)
                    else:
                        texts.append(str(val).strip())
    
        return " ".join(texts)
    
    def add_chunks(self, html_chunks, metadata_list=None):
        if metadata_list is None:
            metadata_list = [{"chunk_index": i} for i in range(len(html_chunks))]
        
        documents = []
        for i, (html_chunk, meta) in enumerate(zip(html_chunks, metadata_list)):
            plain_text = self.extract_plain_text(html_chunk)
            # Store HTML in metadata
            meta['original_html'] = html_chunk  
            
            documents.append(Document(
                page_content=plain_text,
                metadata=meta
            ))
        
        if self.vectorstore is None:
            self.vectorstore = Chroma.from_documents(
                documents, self.embeddings, persist_directory=self.persist_directory
            )
        else:
            self.vectorstore.add_documents(documents)
    
    def search_with_html_context(self, query, k=5):
        if not self.vectorstore:
            return []
            
        q_emb = self.embeddings.embed_query(query)
        
        results = self.vectorstore._collection.query(
            query_embeddings=[q_emb],
            n_results=k,
            include=["documents","metadatas"]
        )
        docs, metas = results["documents"][0], results["metadatas"][0]
        out = []
        for doc, meta in zip(docs, metas):
            out.append({
                "plain_text": doc,
                "structured_html": meta["original_html"],
                "metadata": meta,
            })
        return out

def create_dual_vector_db(html_content, max_size=1000):
    chunks = chunkIt(html_content, max_size)
    vector_db = DualRepresentationVectorDB()
    vector_db.add_chunks(chunks)
    return vector_db

def llm(sys, prompt):
    pr = {
        "model": "gemma3:4b",
        "messages": [
            {
                "role": "system",
                "content": (
                    sys
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 250
    }
    resp = requests.post("http://localhost:11434/v1/chat/completions", json=pr)

    if resp.ok:
        return resp.json()["choices"][0]["message"]["content"].strip()
    else:
        return "Could not connect to LLM"

def question_rewrite(ques):
    q = "You are a smart query rewriter. "\
        "Take the user’s input and output only a concise, "\
        "self-contained question that could be asked directly to an API or assistant. "\
        "Do not ask for more information, just rewrite."
    return llm(q, ques)

def rag_pipeline(html_content: str, raw_query: str) -> str:
    rewritten = question_rewrite(raw_query)

    vector_db = create_dual_vector_db(html_content)
    results = vector_db.search_with_html_context(rewritten, k=5)

    context = "\n\n".join([r['structured_html'] for r in results])
    user_prompt = f"Context:\n{context}\n\nQuestion: {rewritten}"

    ans = llm(
        "You are an assistant. Answer based on the provided context. "
        "If unable to answer, say you cannot find the information.",
        user_prompt
    )

    return ans
