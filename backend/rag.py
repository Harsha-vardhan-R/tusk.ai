# app.py - COMPLETE RAG WITH YOUR FULL PROMPT, NO LANGCHAIN
from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
import requests
import re
from dataclasses import dataclass
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    html: str
    text: str
    score: float

def chunkIt(html_content, max_size=400, overlap=100):
    """YOUR ORIGINAL CHUNKING - UNCHANGED"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # remove media and cosmetics
    for tag in soup.find_all(['img', 'video', 'audio', 'picture', 'iframe', 'object', 'embed', 'source', 'path']):
        tag.decompose()
    for tag in soup.find_all(['script', 'style', 'noscript']):
        tag.decompose()
    
    chunks = []
    current_chunk_elements = []
    current_chunk_size = 0

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

def simple_search(query: str, chunks: list, k=5) -> list:
    """Simple but effective TF-IDF search"""
    query_words = re.findall(r'\w{3,}', query.lower())
    
    results = []
    for chunk_html in chunks:
        soup = BeautifulSoup(chunk_html, 'html.parser')
        chunk_text = soup.get_text()
        chunk_words = re.findall(r'\w{3,}', chunk_text.lower())
        
        if not chunk_words:
            continue
            
        query_hits = sum(chunk_words.count(word) for word in query_words)
        score = query_hits / len(chunk_words)
        
        results.append(Chunk(chunk_html, chunk_text, score))
    
    return sorted(results, key=lambda x: x.score, reverse=True)[:k]

def llm(sys_prompt: str, user_prompt: str) -> str:
    """Direct Ollama API call"""
    payload = {
        "model": "gemma3:4b",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0,
        "max_tokens": 250
    }
    
    try:
        resp = requests.post(
            "http://localhost:11434/v1/chat/completions",
            json=payload,
            timeout=30
        )
        if resp.ok:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return f"LLM Error: {resp.status_code}"
    except Exception as e:
        return f"Ollama Error: {str(e)}"

def question_rewrite(ques: str) -> str:
    """Query rewriter - YOUR ORIGINAL LOGIC"""
    q = (
        "You are a smart query rewriter. "
        "Take the user's input and output only a concise, "
        "self-contained question that could be asked directly to an API or assistant. "
        "Do not ask for more information, just rewrite."
    )
    return llm(q, ques)

# YOUR FULL ORIGINAL SYSTEM PROMPT - UNCHANGED
FULL_SYSTEM_PROMPT = """You are an intelligent web page content analyst assistant integrated into a browser extension. Your role is to:

1. **Answer questions** about web page content provided to you
2. **Generate data** (CSV, JSON, tables, structured formats) from page content when requested
3. **Handle out-of-context requests** gracefully (greetings, general knowledge questions)
4. **Extract and transform** information from raw HTML page data

### Key Instructions:

**Context Awareness:**
- You will receive extracted content from web pages as context
- The context may include HTML structure, text, tables, lists, and metadata
- Treat this context as the primary source of truth for answering questions
- If information isn't in the context, clearly state 'This information is not available on the page'

**Response Types:**

1. **Information Queries** - Answer questions about page content
   - Use only the provided context
   - Cite where the information came from on the page
   - Be specific and concise
   
2. **Data Generation** - User asks for CSV, JSON, tables, or structured exports
   - Extract relevant data from the context
   - Format exactly as requested
   - Include headers and structure
   - For CSV: use proper escaping for commas and quotes
   - For JSON: valid, properly formatted JSON
   - Return ONLY the file content, no explanations

3. **General Requests** - Greetings, general knowledge, or conversational requests
   - Answer normally if context isn't needed
   - Example: 'What is the capital of France?' → 'Paris'
   - Example: 'Hi, how are you?' → Friendly response
   - Example: 'Explain machine learning' → Brief explanation

**Output Format Rules:**
- **Default (Q&A):** Natural language response
- **File Generation:** Return the exact file content with no preamble or postamble
- **Error Cases:** Explain what's missing or why you can't fulfill the request
- **Ambiguity:** Ask clarifying questions if needed"""

def rag_pipeline(html_content: str, raw_query: str) -> str:
    """YOUR FULL RAG PIPELINE - EXACT SAME LOGIC"""
    if not html_content or not raw_query:
        return "Error: Missing HTML content or query"

    try:
        # 1. Query rewrite
        rewritten = question_rewrite(raw_query)
        logger.info(f"Rewritten: {rewritten}")

        # 2. Chunk HTML (YOUR ORIGINAL)
        chunks = chunkIt(html_content, max_size=1000)

        # 3. Search top chunks
        results = simple_search(rewritten, chunks, k=5)

        if not results:
            return "No relevant content found on the page"

        context = "\n\n".join([r.html for r in results])
        user_prompt = f"Context:\n{context}\n\nQuestion: {rewritten}"

        # 5. YOUR FULL SYSTEM PROMPT
        ans = llm(FULL_SYSTEM_PROMPT, user_prompt)

        return ans
        
    except Exception as e:
        return f"Pipeline error: {str(e)}"

@app.route('/')
def home():
    return "🚀 Flask RAG Server Running on port 5000!"

@app.route('/health/<name>')
def health(name):
    return f"'Hello': {name}"

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.route('/prompt', methods=['POST'])
def generateOutput():
    """YOUR ORIGINAL ENDPOINT"""
    data = request.get_json()

    if data is None:
        return jsonify({"error": "Missing arguments for the POST request"})

    prompt = data.get("prompt")
    context = data.get("context")

    result = rag_pipeline(context, prompt)

    print(result)

    return jsonify({
        "success": True,
        "response": result
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
