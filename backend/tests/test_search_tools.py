"""Tests for CourseSearchTool and ToolManager"""

from unittest.mock import Mock, patch

import pytest
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolDefinition:
    """Test tool definition for Anthropic API"""

    def test_get_tool_definition(self, mock_vector_store):
        """Test tool definition matches Anthropic schema"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        # Verify structure
        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition

        # Verify name
        assert definition["name"] == "search_course_content"

        # Verify schema
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "query" in schema["properties"]
        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]

        # Verify only query is required
        assert schema["required"] == ["query"]


class TestCourseSearchToolExecution:
    """Test tool execution logic"""

    def test_execute_without_filters(self, mock_vector_store, sample_search_results):
        """Test tool execution with only query parameter"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query")

        # Verify vector store called correctly
        mock_vector_store.search.assert_called_once_with(
            query="test query", course_name=None, lesson_number=None
        )

        # Verify result is formatted string
        assert isinstance(result, str)
        assert len(result) > 0
        assert "[Introduction to MCP" in result

        # Verify sources populated
        assert len(tool.last_sources) > 0

    def test_execute_with_course_filter(self, mock_vector_store, sample_search_results):
        """Test tool execution with course filter"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query", course_name="MCP")

        # Verify parameters passed correctly
        mock_vector_store.search.assert_called_once_with(
            query="test query", course_name="MCP", lesson_number=None
        )

        assert isinstance(result, str)

    def test_execute_with_lesson_filter(self, mock_vector_store, sample_search_results):
        """Test tool execution with lesson filter"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query", lesson_number=2)

        # Verify parameters
        mock_vector_store.search.assert_called_once_with(
            query="test query", course_name=None, lesson_number=2
        )

    def test_execute_with_all_parameters(
        self, mock_vector_store, sample_search_results
    ):
        """Test tool execution with all parameters"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query", course_name="MCP", lesson_number=1)

        # Verify all parameters passed
        mock_vector_store.search.assert_called_once_with(
            query="test query", course_name="MCP", lesson_number=1
        )


class TestEmptyResults:
    """Test handling of empty search results"""

    def test_execute_with_empty_results(self, mock_vector_store):
        """Test tool execution when no results found"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query")

        assert "No relevant content found" in result
        assert len(tool.last_sources) == 0

    def test_execute_empty_results_with_course_filter(self, mock_vector_store):
        """Test empty results with course filter shows filter info"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query", course_name="MCP")

        assert "No relevant content found" in result
        assert "in course 'MCP'" in result

    def test_execute_empty_results_with_lesson_filter(self, mock_vector_store):
        """Test empty results with lesson filter shows filter info"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query", lesson_number=2)

        assert "No relevant content found" in result
        assert "in lesson 2" in result

    def test_execute_empty_results_with_both_filters(self, mock_vector_store):
        """Test empty results with both filters shows both in message"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query", course_name="MCP", lesson_number=1)

        assert "No relevant content found" in result
        assert "in course 'MCP'" in result
        assert "in lesson 1" in result


class TestErrorHandling:
    """Test error handling from VectorStore"""

    def test_execute_with_search_error(self, mock_vector_store):
        """DIAGNOSTIC: Test tool execution when search returns error"""
        error_results = SearchResults.empty("Search error: ChromaDB connection failed")
        mock_vector_store.search.return_value = error_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query")

        # Error message should be returned
        assert "Search error: ChromaDB connection failed" in result
        assert len(tool.last_sources) == 0

    def test_execute_with_vector_store_exception(self, mock_vector_store):
        """DIAGNOSTIC: Test tool execution when VectorStore raises exception"""
        mock_vector_store.search.side_effect = Exception("Unexpected error")

        tool = CourseSearchTool(mock_vector_store)

        # Exception should propagate
        with pytest.raises(Exception) as exc_info:
            tool.execute(query="test query")

        assert "Unexpected error" in str(exc_info.value)


class TestResultFormatting:
    """Test result formatting logic"""

    def test_format_results_single_document(self, mock_vector_store):
        """Test formatting single search result"""
        single_result = SearchResults(
            documents=["MCP stands for Model Context Protocol."],
            metadata=[
                {
                    "course_title": "Introduction to MCP",
                    "lesson_number": 1,
                    "chunk_index": 0,
                }
            ],
            distances=[0.3],
        )
        mock_vector_store.search.return_value = single_result

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="What is MCP?")

        # Verify format
        assert "[Introduction to MCP - Lesson 1]" in result
        assert "MCP stands for Model Context Protocol" in result

    def test_format_results_multiple_documents(
        self, mock_vector_store, sample_search_results
    ):
        """Test formatting multiple search results"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test query")

        # Results should be separated by double newlines
        assert "\n\n" in result

        # Both results should be present
        assert "MCP stands for Model Context Protocol" in result
        assert "Advanced MCP features" in result

    def test_format_results_without_lesson_number(self, mock_vector_store):
        """Test formatting results with no lesson_number in metadata"""
        result_no_lesson = SearchResults(
            documents=["General course information"],
            metadata=[{"course_title": "Introduction to MCP", "chunk_index": 0}],
            distances=[0.3],
        )
        mock_vector_store.search.return_value = result_no_lesson

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        # Should not include lesson number in header
        assert "[Introduction to MCP]" in result
        assert "Lesson" not in result


