"""Tests for FastAPI endpoints"""
import pytest
from unittest.mock import Mock
from httpx import AsyncClient


@pytest.mark.api
class TestRootEndpoint:
    """Test root endpoint"""

    async def test_root_endpoint_returns_success(self, async_client):
        """Test root endpoint returns status message"""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Course Materials RAG System"
        assert data["status"] == "running"


@pytest.mark.api
class TestQueryEndpoint:
    """Test /api/query endpoint"""

    async def test_query_without_session_id(self, async_client, mock_rag_system):
        """Test query endpoint creates new session when not provided"""
        response = await async_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify session was created
        mock_rag_system.session_manager.create_session.assert_called_once()

        # Verify query was processed
        mock_rag_system.query.assert_called_once()

    async def test_query_with_existing_session_id(self, async_client, mock_rag_system):
        """Test query endpoint uses provided session ID"""
        test_session_id = "existing-session-123"

        response = await async_client.post(
            "/api/query",
            json={
                "query": "Tell me about advanced MCP features",
                "session_id": test_session_id
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response includes the same session ID
        assert data["session_id"] == test_session_id

        # Verify session manager was NOT asked to create new session
        mock_rag_system.session_manager.create_session.assert_not_called()

        # Verify query was called with correct session
        mock_rag_system.query.assert_called_once_with(
            "Tell me about advanced MCP features",
            test_session_id
        )

    async def test_query_returns_answer_and_sources(self, async_client, mock_rag_system):
        """Test query endpoint returns answer and sources from RAG system"""
        response = await async_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify answer matches mock return value
        assert data["answer"] == "This is a test response about MCP."

        # Verify sources are included
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) > 0

        # Verify source structure
        source = data["sources"][0]
        assert "display" in source
        assert "url" in source
        assert source["display"] == "Introduction to MCP - Lesson 1"

    async def test_query_with_empty_query_string(self, async_client):
        """Test query endpoint with empty query string"""
        response = await async_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still return 200 (validation handled by RAG system)
        assert response.status_code == 200

    async def test_query_missing_query_field(self, async_client):
        """Test query endpoint with missing required field"""
        response = await async_client.post(
            "/api/query",
            json={}
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    async def test_query_invalid_json(self, async_client):
        """Test query endpoint with invalid JSON"""
        response = await async_client.post(
            "/api/query",
            content="invalid json{",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 for malformed JSON
        assert response.status_code == 422

    async def test_query_handles_rag_system_error(self, async_client, mock_rag_system):
        """Test query endpoint handles errors from RAG system"""
        # Configure mock to raise exception
        mock_rag_system.query.side_effect = Exception("Database connection failed")

        response = await async_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        # Should return 500 for internal error
        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]


@pytest.mark.api
class TestCoursesEndpoint:
    """Test /api/courses endpoint"""

    async def test_get_courses_returns_analytics(self, async_client, mock_rag_system):
        """Test courses endpoint returns course analytics"""
        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify data matches mock return value
        assert data["total_courses"] == 4
        assert isinstance(data["course_titles"], list)
        assert len(data["course_titles"]) == 4

        # Verify RAG system was called
        mock_rag_system.get_course_analytics.assert_called_once()

    async def test_get_courses_returns_expected_course_list(self, async_client):
        """Test courses endpoint returns expected course titles"""
        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        expected_courses = [
            "Introduction to MCP",
            "Advanced Python",
            "Web Development",
            "Data Science"
        ]

        assert data["course_titles"] == expected_courses

    async def test_get_courses_handles_error(self, async_client, mock_rag_system):
        """Test courses endpoint handles errors gracefully"""
        # Configure mock to raise exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Vector store unavailable")

        response = await async_client.get("/api/courses")

        # Should return 500 for internal error
        assert response.status_code == 500
        assert "Vector store unavailable" in response.json()["detail"]


@pytest.mark.api
class TestSessionDeletionEndpoint:
    """Test /api/session/{session_id} DELETE endpoint"""

    async def test_delete_existing_session(self, async_client, mock_rag_system):
        """Test deleting an existing session"""
        session_id = "test-session-456"

        response = await async_client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify response indicates success
        assert data["status"] == "success"
        assert session_id in data["message"]

        # Verify session manager was called
        mock_rag_system.session_manager.delete_session.assert_called_once_with(session_id)

    async def test_delete_nonexistent_session(self, async_client, mock_rag_system):
        """Test deleting a session that doesn't exist"""
        # Configure mock to return False (session not found)
        mock_rag_system.session_manager.delete_session.return_value = False

        session_id = "nonexistent-session"
        response = await async_client.delete(f"/api/session/{session_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify response indicates not found
        assert data["status"] == "not_found"
        assert session_id in data["message"]

    async def test_delete_session_handles_error(self, async_client, mock_rag_system):
        """Test session deletion handles errors gracefully"""
        # Configure mock to raise exception
        mock_rag_system.session_manager.delete_session.side_effect = Exception("Session manager error")

        response = await async_client.delete("/api/session/test-session")

        # Should return 500 for internal error
        assert response.status_code == 500
        assert "Session manager error" in response.json()["detail"]


@pytest.mark.api
class TestCORSHeaders:
    """Test CORS headers are properly configured"""

    async def test_cors_headers_on_query_endpoint(self, async_client):
        """Test CORS headers are present on query endpoint"""
        response = await async_client.post(
            "/api/query",
            json={"query": "test"},
            headers={"Origin": "http://example.com"}
        )

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"

    async def test_cors_headers_on_courses_endpoint(self, async_client):
        """Test CORS headers are present on courses endpoint"""
        response = await async_client.get(
            "/api/courses",
            headers={"Origin": "http://example.com"}
        )

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers


@pytest.mark.api
class TestEndpointIntegration:
    """Integration tests across multiple endpoints"""

    async def test_query_and_get_courses_workflow(self, async_client, mock_rag_system):
        """Test typical user workflow: get courses then query"""
        # First, get available courses
        courses_response = await async_client.get("/api/courses")
        assert courses_response.status_code == 200
        courses_data = courses_response.json()
        assert courses_data["total_courses"] > 0

        # Then, query about a course
        query_response = await async_client.post(
            "/api/query",
            json={"query": f"Tell me about {courses_data['course_titles'][0]}"}
        )
        assert query_response.status_code == 200
        query_data = query_response.json()
        assert "session_id" in query_data

        # Verify we got a session ID
        session_id = query_data["session_id"]
        assert session_id is not None

    async def test_session_lifecycle(self, async_client, mock_rag_system):
        """Test complete session lifecycle: create, use, delete"""
        # Create session via query
        response1 = await async_client.post(
            "/api/query",
            json={"query": "First question"}
        )
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Use same session for follow-up query
        response2 = await async_client.post(
            "/api/query",
            json={
                "query": "Follow-up question",
                "session_id": session_id
            }
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Delete the session
        delete_response = await async_client.delete(f"/api/session/{session_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "success"
