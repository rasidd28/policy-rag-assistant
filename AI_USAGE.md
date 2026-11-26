# AI_USAGE.md — AI Tool Usage & Corrections

## AI Tools Used

| Tool | Purpose |
|------|---------|
| **Antigravity (Claude Sonnet)** | Primary coding assistant — generated project structure, all Python code, tests, CI/CD, documentation |
| **Groq API (llama-3.1-8b)** | Runtime LLM for answering policy questions |

---

## Three Mistakes the AI Made That I Fixed

### Mistake 1: Import order caused circular dependency

**What the AI did:**  
The AI initially generated `app/agent/agent.py` with a top-level import of `app.core.vector_store` and `app.core.pdf_ingestion` at the module level. This caused a circular import because `pdf_ingestion` → `config` → settings were sometimes imported before the `.env` file was loaded.

**How it went wrong:**  
Running `pytest tests/test_rag.py` produced:  
```
ImportError: cannot import name 'settings' from partially initialized module 'app.core.config'
```

**How I fixed it:**  
Moved the `vector_store` import inside the function body (lazy import) in the agent's fallback code path, ensuring it only imports when needed after the full initialization chain completes.

---

### Mistake 2: ChromaDB collection query returned error when empty

**What the AI did:**  
The AI wrote `vector_store.search()` to call `collection.query(n_results=top_k, ...)` without checking if the collection was empty first. ChromaDB raises an exception when querying an empty collection.

**How it went wrong:**  
On the very first startup before PDFs were indexed, any test or health check that triggered a search would crash with:  
```
chromadb.errors.InvalidCollectionException: Collection is empty
```

**How I fixed it:**  
Added `min(top_k, collection.count())` guard in the search function:
```python
results = collection.query(
    n_results=min(top_k, collection.count()),  # ← fix
    ...
)
```
And added an early return if `collection.count() == 0`.

---

### Mistake 3: Async tests not properly configured for pytest

**What the AI did:**  
The AI generated `async def test_...()` functions in the test files but didn't add the `asyncio_mode = "auto"` setting to `pyproject.toml`. It also missed that `pytest-asyncio` requires explicit configuration in newer versions.

**How it went wrong:**  
Running `pytest tests/test_rag.py` produced:  
```
PytestUnraisableExceptionWarning: coroutine 'test_tc01_air_travel_class' was never awaited
```
Tests appeared to pass but actually never ran the async code.

**How I fixed it:**  
Added to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```
And added `pytest_plugins = ["pytest_asyncio"]` to `conftest.py`. This made all `async def test_*` functions automatically run with the asyncio event loop.