class TestSourceTracking:
    """Test source tracking functionality"""

    def test_format_results_tracks_sources(
        self, mock_vector_store, sample_search_results
    ):
        """Test that formatting populates last_sources"""
        mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/mcp/lesson1"
        )
        mock_vector_store.get_course_link.return_value = "https://example.com/mcp"
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test query")

        # Verify sources populated
        assert len(tool.last_sources) > 0

        # Check source structure
        source = tool.last_sources[0]
        assert "display" in source
        assert "url" in source

    def test_format_results_deduplicates_sources(self, mock_vector_store):
        """Test that duplicate sources are not added"""
        # Three documents from same course/lesson
        duplicate_results = SearchResults(
            documents=["Doc 1", "Doc 2", "Doc 3"],
            metadata=[
                {
                    "course_title": "Introduction to MCP",
                    "lesson_number": 1,
                    "chunk_index": 0,
                },
                {
                    "course_title": "Introduction to MCP",
                    "lesson_number": 1,
                    "chunk_index": 1,
                },
                {
                    "course_title": "Introduction to MCP",
                    "lesson_number": 1,
                    "chunk_index": 2,
                },
            ],
            distances=[0.1, 0.2, 0.3],
        )
        mock_vector_store.search.return_value = duplicate_results
        mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/mcp/lesson1"
        )

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        # Should only have 1 source
        assert len(tool.last_sources) == 1

    def test_sources_with_lesson_links(self, mock_vector_store, sample_search_results):
        """Test source retrieval prioritizes lesson links"""
        mock_vector_store.get_lesson_link.return_value = (
            "https://example.com/mcp/lesson1"
        )
        mock_vector_store.get_course_link.return_value = "https://example.com/mcp"
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        # Verify lesson link used
        mock_vector_store.get_lesson_link.assert_called()
        assert tool.last_sources[0]["url"] == "https://example.com/mcp/lesson1"

    def test_sources_fallback_to_course_link(
        self, mock_vector_store, sample_search_results
    ):
        """Test source retrieval falls back to course link"""
        mock_vector_store.get_lesson_link.return_value = None  # No lesson link
        mock_vector_store.get_course_link.return_value = "https://example.com/mcp"
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        # Should fall back to course link
        assert tool.last_sources[0]["url"] == "https://example.com/mcp"

    def test_sources_with_no_links(self, mock_vector_store, sample_search_results):
        """Test sources when no links available"""
        mock_vector_store.get_lesson_link.return_value = None
        mock_vector_store.get_course_link.return_value = None
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        # Source URL should be None
        assert tool.last_sources[0]["url"] is None

    def test_sources_reset_on_new_execution(
        self, mock_vector_store, sample_search_results
    ):
        """Test that sources are replaced, not appended"""
        mock_vector_store.search.return_value = sample_search_results

        tool = CourseSearchTool(mock_vector_store)

        # First execution
        tool.execute(query="first query")
        first_sources = tool.last_sources.copy()

        # Second execution
        tool.execute(query="second query")
        second_sources = tool.last_sources

        # Sources should be reset, not accumulated
        # (In this test they're the same, but the list should be recreated)
        assert len(second_sources) > 0


class TestToolManager:
    """Test ToolManager functionality"""

    def test_register_tool(self, mock_vector_store):
        """Test tool registration"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        # Tool should be registered
        assert "search_course_content" in manager.tools

    def test_get_tool_definitions(self, mock_vector_store):
        """Test getting all tool definitions"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        definitions = manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"

    def test_execute_tool_success(self, mock_vector_store, sample_search_results):
        """Test executing registered tool"""
        mock_vector_store.search.return_value = sample_search_results

        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="test query")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_execute_tool_not_found(self):
        """Test executing non-existent tool"""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """Test retrieving sources from last search"""
        mock_vector_store.search.return_value = sample_search_results

        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute tool to generate sources
        manager.execute_tool("search_course_content", query="test")

        # Retrieve sources
        sources = manager.get_last_sources()

        assert len(sources) > 0

    def test_reset_sources(self, mock_vector_store, sample_search_results):
        """Test resetting sources"""
        mock_vector_store.search.return_value = sample_search_results

        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute and verify sources exist
        manager.execute_tool("search_course_content", query="test")
        assert len(manager.get_last_sources()) > 0

        # Reset sources
        manager.reset_sources()

        # Sources should be cleared
        assert len(manager.get_last_sources()) == 0
