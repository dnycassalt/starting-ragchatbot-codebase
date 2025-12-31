"""Tests for VectorStore ChromaDB interaction"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from vector_store import VectorStore, SearchResults


class TestVectorStoreSearch:
    """Test VectorStore search functionality"""

    def test_search_without_filters(self, mock_chroma_client, sample_chroma_query_result, test_config):
        """Test basic search with no course or lesson filters"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Execute search
                results = store.search("test query")

                # Verify search was called correctly
                store.course_content.query.assert_called_once()
                call_args = store.course_content.query.call_args

                assert call_args[1]['query_texts'] == ["test query"]
                assert call_args[1]['n_results'] == 5
                assert call_args[1].get('where') is None  # No filter

                # Verify results
                assert not results.is_empty()
                assert len(results.documents) == 2
                assert results.error is None

    def test_search_with_course_filter(self, mock_chroma_client, sample_chroma_query_result, test_config):
        """Test search with course name filter"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Mock course name resolution
                with patch.object(store, '_resolve_course_name', return_value="Introduction to MCP"):
                    results = store.search("test query", course_name="MCP")

                # Verify course name was resolved
                store._resolve_course_name.assert_called_once_with("MCP")

                # Verify search called with filter
                call_args = store.course_content.query.call_args
                assert call_args[1].get('where') == {"course_title": "Introduction to MCP"}

    def test_search_with_lesson_filter(self, mock_chroma_client, sample_chroma_query_result, test_config):
        """Test search with lesson number filter"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                results = store.search("test query", lesson_number=2)

                # Verify filter applied
                call_args = store.course_content.query.call_args
                assert call_args[1].get('where') == {"lesson_number": 2}

    def test_search_with_both_filters(self, mock_chroma_client, sample_chroma_query_result, test_config):
        """Test search with course and lesson filters"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                with patch.object(store, '_resolve_course_name', return_value="Introduction to MCP"):
                    results = store.search("test query", course_name="MCP", lesson_number=1)

                # Verify compound filter
                call_args = store.course_content.query.call_args
                expected_filter = {
                    "$and": [
                        {"course_title": "Introduction to MCP"},
                        {"lesson_number": 1}
                    ]
                }
                assert call_args[1].get('where') == expected_filter

    def test_search_with_unmatched_course(self, mock_chroma_client, test_config):
        """Test search when course name doesn't match any course"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Mock course resolution failure
                with patch.object(store, '_resolve_course_name', return_value=None):
                    results = store.search("test query", course_name="NonexistentCourse")

                # Verify error result
                assert results.is_empty()
                assert results.error is not None
                assert "No course found matching 'NonexistentCourse'" in results.error

    def test_search_with_chroma_exception(self, mock_chroma_client, test_config):
        """DIAGNOSTIC: Test search when ChromaDB raises exception"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Make query raise exception
                store.course_content.query.side_effect = Exception("ChromaDB connection failed")

                results = store.search("test query")

                # Verify error is captured
                assert results.is_empty()
                assert results.error is not None
                assert "Search error: ChromaDB connection failed" in results.error


class TestCourseNameResolution:
    """Test course name resolution and semantic matching"""

    def test_resolve_course_name_exact_match(self, mock_chroma_client, test_config):
        """Test course name resolution with exact title"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Mock catalog query result
                store.course_catalog.query.return_value = {
                    'documents': [["Introduction to MCP"]],
                    'metadatas': [[{"title": "Introduction to MCP"}]]
                }

                result = store._resolve_course_name("Introduction to MCP")

                assert result == "Introduction to MCP"
                store.course_catalog.query.assert_called_once()

    def test_resolve_course_name_partial_match(self, mock_chroma_client, test_config):
        """Test course name resolution with partial/fuzzy match"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Mock catalog query for partial match
                store.course_catalog.query.return_value = {
                    'documents': [["Introduction to MCP"]],
                    'metadatas': [[{"title": "Introduction to MCP"}]]
                }

                result = store._resolve_course_name("MCP")

                assert result == "Introduction to MCP"

    def test_resolve_course_name_no_match(self, mock_chroma_client, test_config):
        """Test course name resolution when no courses match"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Mock empty result
                store.course_catalog.query.return_value = {
                    'documents': [[]],
                    'metadatas': [[]]
                }

                result = store._resolve_course_name("XYZ")

                assert result is None

    def test_resolve_course_name_with_exception(self, mock_chroma_client, test_config):
        """Test course name resolution when ChromaDB raises error"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Make catalog query raise exception
                store.course_catalog.query.side_effect = Exception("Database error")

                result = store._resolve_course_name("MCP")

                assert result is None


class TestDataAddition:
    """Test adding course data to vector store"""

    def test_add_course_metadata(self, mock_chroma_client, sample_course, test_config):
        """Test adding course to catalog"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                store.add_course_metadata(sample_course)

                # Verify add was called
                store.course_catalog.add.assert_called_once()
                call_args = store.course_catalog.add.call_args[1]

                # Verify structure
                assert call_args['documents'] == ["Introduction to MCP"]
                assert call_args['ids'] == ["Introduction to MCP"]
                assert call_args['metadatas'][0]['title'] == "Introduction to MCP"
                assert call_args['metadatas'][0]['instructor'] == "Test Instructor"
                assert 'lessons_json' in call_args['metadatas'][0]

    def test_add_course_content(self, mock_chroma_client, sample_course_chunks, test_config):
        """Test adding course chunks to content collection"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                store.add_course_content(sample_course_chunks)

                # Verify add was called
                store.course_content.add.assert_called_once()
                call_args = store.course_content.add.call_args[1]

                # Verify data structure
                assert len(call_args['documents']) == 3
                assert len(call_args['metadatas']) == 3
                assert len(call_args['ids']) == 3

                # Check first chunk
                assert call_args['metadatas'][0]['course_title'] == "Introduction to MCP"
                assert call_args['metadatas'][0]['lesson_number'] == 1

    def test_add_empty_course_content(self, mock_chroma_client, test_config):
        """Test adding empty chunk list"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                store.add_course_content([])

                # Verify add was NOT called
                store.course_content.add.assert_not_called()


