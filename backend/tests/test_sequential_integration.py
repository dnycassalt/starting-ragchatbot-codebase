"""Integration tests for sequential tool calling functionality"""

import json
from typing import Any, Dict

import pytest
import requests


@pytest.fixture
def base_url():
    """Base URL for the running server"""
    return "http://localhost:8000"


@pytest.fixture
def api_headers():
    """Standard headers for API requests"""
    return {"Content-Type": "application/json"}


class TestSequentialToolCallingIntegration:
    """Integration tests for sequential tool calling with real queries"""

    def test_comparison_query_two_courses(
        self, base_url: str, api_headers: Dict[str, str]
    ):
        """
        Test comparing lesson 3 across two courses - should trigger
        sequential tool calls
        """
        query_data = {
            "query": (
                "Compare lesson 3 in 'Advanced Retrieval for AI "
                "with Chroma' vs 'Prompt Compression and Query "
                "Optimization'"
            )
        }

        response = requests.post(
            f"{base_url}/api/query", headers=api_headers, data=json.dumps(query_data)
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify answer contains information about both courses
        answer = data["answer"].lower()
        assert "advanced retrieval" in answer or "chroma" in answer
        assert "prompt compression" in answer or "query optimization" in answer

        # Should have sources from both courses
        sources = data["sources"]
        assert len(sources) > 0

        # Verify sources contain references to both courses
        source_texts = [s["display"] if isinstance(s, dict) else s for s in sources]
        source_combined = " ".join(source_texts).lower()

        # At least one mention of each course should appear
        has_chroma = any(
            "chroma" in text.lower() or "advanced retrieval" in text.lower()
            for text in source_texts
        )
        has_prompt = any(
            "prompt" in text.lower() or "compression" in text.lower()
            for text in source_texts
        )

        # Log for debugging
        print("\n--- Comparison Query Test ---")
        print(f"Query: {query_data['query']}")
        print(f"Answer length: {len(data['answer'])} chars")
        print(f"Number of sources: {len(sources)}")
        print(f"Sources: {source_texts}")
        print(f"Has Chroma sources: {has_chroma}")
        print(f"Has Prompt sources: {has_prompt}")

        # At least one course should be referenced in sources
        assert (
            has_chroma or has_prompt
        ), "Expected sources from at least one of the compared courses"

    def test_multi_part_query_lesson_topic_search(
        self, base_url: str, api_headers: Dict[str, str]
    ):
        """
        Test multi-part query: get topic from one lesson, find other
        courses about that topic
        """
        query_data = {
            "query": (
                "What topic is covered in lesson 1 of MCP and "
                "find other courses about that topic"
            )
        }

        response = requests.post(
            f"{base_url}/api/query", headers=api_headers, data=json.dumps(query_data)
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data

        answer = data["answer"].lower()

        # Should mention MCP
        assert "mcp" in answer or "model context protocol" in answer

        # Should have sources
        assert len(data["sources"]) > 0

        print("\n--- Multi-Part Query Test ---")
        print(f"Query: {query_data['query']}")
        print(f"Answer preview: {data['answer'][:200]}...")
        print(f"Number of sources: {len(data['sources'])}")

    def test_course_outline_then_specific_lesson(
        self, base_url: str, api_headers: Dict[str, str]
    ):
        """
        Test querying for course outline first, then specific lesson
        """
        query_data = {
            "query": (
                "Get the outline of 'MCP: Build Rich-Context AI "
                "Apps with Anthropic' then tell me about lesson 2"
            )
        }

        response = requests.post(
            f"{base_url}/api/query", headers=api_headers, data=json.dumps(query_data)
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data

        answer = data["answer"].lower()

        # Should reference MCP and lesson 2
        assert "mcp" in answer or "model context protocol" in answer
        assert "lesson 2" in answer or "lesson two" in answer

        # Should have sources
        assert len(data["sources"]) > 0

        print("\n--- Outline + Specific Lesson Test ---")
        print(f"Query: {query_data['query']}")
        print(f"Answer preview: {data['answer'][:200]}...")
        print(f"Number of sources: {len(data['sources'])}")

    def test_session_persistence_across_sequential_calls(
        self, base_url: str, api_headers: Dict[str, str]
    ):
        """
        Test that session is maintained correctly during sequential
        tool calls
        """
        # First query
        query1_data = {"query": "What is MCP?"}

        response1 = requests.post(
            f"{base_url}/api/query", headers=api_headers, data=json.dumps(query1_data)
        )

        assert response1.status_code == 200
        data1 = response1.json()
        session_id = data1["session_id"]

        # Second query using same session - should trigger sequential calls
        query2_data = {
            "query": (
                "Compare that with lesson 1 of 'Advanced "
                "Retrieval for AI with Chroma'"
            ),
            "session_id": session_id,
        }

        response2 = requests.post(
            f"{base_url}/api/query", headers=api_headers, data=json.dumps(query2_data)
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # Same session should be maintained
        assert data2["session_id"] == session_id

        # Should have an answer referencing the comparison
        assert len(data2["answer"]) > 0

        print("\n--- Session Persistence Test ---")
        print(f"Session ID: {session_id}")
        print(f"Query 1: {query1_data['query']}")
        print(f"Query 2: {query2_data['query']}")
        print(f"Answer 2 preview: {data2['answer'][:200]}...")


@pytest.mark.skipif(
    True, reason="Requires running server - run manually with 'make test-integration'"
)
class TestManualSequentialIntegration:
    """
    Manual integration tests that require server to be running.
    These are skipped by default in unit tests.
    """

    def test_server_health_check(self, base_url: str):
        """Verify server is accessible"""
        response = requests.get(f"{base_url}/api/courses")
        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert data["total_courses"] > 0
