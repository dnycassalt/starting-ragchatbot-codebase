"""Shared test fixtures for RAG chatbot tests"""
import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import Course, Lesson, CourseChunk
from vector_store import SearchResults
from config import Config


# ==================== Configuration Fixtures ====================

@pytest.fixture
def test_config():
    """Test configuration with safe defaults"""
    return Config(
        ANTHROPIC_API_KEY="test-api-key-123",
        ANTHROPIC_MODEL="claude-sonnet-4-20250514",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=100,
        MAX_RESULTS=5,
        MAX_HISTORY=2,
        MAX_TOOL_ROUNDS=2,
        CHROMA_PATH="./test_chroma_db"
    )


# ==================== Sample Data Fixtures ====================

@pytest.fixture
def sample_course():
    """Sample Course object for testing"""
    return Course(
        title="Introduction to MCP",
        course_link="https://example.com/mcp",
        instructor="Test Instructor",
        lessons=[
            Lesson(
                lesson_number=1,
                title="Getting Started with MCP",
                lesson_link="https://example.com/mcp/lesson1"
            ),
            Lesson(
                lesson_number=2,
                title="Advanced MCP Features",
                lesson_link="https://example.com/mcp/lesson2"
            )
        ]
    )


@pytest.fixture
def sample_course_chunks():
    """Sample CourseChunk objects for testing"""
    return [
        CourseChunk(
            content="MCP stands for Model Context Protocol. It is a powerful framework for building AI applications.",
            course_title="Introduction to MCP",
            lesson_number=1,
            chunk_index=0
        ),
        CourseChunk(
            content="Advanced MCP features include server implementations, resource handling, and tool integration.",
            course_title="Introduction to MCP",
            lesson_number=2,
            chunk_index=1
        ),
        CourseChunk(
            content="MCP enables seamless communication between AI models and external data sources.",
            course_title="Introduction to MCP",
            lesson_number=1,
            chunk_index=2
        )
    ]


@pytest.fixture
def sample_search_results():
    """Sample SearchResults object with documents and metadata"""
    return SearchResults(
        documents=[
            "MCP stands for Model Context Protocol. It is a powerful framework.",
            "Advanced MCP features include server implementations and tool integration."
        ],
        metadata=[
            {
                "course_title": "Introduction to MCP",
                "lesson_number": 1,
                "chunk_index": 0
            },
            {
                "course_title": "Introduction to MCP",
                "lesson_number": 2,
                "chunk_index": 1
            }
        ],
        distances=[0.3, 0.5],
        error=None
    )


