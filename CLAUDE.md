# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retrieval-Augmented Generation (RAG) chatbot** for querying educational course materials. The system uses semantic search with ChromaDB and Claude AI's tool-calling capabilities to provide context-aware answers about course content.

**Key Architecture**: Full-stack web app with FastAPI backend, vanilla JavaScript frontend, ChromaDB vector database, and Anthropic Claude AI integration.

**CRITICAL**: This project uses `uv` for all Python operations.
- **NEVER** use `pip install` → use `uv add`
- **NEVER** use `python script.py` → use `uv run python script.py`
- **NEVER** use bare commands like `uvicorn` or `pytest` → use `uv run uvicorn` or `uv run pytest`

## Development Commands

### Running the Application

```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application runs at `http://localhost:8000` (web UI) and `http://localhost:8000/docs` (API docs).

### Dependency Management

**IMPORTANT**: Always use `uv` - never use `pip` directly.

```bash
# Install/sync dependencies
uv sync

# Add a new package
uv add package-name

# Remove a package
uv remove package-name

# Update dependencies
uv lock --upgrade

# Run Python scripts (ALWAYS use 'uv run python', never bare 'python')
uv run python script.py
uv run python -m module_name

# Run installed CLI tools (ALWAYS use 'uv run', never bare command)
uv run uvicorn app:app --reload
uv run pytest
uv run black .
uv run mypy .
```

### Environment Setup

Required: Create `.env` file in project root with:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture Deep Dive

### Request Flow Pattern

This system uses a **two-phase Claude API interaction** pattern that's critical to understand:

1. **Phase 1 - Tool Decision**: User query → Claude API (with tools available) → Claude decides whether to use `search_course_content` tool
2. **Phase 2 - Tool Execution**: If tool used → Execute semantic search → Return results to Claude → Claude synthesizes final answer

This is NOT a traditional RAG pattern where search happens before AI. Claude intelligently decides when course-specific search is needed versus answering from general knowledge.

### Core Components Interaction

**[backend/rag_system.py](backend/rag_system.py)** - Central orchestrator
- Coordinates all components (document processor, vector store, AI generator, session manager, tool manager)
- `query()` method is the main entry point for user queries
- Manages conversation history via `SessionManager`

**[backend/ai_generator.py](backend/ai_generator.py)** - Claude API wrapper
- `generate_response()`: Initial call with tools available
- `_handle_tool_execution()`: Executes tools and makes second API call with results
- System prompt (lines 8-30) defines Claude's behavior and tool usage guidelines

**[backend/search_tools.py](backend/search_tools.py)** - Tool definitions
- `CourseSearchTool`: Implements tool interface for Claude
- `ToolManager`: Registry pattern for managing multiple tools
- `last_sources` tracking: Sources are stored during search execution and retrieved after response generation

**[backend/vector_store.py](backend/vector_store.py)** - ChromaDB interface
- **Two collections**: `course_catalog` (course metadata) and `course_content` (searchable chunks)
- `_resolve_course_name()`: Semantic matching allows fuzzy course name queries (e.g., "MCP" matches "Introduction to MCP")
- `search()`: Unified interface that handles course resolution → filtering → content search

**[backend/document_processor.py](backend/document_processor.py)** - Document ingestion
- Parses course metadata from document headers (Course Title, Course Link, Instructor)
- Identifies lessons using pattern: `Lesson N: Title`
- Chunks text with sentence-aware splitting (800 chars with 100 char overlap)

**[backend/session_manager.py](backend/session_manager.py)** - Conversation state
- In-memory session storage (sessions lost on restart)
- Keeps last `MAX_HISTORY` exchanges (default: 2 = 4 messages total)
- History formatted as string and appended to system prompt

### Data Models ([backend/models.py](backend/models.py))

- `Course`: Container for course metadata + list of `Lesson` objects
- `Lesson`: Individual lesson with number, title, optional link
- `CourseChunk`: Vector storage unit with content + metadata (course_title, lesson_number, chunk_index)

### Configuration ([backend/config.py](backend/config.py))

Key settings that affect system behavior:
- `ANTHROPIC_MODEL`: `claude-sonnet-4-20250514`
- `EMBEDDING_MODEL`: `all-MiniLM-L6-v2` (384-dimensional, lightweight)
- `CHUNK_SIZE`: 800 characters
- `CHUNK_OVERLAP`: 100 characters
- `MAX_RESULTS`: 5 search results returned
- `MAX_HISTORY`: 2 conversation exchanges remembered
- `CHROMA_PATH`: `./chroma_db` (local persistent storage)

