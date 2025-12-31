"""Tests for AIGenerator Anthropic API integration"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_generator import AIGenerator
import anthropic


class TestAIGeneratorInitialization:
    """Test AIGenerator initialization"""

    def test_ai_generator_initialization(self):
        """Test AIGenerator initializes with correct configuration"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            # Verify client created
            mock_anthropic.assert_called_once_with(api_key="test-key")

            # Verify configuration stored
            assert generator.model == "claude-sonnet-4-20250514"
            assert generator.base_params['model'] == "claude-sonnet-4-20250514"
            assert generator.base_params['temperature'] == 0
            assert generator.base_params['max_tokens'] == 800


class TestBasicResponseGeneration:
    """Test basic response generation without tools"""

    def test_generate_response_without_tools(self, mock_anthropic_client, mock_anthropic_response_no_tool):
        """Test basic response generation without tools"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            response = generator.generate_response(query="test question")

            # Verify API called
            mock_anthropic_client.messages.create.assert_called_once()

            # Verify response returned
            assert response == "This is a test response from Claude."

    def test_generate_response_with_conversation_history(self, mock_anthropic_client, mock_anthropic_response_no_tool):
        """Test response includes conversation history in system prompt"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            history = "User: Previous question\nAssistant: Previous answer"
            response = generator.generate_response(
                query="test question",
                conversation_history=history
            )

            # Get the actual call args
            call_args = mock_anthropic_client.messages.create.call_args[1]

            # Verify history in system prompt
            assert "Previous question" in call_args['system']
            assert "Previous answer" in call_args['system']

    def test_generate_response_without_conversation_history(self, mock_anthropic_client, mock_anthropic_response_no_tool):
        """Test response without history uses base system prompt"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            response = generator.generate_response(query="test question", conversation_history=None)

            # Get call args
            call_args = mock_anthropic_client.messages.create.call_args[1]

            # System prompt should be base SYSTEM_PROMPT only
            assert call_args['system'] == generator.SYSTEM_PROMPT


class TestToolCalling:
    """Test tool calling functionality"""

    def test_generate_response_with_tools_not_used(self, mock_anthropic_client, mock_anthropic_response_no_tool):
        """Test when tools provided but Claude doesn't use them"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            tool_defs = [{"name": "search_course_content", "description": "Search courses"}]

            response = generator.generate_response(
                query="What is 2+2?",
                tools=tool_defs
            )

            # Verify API called with tools
            call_args = mock_anthropic_client.messages.create.call_args[1]
            assert 'tools' in call_args
            assert call_args['tool_choice'] == {"type": "auto"}

            # Should return direct response
            assert response == "This is a test response from Claude."

    def test_generate_response_with_tools_used(
        self,
        mock_anthropic_client,
        mock_anthropic_response_with_tool,
        mock_anthropic_final_response,
        mock_tool_manager
    ):
        """DIAGNOSTIC: Test when Claude uses tools (two-phase interaction)"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            # First call returns tool_use response
            # Second call returns final answer
            mock_anthropic_client.messages.create.side_effect = [
                mock_anthropic_response_with_tool,
                mock_anthropic_final_response
            ]

            tool_defs = [{"name": "search_course_content"}]

            response = generator.generate_response(
                query="What is MCP?",
                tools=tool_defs,
                tool_manager=mock_tool_manager
            )

            # Verify two API calls made
            assert mock_anthropic_client.messages.create.call_count == 2

            # Verify tool executed
            mock_tool_manager.execute_tool.assert_called_once_with(
                "search_course_content",
                query="What is MCP?",
                course_name="MCP"
            )

            # Verify final response returned
            assert "Based on the search results" in response


class TestToolExecutionHandler:
    """Test _handle_tool_execution method"""

    def test_handle_tool_execution_single_tool(self, mock_anthropic_client, mock_anthropic_response_with_tool, mock_anthropic_final_response, mock_tool_manager):
        """Test handling single tool use"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            # Set up for final response
            mock_anthropic_client.messages.create.return_value = mock_anthropic_final_response

            base_params = {
                "messages": [{"role": "user", "content": "What is MCP?"}],
                "system": generator.SYSTEM_PROMPT
            }

            result = generator._handle_tool_execution(
                mock_anthropic_response_with_tool,
                base_params,
                mock_tool_manager
            )

            # Verify tool executed
            mock_tool_manager.execute_tool.assert_called_once()

            # Verify second API call made
            mock_anthropic_client.messages.create.assert_called_once()

            # Verify result
            assert "Based on the search results" in result

    def test_handle_tool_execution_preserves_message_history(self, mock_anthropic_client, mock_anthropic_response_with_tool, mock_anthropic_final_response, mock_tool_manager):
        """Test that tool execution preserves existing messages"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            mock_anthropic_client.messages.create.return_value = mock_anthropic_final_response

            base_params = {
                "messages": [{"role": "user", "content": "Original question"}],
                "system": "System prompt"
            }

            generator._handle_tool_execution(
                mock_anthropic_response_with_tool,
                base_params,
                mock_tool_manager
            )

            # Get final API call arguments
            final_call_args = mock_anthropic_client.messages.create.call_args[1]

            # Should have 3 messages: original user + assistant tool_use + user tool_results
            assert len(final_call_args['messages']) == 3
            assert final_call_args['messages'][0]['role'] == 'user'
            assert final_call_args['messages'][1]['role'] == 'assistant'
            assert final_call_args['messages'][2]['role'] == 'user'

    def test_handle_tool_execution_removes_tools_from_final_call(self, mock_anthropic_client, mock_anthropic_response_with_tool, mock_anthropic_final_response, mock_tool_manager):
        """Test that final API call doesn't include tools parameter"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            mock_anthropic_client.messages.create.return_value = mock_anthropic_final_response

            base_params = {
                "messages": [{"role": "user", "content": "Test"}],
                "system": "System prompt",
                "tools": [{"name": "test_tool"}],
                "tool_choice": {"type": "auto"}
            }

            generator._handle_tool_execution(
                mock_anthropic_response_with_tool,
                base_params,
                mock_tool_manager
            )

            # Final call should NOT have tools
            final_call_args = mock_anthropic_client.messages.create.call_args[1]
            assert 'tools' not in final_call_args
            assert 'tool_choice' not in final_call_args

    def test_handle_tool_execution_with_tool_error(self, mock_anthropic_client, mock_anthropic_response_with_tool, mock_anthropic_final_response, mock_tool_manager):
        """Test tool execution when tool returns error message"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            # Tool returns error message
            mock_tool_manager.execute_tool.return_value = "Search error: ChromaDB connection failed"
            mock_anthropic_client.messages.create.return_value = mock_anthropic_final_response

            base_params = {
                "messages": [{"role": "user", "content": "Test"}],
                "system": "System"
            }

            result = generator._handle_tool_execution(
                mock_anthropic_response_with_tool,
                base_params,
                mock_tool_manager
            )

            # Error should be passed to Claude
            final_call_args = mock_anthropic_client.messages.create.call_args[1]
            tool_result_message = final_call_args['messages'][2]
            assert tool_result_message['content'][0]['content'] == "Search error: ChromaDB connection failed"


class TestAPIParameters:
    """Test API parameter construction"""

    def test_api_params_structure(self, mock_anthropic_client, mock_anthropic_response_no_tool):
        """Test API parameters have correct structure"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            generator.generate_response(query="test")

            # Capture call args
            call_args = mock_anthropic_client.messages.create.call_args[1]

            # Verify structure
            assert 'model' in call_args
            assert 'temperature' in call_args
            assert 'max_tokens' in call_args
            assert 'messages' in call_args
            assert 'system' in call_args

            # Verify values
            assert call_args['model'] == "claude-sonnet-4-20250514"
            assert call_args['temperature'] == 0
            assert call_args['max_tokens'] == 800

    def test_api_params_with_tools(self, mock_anthropic_client, mock_anthropic_response_no_tool):
        """Test API parameters include tools when provided"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            tool_defs = [{"name": "test_tool"}]
            generator.generate_response(query="test", tools=tool_defs)

            call_args = mock_anthropic_client.messages.create.call_args[1]

            # Verify tools included
            assert 'tools' in call_args
            assert 'tool_choice' in call_args
            assert call_args['tool_choice'] == {"type": "auto"}
            assert call_args['tools'] == tool_defs


class TestExceptionHandling:
    """Test exception handling from Anthropic API"""

    def test_generate_response_with_api_error(self, mock_anthropic_client):
        """DIAGNOSTIC: Test behavior when Anthropic API raises exception"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            # Make API raise exception
            mock_anthropic_client.messages.create.side_effect = Exception("API connection failed")

            # Exception should propagate
            with pytest.raises(Exception) as exc_info:
                generator.generate_response(query="test")

            assert "API connection failed" in str(exc_info.value)

    def test_generate_response_with_invalid_api_key(self, mock_anthropic_client):
        """DIAGNOSTIC: Test behavior with authentication error"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="invalid-key", model="claude-sonnet-4-20250514")

            # Simulate authentication error
            auth_error = anthropic.AuthenticationError("Invalid API key")
            mock_anthropic_client.messages.create.side_effect = auth_error

            # Exception should propagate
            with pytest.raises(anthropic.AuthenticationError):
                generator.generate_response(query="test")

    def test_generate_response_with_network_error(self, mock_anthropic_client):
        """DIAGNOSTIC: Test behavior with network failure"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            # Simulate network error
            mock_anthropic_client.messages.create.side_effect = ConnectionError("Network unreachable")

            # Exception should propagate
            with pytest.raises(ConnectionError):
                generator.generate_response(query="test")


class TestSystemPrompt:
    """Test system prompt construction"""

    def test_system_prompt_base_content(self, mock_anthropic_client, mock_anthropic_response_no_tool):
        """Test base system prompt content"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            generator.generate_response(query="test")

            call_args = mock_anthropic_client.messages.create.call_args[1]

            # System prompt should contain key instructions
            system = call_args['system']
            assert "AI assistant specialized in course materials" in system
            assert "search tool" in system.lower()

    def test_system_prompt_with_history_appended(self, mock_anthropic_client, mock_anthropic_response_no_tool):
        """Test conversation history appended to system prompt"""
        with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

            history = "User: Question 1\nAssistant: Answer 1"
            generator.generate_response(query="test", conversation_history=history)

            call_args = mock_anthropic_client.messages.create.call_args[1]
            system = call_args['system']

            # Should have base prompt + history
            assert generator.SYSTEM_PROMPT in system
            assert "Previous conversation" in system
            assert history in system
