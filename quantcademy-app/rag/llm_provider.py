"""
QuantCademy LLM Provider
Capstone-grade RAG with:
- Citation-required answers
- Confidence gating
- Source-tiered responses
"""

import os
import re
from typing import Generator, Union, Optional, List, Dict, Tuple
from pathlib import Path

# Load environment variables - try multiple locations
try:
    from dotenv import load_dotenv
    # Try loading from quantcademy-app directory first
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Fallback to default location
        load_dotenv()
except ImportError:
    pass

# Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash-latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Import providers based on availability
GEMINI_AVAILABLE = False
OLLAMA_AVAILABLE = False
genai = None
_gemini_client = None  # New SDK uses Client

# Try new package first (google-genai) — uses Client API
try:
    import google.genai as _genai_module
    genai = _genai_module
    if GEMINI_API_KEY:
        _gemini_client = _genai_module.Client(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
except (ImportError, AttributeError):
    # Fallback to old package name for compatibility
    try:
        import google.generativeai as genai
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            GEMINI_AVAILABLE = True
    except (ImportError, AttributeError):
        genai = None
        pass

try:
    import requests
    OLLAMA_AVAILABLE = True
except ImportError:
    pass


# System prompt for capstone-grade RAG tutor
SYSTEM_PROMPT = """You are QuantCademy AI, a capstone-grade investment education tutor. You provide CITATION-BACKED answers grounded in authoritative sources.

## YOUR ROLE
- Teach investing concepts accurately and simply
- ALWAYS cite your sources in your answers
- Never give specific financial advice or stock picks
- Refuse to recommend individual stocks - explain why index funds are better
- Emphasize that investing involves risk

## CITATION REQUIREMENTS (CRITICAL)
1. ALWAYS include a "Sources:" line at the end of your response
2. Cite the source tier when possible (e.g., "According to SEC regulations...")
3. When sources conflict, prefer higher-tier sources:
   - Tier 1 (Highest): SEC, FINRA, IRS, Treasury
   - Tier 2: Federal Reserve, CFA Institute, Vanguard Research
   - Tier 3: Fidelity, Schwab, Bogleheads
   - Tier 4: Investopedia, NerdWallet
4. If context is insufficient, say "I don't have enough reliable sources to answer this confidently"

## REFUSAL POLICY
REFUSE to answer and explain why for:
- "Which stock should I buy?" → Explain index fund benefits instead
- "Is [stock] a good investment?" → Explain diversification instead
- "When will the market go up/down?" → Explain market unpredictability
- Questions outside your knowledge → Admit limitations

## RESPONSE LENGTH
- Simple definitions or yes/no questions: 40-60 words
- Conceptual explanations or "how/why" questions: 80-120 words
- Multi-part or comparison questions: up to 150 words
- NEVER exceed 150 words unless the user explicitly asks for more detail

## RESPONSE FORMAT
1. Key definitions in **bold**
2. One practical example max
3. **End with:** "Sources: [list sources]"

## TEACHING STYLE
- Beginner-friendly, clear, and brief
- One analogy max
- Be honest about what you don't know
"""


# Stock picking refusal messages
STOCK_PICKING_TRIGGERS = [
    "which stock", "what stock", "best stock", "good stock",
    "should i buy", "will stock", "should i invest in",
    "is tesla", "is apple", "is nvidia", "is amazon",
    "meme stock", "penny stock"
]

STOCK_PICKING_REFUSAL = """
## I Can't Recommend Specific Stocks 🚫

I'm designed to help you learn about investing, not to pick stocks. Here's why:

**According to SEC and FINRA guidelines:**
- 90%+ of professional stock pickers underperform index funds over 15+ years
- Individual stock picking exposes you to concentrated company risk
- Even experts can't reliably predict which stocks will outperform

**What I CAN help with:**
- Understanding how index funds work (and why they beat most stock pickers)
- Building a diversified portfolio appropriate for your goals
- Explaining risk management and asset allocation
- Teaching you about retirement accounts (401k, IRA)

**A better approach for most investors:**
A simple 3-fund portfolio (US stocks, international stocks, bonds via low-cost index funds) has historically outperformed most active investors while requiring almost no effort.

Would you like me to explain how to build a diversified portfolio instead?

*Sources: SEC Investor.gov, FINRA, SPIVA Research*
"""


def _trim_to_last_sentence(text: str) -> str:
    """Trim text to the last complete sentence so it doesn't end mid-thought."""
    if not text:
        return text
    # Find last sentence-ending punctuation (. ! ? or markdown list/header line)
    # We look for '. ', '.\n', '!', '?' at the end, or the text already ends cleanly
    stripped = text.rstrip()
    if stripped and stripped[-1] in '.!?':
        return stripped
    # Find the last sentence boundary
    match = list(re.finditer(r'[.!?](?:\s|$|\n|"|\*)', stripped))
    if match:
        last = match[-1]
        return stripped[:last.start() + 1].rstrip()
    # No sentence boundary found — return as-is (better than empty)
    return stripped


def _should_refuse_stock_picking(query: str) -> bool:
    """Check if the query is asking for stock picks."""
    query_lower = query.lower()
    return any(trigger in query_lower for trigger in STOCK_PICKING_TRIGGERS)


def check_llm_status() -> dict:
    """Check which LLM providers are available."""
    status = {
        "provider": LLM_PROVIDER,
        "status": "offline",
        "message": "",
        "gemini_available": GEMINI_AVAILABLE,
        "ollama_available": False
    }
    
    if LLM_PROVIDER == "gemini" and GEMINI_AVAILABLE:
        try:
            if _gemini_client is not None:
                # New SDK: use Client
                _gemini_client.models.list()
                status["status"] = "online"
                status["message"] = f"Gemini ({GEMINI_MODEL})"
                status["available"] = True
                return status
            elif genai is not None and hasattr(genai, 'GenerativeModel'):
                # Old SDK: use GenerativeModel
                model = genai.GenerativeModel(GEMINI_MODEL)
                status["status"] = "online"
                status["message"] = f"Gemini ({GEMINI_MODEL})"
                status["available"] = True
                return status
        except Exception as e:
            status["message"] = f"Gemini error: {str(e)}"
            status["available"] = False
    
    if LLM_PROVIDER == "ollama" or not GEMINI_AVAILABLE:
        try:
            import requests
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                status["ollama_available"] = True
                if any('llama3' in name.lower() for name in model_names):
                    status["status"] = "online"
                    status["message"] = "Ollama (llama3)"
                else:
                    status["message"] = "Ollama online but llama3 not found"
        except Exception:
            pass
    
    if status["status"] == "offline":
        if not GEMINI_API_KEY:
            status["message"] = "No GEMINI_API_KEY in .env"
        elif not GEMINI_AVAILABLE:
            status["message"] = f"Gemini package not available. Install: pip install google-genai (or google-generativeai)"
        elif genai is None:
            status["message"] = "Gemini module failed to import"
        else:
            status["message"] = "No LLM provider available"
        status["available"] = False
    else:
        status["available"] = True
    
    return status


def chat_with_llm(
    message: str,
    context: str = "",
    citations: str = "",
    confidence: float = 1.0,
    is_confident: bool = True,
    refusal_reason: str = None,
    conversation_history: list = None,
    stream: bool = True
) -> Union[Generator[str, None, None], str]:
    """
    Send a message to the configured LLM with RAG context and citations.
    
    Args:
        message: User's question
        context: Retrieved context from knowledge base (with source attribution)
        citations: Formatted citation string to include
        confidence: Retrieval confidence score (0-1)
        is_confident: Whether we have enough reliable sources
        refusal_reason: Why we can't answer (if not confident)
        conversation_history: Previous messages
        stream: Whether to stream the response
    
    Yields/Returns:
        Response text with citations
    """
    # Check for stock picking request FIRST
    if _should_refuse_stock_picking(message):
        if stream:
            def refuse_gen():
                yield STOCK_PICKING_REFUSAL
            return refuse_gen()
        return STOCK_PICKING_REFUSAL
    
    # Check confidence gate
    if not is_confident and refusal_reason:
        refusal_response = f"""
## I Don't Have Enough Information ⚠️

{refusal_reason}

**What you can do:**
- Try rephrasing your question
- Ask about a more specific topic
- Ask me about: asset allocation, retirement accounts, index funds, compound interest, or risk management

I only answer when I have reliable sources to back up my response.
"""
        if stream:
            def refusal_gen():
                yield refusal_response
            return refusal_gen()
        return refusal_response
    
    # Build the augmented prompt with context and citation requirements
    augmented_message = f"""CONTEXT FROM TRUSTED FINANCIAL EDUCATION SOURCES (Confidence: {confidence:.0%}):
{context}

REQUIRED CITATIONS TO INCLUDE:
{citations}

USER QUESTION: {message}

INSTRUCTIONS:
1. Answer the user's question using ONLY the context above
2. Be accurate and beginner-friendly
3. Include specific examples when helpful
4. ALWAYS end your response with "Sources: " followed by the citations provided above
5. If the context doesn't fully cover the topic, acknowledge limitations
6. DO NOT make up information not in the context"""

    # Try Gemini first
    if LLM_PROVIDER == "gemini" and GEMINI_AVAILABLE:
        return _chat_with_gemini(augmented_message, conversation_history, stream)
    
    # Fall back to Ollama
    if OLLAMA_AVAILABLE:
        return _chat_with_ollama(augmented_message, conversation_history, stream)
    
    # No provider available
    error_msg = "❌ No LLM provider available. Please check your .env configuration."
    if stream:
        def error_generator():
            yield error_msg
        return error_generator()
    return error_msg


def _chat_with_gemini(
    message: str,
    conversation_history: list = None,
    stream: bool = True
) -> Union[Generator[str, None, None], str]:
    """Chat using Google Gemini (supports both new and old SDK)."""
    
    # Try new SDK (google-genai with Client) first
    if _gemini_client is not None:
        return _chat_with_gemini_new_sdk(message, conversation_history, stream)
    
    # Fallback to old SDK (google-generativeai with GenerativeModel)
    if genai is not None and hasattr(genai, 'GenerativeModel'):
        return _chat_with_gemini_old_sdk(message, conversation_history, stream)
    
    error_msg = "❌ Gemini module not available. Install: pip install google-genai"
    if stream:
        def error_gen():
            yield error_msg
        return error_gen()
    return error_msg


def _chat_with_gemini_new_sdk(
    message: str,
    conversation_history: list = None,
    stream: bool = True
) -> Union[Generator[str, None, None], str]:
    """Chat using the new google-genai SDK (Client API)."""
    try:
        # Build contents with conversation history
        contents = []
        if SYSTEM_PROMPT:
            contents.append({"role": "user", "parts": [{"text": f"[System] {SYSTEM_PROMPT}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })
        
        contents.append({"role": "user", "parts": [{"text": message}]})
        
        # Use the model name - strip "models/" prefix if present for the new SDK
        model_name = GEMINI_MODEL
        if model_name.startswith("models/"):
            model_name = model_name[7:]
        
        if stream:
            def generate():
                response = _gemini_client.models.generate_content_stream(
                    model=model_name,
                    contents=contents
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            return generate()
        else:
            response = _gemini_client.models.generate_content(
                model=model_name,
                contents=contents
            )
            return response.text
            
    except Exception as e:
        error_msg = f"❌ Gemini error: {str(e)}"
        if stream:
            def error_gen():
                yield error_msg
            return error_gen()
        return error_msg


def _chat_with_gemini_old_sdk(
    message: str,
    conversation_history: list = None,
    stream: bool = True
) -> Union[Generator[str, None, None], str]:
    """Chat using the old google-generativeai SDK (GenerativeModel API)."""
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT
        )
        
        # Build chat history
        history = []
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = "user" if msg.get("role") == "user" else "model"
                history.append({
                    "role": role,
                    "parts": [msg.get("content", "")]
                })
        
        chat = model.start_chat(history=history)
        
        if stream:
            def generate():
                response = chat.send_message(message, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            return generate()
        else:
            response = chat.send_message(message)
            return response.text
            
    except Exception as e:
        error_msg = f"❌ Gemini error: {str(e)}"
        if stream:
            def error_gen():
                yield error_msg
            return error_gen()
        return error_msg


def _chat_with_ollama(
    message: str,
    conversation_history: list = None,
    stream: bool = True
) -> Union[Generator[str, None, None], str]:
    """Chat using Ollama."""
    import requests
    import json
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if conversation_history:
        for msg in conversation_history[-6:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    
    messages.append({"role": "user", "content": message})
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 1024
        }
    }
    
    try:
        if stream:
            def generate():
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    json=payload,
                    stream=True,
                    timeout=120
                )
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if 'message' in data and 'content' in data['message']:
                                yield data['message']['content']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
            return generate()
        else:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=120
            )
            data = response.json()
            return data.get('message', {}).get('content', 'No response generated.')
            
    except Exception as e:
        error_msg = f"❌ Ollama error: {str(e)}"
        if stream:
            def error_gen():
                yield error_msg
            return error_gen()
        return error_msg