## Important Patterns & Constraints

### Document Loading
On startup ([backend/app.py](backend/app.py):88-98), the system:
1. Checks for `../docs` folder
2. Auto-loads all `.pdf`, `.docx`, `.txt` files
3. Skips already-indexed courses (checks ChromaDB for existing course titles)
4. Creates embeddings for all new content

**Adding new courses**: Drop files in `docs/` folder and restart server.

### Tool Execution Flow
When modifying tool behavior:
1. Tool definitions in `search_tools.py` must match Anthropic's tool schema
2. Tool execution returns **string** (not structured data) - Claude sees formatted text
3. Sources are tracked separately via `last_sources` attribute and retrieved by `ToolManager`
4. Tools are registered with `ToolManager` in `rag_system.py` initialization

### Session Management
- Sessions are created on first query if no `session_id` provided
- Frontend maintains `currentSessionId` across page refreshes (sessionStorage)
- Backend sessions are in-memory - all history lost on server restart
- History trimming happens automatically when `MAX_HISTORY * 2` messages exceeded

### Frontend Architecture ([frontend/](frontend/))
Simple vanilla JS with no build step:
- `script.js`: All client logic (fetch API, DOM manipulation, session management)
- `index.html`: Static HTML structure
- `style.css`: Styling
- Uses `marked.js` CDN for markdown rendering

**API Contract**:
- POST `/api/query`: `{query: string, session_id?: string}` → `{answer: string, sources: string[], session_id: string}`
- GET `/api/courses`: `{}` → `{total_courses: int, course_titles: string[]}`

## Modifying System Behavior

### Changing Claude's Instructions
Edit system prompt in [backend/ai_generator.py](backend/ai_generator.py):8-30. This controls:
- When Claude uses search tools vs. answering from knowledge
- Response formatting and tone
- How Claude interprets search results

### Adjusting Search Behavior
Modify [backend/config.py](backend/config.py):
- `MAX_RESULTS`: More results = more context but higher token costs
- `CHUNK_SIZE/OVERLAP`: Larger chunks = more context per result but fewer results fit in context window

### Adding New Tools
1. Create tool class implementing `Tool` interface in `search_tools.py`
2. Implement `get_tool_definition()` (returns Anthropic tool schema)
3. Implement `execute(**kwargs)` (returns string result)
4. Register in `rag_system.py` initialization: `self.tool_manager.register_tool(YourTool(...))`

### Rebuilding Vector Database
Delete `backend/chroma_db/` folder and restart server. All documents in `docs/` will be re-indexed.

## Common Gotchas

1. **Using pip instead of uv**: This project uses `uv` for dependency management. Always use `uv run` to execute Python commands, never bare `python` or `pip`.
2. **Empty responses after changes**: ChromaDB caches embeddings. Delete `backend/chroma_db/` to rebuild.
3. **Session history not working**: Sessions are in-memory. Every server restart clears all sessions.
4. **Course not found**: Course name resolution is semantic but requires some similarity. Very vague queries may not match.
5. **Sources not displaying**: Sources are tracked by `CourseSearchTool.last_sources` and reset after each query. Check `ToolManager.get_last_sources()`.
6. **CORS errors**: CORS is wide-open (`allow_origins=["*"]`) for development. Tighten before production.

## File Organization

```
backend/
├── app.py                  # FastAPI server & endpoints
├── rag_system.py          # Main orchestrator
├── ai_generator.py        # Claude API client
├── vector_store.py        # ChromaDB wrapper
├── search_tools.py        # Tool definitions & manager
├── document_processor.py  # Document parsing & chunking
├── session_manager.py     # Conversation history
├── models.py              # Pydantic data models
└── config.py              # Configuration settings

frontend/
├── index.html            # UI structure
├── script.js             # Client-side logic
└── style.css             # Styling

docs/                     # Course documents (auto-loaded)
```

## No Testing Infrastructure

This codebase currently has **no test suite**. If adding tests, consider testing:
- Document parsing logic (various file formats, malformed headers)
- Chunking algorithm (overlap calculation, sentence boundary detection)
- Vector search accuracy (semantic matching, filtering)
- Tool execution flow (mock Anthropic API responses)
- Session management (history trimming, concurrent sessions)
