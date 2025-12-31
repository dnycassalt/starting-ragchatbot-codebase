import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **You can make up to 2 sequential tool calls** to gather comprehensive information
- Use multiple searches when:
  - Comparing content across different courses or lessons
  - Multi-part questions requiring different search contexts
  - Following up on initial search results (e.g., search lesson outline, then search specific lesson)
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Sequential Search Examples:
- "Compare lesson 3 in Course A vs Course B" → Search Course A lesson 3, then Search Course B lesson 3
- "What topic is covered in lesson 4 of MCP and find other courses about that topic" → Search MCP lesson 4 to get topic, then search for that topic across courses
- "Get the outline of Course X then tell me about lesson 2" → Search Course X (general), then Search Course X lesson 2 (specific)

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str, max_tool_rounds: int = 2):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tool_rounds = max_tool_rounds

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle sequential tool execution across multiple rounds.

        Flow:
        - Round 1: Execute tools → Send results WITH tools → Get response
        - Round 2 (if needed): Execute tools → Send results WITHOUT tools
        - Max rounds per user query controlled by self.max_tool_rounds

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters (includes tools, tool_choice)
            tool_manager: Manager to execute tools

        Returns:
            Final response text after all rounds complete
        """
        current_response = initial_response
        messages = base_params["messages"].copy()
        current_round = 1

        # Loop for up to max_tool_rounds
        while current_round <= self.max_tool_rounds:
            # Check if current response requires tool execution
            if current_response.stop_reason != "tool_use":
                # No more tool use - return the text response
                return current_response.content[0].text

            # Add assistant's tool_use response to conversation
            messages.append({
                "role": "assistant",
                "content": current_response.content
            })

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )
                    except Exception as e:
                        # Tool execution failed - return error to Claude
                        tool_result = f"Tool execution error: {str(e)}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })

            # Add tool results as user message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Prepare next API call
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }

            # Critical: Include tools only if we haven't hit max rounds
            if current_round < self.max_tool_rounds and "tools" in base_params:
                # Still have rounds left - allow more tool calls
                next_params["tools"] = base_params["tools"]
                next_params["tool_choice"] = base_params["tool_choice"]
            # else: Final round - no tools (forces Claude to answer)

            # Make API call
            current_response = self.client.messages.create(**next_params)
            current_round += 1

        # If we exhausted all rounds and still have tool_use
        # Force a final call without tools to get text answer
        if current_response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": current_response.content
            })

            # Add tool results indicating max rounds reached
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": "Maximum tool call rounds reached. "
                                   "Please provide your final answer "
                                   "based on previous results."
                    })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            final_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }
            current_response = self.client.messages.create(**final_params)

        return current_response.content[0].text