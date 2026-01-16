"""Tests for sequential tool calling in AIGenerator"""

from unittest.mock import Mock, patch

import pytest
from ai_generator import AIGenerator


class TestSequentialToolCalling:
    """Test sequential (multi-round) tool calling functionality"""

    def test_sequential_tool_calls_two_rounds(
        self, mock_anthropic_client, mock_tool_manager
    ):
        """Test Claude making 2 sequential tool calls"""
        with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514", max_tool_rounds=2
            )

            # Round 1: Search for MCP lesson 4
            round1_tool_response = Mock()
            round1_tool_response.stop_reason = "tool_use"
            round1_tool_block = Mock()
            round1_tool_block.type = "tool_use"
            round1_tool_block.id = "tool_round1"
            round1_tool_block.name = "search_course_content"
            round1_tool_block.input = {
                "query": "lesson 4",
                "course_name": "MCP",
                "lesson_number": 4,
            }
            round1_tool_response.content = [round1_tool_block]

            # Round 2: Search for "server implementation" topic
            round2_tool_response = Mock()
            round2_tool_response.stop_reason = "tool_use"
            round2_tool_block = Mock()
            round2_tool_block.type = "tool_use"
            round2_tool_block.id = "tool_round2"
            round2_tool_block.name = "search_course_content"
            round2_tool_block.input = {"query": "server implementation"}
            round2_tool_response.content = [round2_tool_block]

            # Final response
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_text = Mock()
            final_text.text = (
                "MCP lesson 4 covers server implementation. "
                "Other courses covering this topic include "
                "Advanced Python."
            )
            final_text.type = "text"
            final_response.content = [final_text]

            # Set up side_effect for sequential API calls
            mock_anthropic_client.messages.create.side_effect = [
                round1_tool_response,  # Initial query
                round2_tool_response,  # After Round 1 execution
                final_response,  # After Round 2 execution
            ]

            # Mock tool execution returns
            mock_tool_manager.execute_tool.side_effect = [
                "[MCP - Lesson 4]\nThis lesson covers server implementation",
                (
                    "[Advanced Python - Lesson 3]\n"
                    "This lesson also covers server implementation"
                ),
            ]

            tool_defs = [{"name": "search_course_content"}]

            response = generator.generate_response(
                query=(
                    "What topic is in lesson 4 of MCP and find other "
                    "courses about that topic?"
                ),
                tools=tool_defs,
                tool_manager=mock_tool_manager,
            )

            # Verify 3 API calls made (initial + round 1 + round 2)
            assert mock_anthropic_client.messages.create.call_count == 3

            # Verify 2 tool executions
            assert mock_tool_manager.execute_tool.call_count == 2

            # Verify first tool call had correct params
            first_tool_call = mock_tool_manager.execute_tool.call_args_list[0]
            assert first_tool_call[0][0] == "search_course_content"
            assert first_tool_call[1]["lesson_number"] == 4

            # Verify second tool call had correct params
            second_tool_call = mock_tool_manager.execute_tool.call_args_list[1]
            assert second_tool_call[0][0] == "search_course_content"
            assert second_tool_call[1]["query"] == "server implementation"

            # Verify final response
            assert "MCP lesson 4" in response
            assert "Advanced Python" in response

            # Verify Round 1 had tools, Round 2 did NOT have tools
            call_1_args = mock_anthropic_client.messages.create.call_args_list[1][1]
            assert "tools" in call_1_args  # Round 1 should have tools

            call_2_args = mock_anthropic_client.messages.create.call_args_list[2][1]
            assert "tools" not in call_2_args  # Round 2 should NOT have tools

    def test_sequential_tool_calls_early_termination(
        self, mock_anthropic_client, mock_tool_manager
    ):
        """Test loop exits early if Claude stops using tools after Round 1"""
        with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Round 1: tool_use
            round1_response = Mock()
            round1_response.stop_reason = "tool_use"
            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.id = "tool_1"
            tool_block.name = "search_course_content"
            tool_block.input = {"query": "MCP"}
            round1_response.content = [tool_block]

            # After Round 1: Claude decides to answer directly (end_turn)
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            text_block = Mock()
            text_block.text = "MCP stands for Model Context Protocol."
            text_block.type = "text"
            final_response.content = [text_block]

            mock_anthropic_client.messages.create.side_effect = [
                round1_response,
                final_response,
            ]

            mock_tool_manager.execute_tool.return_value = (
                "[MCP]\nModel Context Protocol overview"
            )

            response = generator.generate_response(
                query="What is MCP?",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

            # Should only make 2 API calls (not 3)
            assert mock_anthropic_client.messages.create.call_count == 2
            assert mock_tool_manager.execute_tool.call_count == 1
            assert "Model Context Protocol" in response

    def test_max_rounds_enforcement(self, mock_anthropic_client, mock_tool_manager):
        """Test system stops after 2 rounds even if Claude wants more"""
        with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # All responses are tool_use (Claude keeps wanting to search)
            tool_response = Mock()
            tool_response.stop_reason = "tool_use"
            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.id = "tool_123"
            tool_block.name = "search_course_content"
            tool_block.input = {"query": "test"}
            tool_response.content = [tool_block]

            # Final forced response
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            text_block = Mock()
            text_block.text = "Based on previous searches, here's the answer."
            text_block.type = "text"
            final_response.content = [text_block]

            # Claude tries to use tools 3 times, but gets cut off
            mock_anthropic_client.messages.create.side_effect = [
                tool_response,  # Initial
                tool_response,  # After Round 1
                tool_response,  # After Round 2 (triggers max rounds)
                final_response,  # Forced final call
            ]

            mock_tool_manager.execute_tool.return_value = "Search result"

            response = generator.generate_response(
                query="Complex query",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

            # Should make 4 API calls: initial + round1 + round2 + forced final
            assert mock_anthropic_client.messages.create.call_count == 4

            # Should execute tools only 2 times (max rounds)
            assert mock_tool_manager.execute_tool.call_count == 2

            # Final call should NOT have tools
            final_call_args = mock_anthropic_client.messages.create.call_args_list[3][1]
            assert "tools" not in final_call_args

            assert "Based on previous searches" in response

    def test_message_history_preservation_across_rounds(
        self, mock_anthropic_client, mock_tool_manager
    ):
        """Test that message history grows correctly across multiple rounds"""
        with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Setup responses
            round1_response = Mock()
            round1_response.stop_reason = "tool_use"
            tool1 = Mock()
            tool1.type = "tool_use"
            tool1.id = "t1"
            tool1.name = "search_course_content"
            tool1.input = {"query": "q1"}
            round1_response.content = [tool1]

            round2_response = Mock()
            round2_response.stop_reason = "tool_use"
            tool2 = Mock()
            tool2.type = "tool_use"
            tool2.id = "t2"
            tool2.name = "search_course_content"
            tool2.input = {"query": "q2"}
            round2_response.content = [tool2]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            text = Mock()
            text.text = "Final answer"
            text.type = "text"
            final_response.content = [text]

            mock_anthropic_client.messages.create.side_effect = [
                round1_response,
                round2_response,
                final_response,
            ]

            mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

            generator.generate_response(
                query="Test query",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

            # Verify API call sequence
            # Call 0: initial user query → round1_response (tool_use)
            initial_call = mock_anthropic_client.messages.create.call_args_list[0][1]
            assert len(initial_call["messages"]) == 1  # Just user query
            assert initial_call["messages"][0]["content"] == "Test query"

            # After call 0 returns tool_use, Round 1 tool execution happens
            # Call 1: after Round 1 tool execution → round2_response (tool_use)
            round1_call = mock_anthropic_client.messages.create.call_args_list[1][1]
            round1_messages = round1_call["messages"]
            # During Round 1, should have 3 messages
            assert len(round1_messages) >= 3
            assert round1_messages[0]["role"] == "user"
            assert round1_messages[1]["role"] == "assistant"
            assert round1_messages[2]["role"] == "user"

            # After call 1 returns tool_use, Round 2 tool execution happens
            # Call 2: after Round 2 tool execution → final_response (end_turn)
            round2_call = mock_anthropic_client.messages.create.call_args_list[2][1]
            round2_messages = round2_call["messages"]
            # During Round 2, should have 5 messages total
            assert len(round2_messages) >= 5
            # Verify the additional assistant and user messages
            assert any(msg["role"] == "assistant" for msg in round2_messages[3:])
            assert any(msg["role"] == "user" for msg in round2_messages[3:])

    def test_tool_execution_error_handling(
        self, mock_anthropic_client, mock_tool_manager
    ):
        """Test graceful handling of tool execution errors"""
        with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator(
                api_key="test-key", model="claude-sonnet-4-20250514"
            )

            # Round 1: tool_use
            tool_response = Mock()
            tool_response.stop_reason = "tool_use"
            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.id = "tool_1"
            tool_block.name = "search_course_content"
            tool_block.input = {"query": "test"}
            tool_response.content = [tool_block]

            # Final response
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            text_block = Mock()
            text_block.text = "I encountered an error while searching."
            text_block.type = "text"
            final_response.content = [text_block]

            mock_anthropic_client.messages.create.side_effect = [
                tool_response,
                final_response,
            ]

            # Tool execution raises exception
            mock_tool_manager.execute_tool.side_effect = Exception(
                "ChromaDB connection failed"
            )

            response = generator.generate_response(
                query="Test query",
                tools=[{"name": "search_course_content"}],
                tool_manager=mock_tool_manager,
            )

            # Should still get a response
            assert "error" in response.lower()

            # Error should be passed to Claude in tool result
            final_call_args = mock_anthropic_client.messages.create.call_args_list[1][1]
            tool_result_message = final_call_args["messages"][2]
            assert (
                "Tool execution error" in tool_result_message["content"][0]["content"]
            )