@pytest.fixture
def sample_chroma_query_result():
    """Raw ChromaDB query result structure"""
    return {
        'documents': [[
            "MCP stands for Model Context Protocol. It is a powerful framework.",
            "Advanced MCP features include server implementations."
        ]],
        'metadatas': [[
            {"course_title": "Introduction to MCP", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Introduction to MCP", "lesson_number": 2, "chunk_index": 1}
        ]],
        'distances': [[0.3, 0.5]],
        'ids': [["MCP_0", "MCP_1"]]
    }


# ==================== Mock ChromaDB Fixtures ====================

@pytest.fixture
def mock_embedding_function():
    """Mock SentenceTransformer embedding function"""
    mock = Mock()
    mock.return_value = [[0.1] * 384]  # 384-dimensional embedding
    return mock


@pytest.fixture
def mock_chroma_collection(sample_chroma_query_result):
    """Mock ChromaDB collection with query capabilities"""
    mock = Mock()

    # Default successful query
    mock.query.return_value = sample_chroma_query_result

    # Default add operation
    mock.add.return_value = None

    # Default get operation
    mock.get.return_value = {
        'ids': ['Introduction to MCP'],
        'metadatas': [{
            'title': 'Introduction to MCP',
            'instructor': 'Test Instructor',
            'course_link': 'https://example.com/mcp',
            'lessons_json': '[{"lesson_number": 1, "lesson_title": "Getting Started", "lesson_link": "https://example.com/mcp/lesson1"}]',
            'lesson_count': 1
        }]
    }

    return mock


@pytest.fixture
def mock_chroma_client(mock_chroma_collection):
    """Mock ChromaDB PersistentClient"""
    mock_client = Mock()

    # get_or_create_collection returns our mock collection
    mock_client.get_or_create_collection.return_value = mock_chroma_collection

    # delete_collection doesn't raise errors
    mock_client.delete_collection.return_value = None

    return mock_client


# ==================== Mock Anthropic API Fixtures ====================

@pytest.fixture
def mock_anthropic_response_no_tool():
    """Mock Anthropic response without tool use (direct answer)"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    # Create mock content block with text
    mock_text_block = Mock()
    mock_text_block.text = "This is a test response from Claude."
    mock_text_block.type = "text"

    mock_response.content = [mock_text_block]

    return mock_response


@pytest.fixture
def mock_anthropic_response_with_tool():
    """Mock Anthropic response with tool_use (needs tool execution)"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    # Create mock tool_use content block
    mock_tool_block = Mock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.id = "tool_123"
    mock_tool_block.name = "search_course_content"
    mock_tool_block.input = {
        "query": "What is MCP?",
        "course_name": "MCP"
    }

    mock_response.content = [mock_tool_block]

    return mock_response


@pytest.fixture
def mock_anthropic_final_response():
    """Mock final Anthropic response after tool execution"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    mock_text_block = Mock()
    mock_text_block.text = "Based on the search results, MCP stands for Model Context Protocol."
    mock_text_block.type = "text"

    mock_response.content = [mock_text_block]

    return mock_response


@pytest.fixture
def mock_anthropic_client(mock_anthropic_response_no_tool):
    """Mock Anthropic client with messages.create() method"""
    mock_client = Mock()

    # Default to no-tool response
    mock_client.messages.create.return_value = mock_anthropic_response_no_tool

    return mock_client


# ==================== Mock VectorStore Fixtures ====================

@pytest.fixture
def mock_vector_store(sample_search_results):
    """Mock VectorStore with sample data"""
    from vector_store import VectorStore

    mock = Mock(spec=VectorStore)

    # Default successful search
    mock.search.return_value = sample_search_results

    # Course name resolution
    mock._resolve_course_name.return_value = "Introduction to MCP"

    # Link retrieval
    mock.get_course_link.return_value = "https://example.com/mcp"
    mock.get_lesson_link.return_value = "https://example.com/mcp/lesson1"

    # Course metadata
    mock.get_course_count.return_value = 4
    mock.get_existing_course_titles.return_value = [
        "Introduction to MCP",
        "Advanced Python",
        "Web Development",
        "Data Science"
    ]

    # Data addition methods
    mock.add_course_metadata.return_value = None
    mock.add_course_content.return_value = None

    return mock


# ==================== Mock ToolManager Fixtures ====================

@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager with tool execution"""
    from search_tools import ToolManager

    mock = Mock(spec=ToolManager)

    # Tool definitions
    mock.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in the course content"},
                    "course_name": {"type": "string", "description": "Course title (partial matches work)"},
                    "lesson_number": {"type": "integer", "description": "Specific lesson number"}
                },
                "required": ["query"]
            }
        }
    ]

    # Tool execution returns formatted results
    mock.execute_tool.return_value = "[Introduction to MCP - Lesson 1]\nMCP stands for Model Context Protocol."

    # Source tracking
    mock.get_last_sources.return_value = [
        {
            "display": "Introduction to MCP - Lesson 1",
            "url": "https://example.com/mcp/lesson1"
        }
    ]

    mock.reset_sources.return_value = None

    return mock


# ==================== Mock SessionManager Fixtures ====================

@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for conversation history"""
    from session_manager import SessionManager

    mock = Mock(spec=SessionManager)

    # Session creation
    mock.create_session.return_value = "test-session-123"

    # History retrieval
    mock.get_conversation_history.return_value = "User: Previous question\nAssistant: Previous answer"

    # Message management
    mock.add_exchange.return_value = None
    mock.add_message.return_value = None

    # Session deletion
    mock.delete_session.return_value = True

    return mock


# ==================== FastAPI Testing Fixtures ====================

@pytest.fixture
def mock_rag_system(mock_vector_store, mock_tool_manager, mock_session_manager):
    """Mock RAGSystem for API testing"""
    from rag_system import RAGSystem

    mock = Mock(spec=RAGSystem)

    # Core components
    mock.vector_store = mock_vector_store
    mock.tool_manager = mock_tool_manager
    mock.session_manager = mock_session_manager

    # Query method returns answer and sources
    mock.query.return_value = (
        "This is a test response about MCP.",
        [
            {
                "display": "Introduction to MCP - Lesson 1",
                "url": "https://example.com/mcp/lesson1"
            }
        ]
    )

    # Course analytics
    mock.get_course_analytics.return_value = {
        "total_courses": 4,
        "course_titles": [
            "Introduction to MCP",
            "Advanced Python",
            "Web Development",
            "Data Science"
        ]
    }

    return mock


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app with mocked RAG system"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Union, Dict

    # Create test app
    app = FastAPI(title="Test RAG System")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Union[str, Dict[str, Optional[str]]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Define endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        from fastapi import HTTPException
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        from fastapi import HTTPException
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        from fastapi import HTTPException
        try:
            deleted = mock_rag_system.session_manager.delete_session(session_id)
            if deleted:
                return {"status": "success", "message": f"Session {session_id} deleted"}
            else:
                return {"status": "not_found", "message": f"Session {session_id} not found"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "Course Materials RAG System", "status": "running"}

    return app


@pytest.fixture
async def async_client(test_app):
    """Async test client for FastAPI testing"""
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