class TestLinkRetrieval:
    """Test course and lesson link retrieval"""

    def test_get_course_link_success(self, mock_chroma_client, test_config):
        """Test retrieving course link"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Mock get response
                store.course_catalog.get.return_value = {
                    'metadatas': [{
                        'title': 'Introduction to MCP',
                        'course_link': 'https://example.com/mcp'
                    }]
                }

                link = store.get_course_link("Introduction to MCP")

                assert link == 'https://example.com/mcp'
                store.course_catalog.get.assert_called_once_with(ids=["Introduction to MCP"])

    def test_get_lesson_link_success(self, mock_chroma_client, test_config):
        """Test retrieving lesson link"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Mock get response with lessons
                store.course_catalog.get.return_value = {
                    'metadatas': [{
                        'lessons_json': '[{"lesson_number": 1, "lesson_title": "Getting Started", "lesson_link": "https://example.com/mcp/lesson1"}]'
                    }]
                }

                link = store.get_lesson_link("Introduction to MCP", 1)

                assert link == 'https://example.com/mcp/lesson1'

    def test_get_lesson_link_no_lesson(self, mock_chroma_client, test_config):
        """Test retrieving link for non-existent lesson"""
        with patch('chromadb.PersistentClient', return_value=mock_chroma_client):
            with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
                store = VectorStore(
                    chroma_path=test_config.CHROMA_PATH,
                    embedding_model=test_config.EMBEDDING_MODEL,
                    max_results=test_config.MAX_RESULTS
                )

                # Mock get response without matching lesson
                store.course_catalog.get.return_value = {
                    'metadatas': [{
                        'lessons_json': '[{"lesson_number": 1, "lesson_title": "Getting Started", "lesson_link": "https://example.com/mcp/lesson1"}]'
                    }]
                }

                link = store.get_lesson_link("Introduction to MCP", 99)

                assert link is None


class TestSearchResultsClass:
    """Test SearchResults dataclass"""

    def test_from_chroma(self, sample_chroma_query_result):
        """Test creating SearchResults from ChromaDB response"""
        results = SearchResults.from_chroma(sample_chroma_query_result)

        assert len(results.documents) == 2
        assert len(results.metadata) == 2
        assert len(results.distances) == 2
        assert results.error is None
        assert not results.is_empty()

    def test_empty_results(self):
        """Test creating empty SearchResults with error"""
        results = SearchResults.empty("Test error message")

        assert results.is_empty()
        assert results.error == "Test error message"
        assert len(results.documents) == 0

    def test_is_empty_check(self):
        """Test is_empty() method"""
        empty = SearchResults(documents=[], metadata=[], distances=[])
        not_empty = SearchResults(documents=["test"], metadata=[{}], distances=[0.5])

        assert empty.is_empty()
        assert not not_empty.is_empty()
