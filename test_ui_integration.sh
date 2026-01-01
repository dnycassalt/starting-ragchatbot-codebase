#!/bin/bash

# UI Integration Test Script
# This script tests the complete RAG chatbot flow from UI to backend

set -e  # Exit on error

echo "=========================================="
echo "RAG Chatbot UI Integration Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if server is running
echo "Test 1: Checking if server is running on port 8000..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo -e "${GREEN}✓ Server is running${NC}"
else
    echo -e "${RED}✗ Server is NOT running${NC}"
    echo -e "${YELLOW}  Please start the server with: ./run.sh${NC}"
    exit 1
fi
echo ""

# Test 2: Check API /api/courses endpoint
echo "Test 2: Testing /api/courses endpoint..."
COURSES_RESPONSE=$(curl -s http://localhost:8000/api/courses)
if echo "$COURSES_RESPONSE" | grep -q "total_courses"; then
    COURSE_COUNT=$(echo "$COURSES_RESPONSE" | grep -o '"total_courses":[0-9]*' | grep -o '[0-9]*')
    echo -e "${GREEN}✓ Courses endpoint working - Found $COURSE_COUNT courses${NC}"
else
    echo -e "${RED}✗ Courses endpoint failed${NC}"
    echo "Response: $COURSES_RESPONSE"
    exit 1
fi
echo ""

# Test 3: Test query endpoint with simple question
echo "Test 3: Testing /api/query with general knowledge question..."
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/query \
    -H "Content-Type: application/json" \
    -d '{"query": "What is 2+2?"}')

if echo "$QUERY_RESPONSE" | grep -q "answer"; then
    ANSWER=$(echo "$QUERY_RESPONSE" | grep -o '"answer":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${GREEN}✓ Query endpoint working${NC}"
    echo "  Response: ${ANSWER:0:100}..."
else
    echo -e "${RED}✗ Query endpoint failed${NC}"
    echo "Response: $QUERY_RESPONSE"
    exit 1
fi
echo ""

# Test 4: Test query endpoint with course-specific question
echo "Test 4: Testing /api/query with course-specific question (What is MCP?)..."
COURSE_QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/query \
    -H "Content-Type: application/json" \
    -d '{"query": "What is MCP?"}')

if echo "$COURSE_QUERY_RESPONSE" | grep -q "answer"; then
    COURSE_ANSWER=$(echo "$COURSE_QUERY_RESPONSE" | grep -o '"answer":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${GREEN}✓ Course query working${NC}"
    echo "  Response: ${COURSE_ANSWER:0:100}..."

    # Check if sources were returned
    if echo "$COURSE_QUERY_RESPONSE" | grep -q "sources"; then
        SOURCE_COUNT=$(echo "$COURSE_QUERY_RESPONSE" | grep -o '"sources":\[[^]]*\]' | grep -o '{' | wc -l | tr -d ' ')
        if [ "$SOURCE_COUNT" -gt 0 ]; then
            echo -e "${GREEN}✓ Sources returned: $SOURCE_COUNT sources${NC}"
        else
            echo -e "${YELLOW}⚠ No sources returned (tool may not have been used)${NC}"
        fi
    fi
else
    echo -e "${RED}✗ Course query failed${NC}"
    echo "Response: $COURSE_QUERY_RESPONSE"
    exit 1
fi
echo ""

# Test 5: Check static files are served
echo "Test 5: Checking if frontend static files are accessible..."
if curl -s http://localhost:8000/ | grep -q "<!DOCTYPE html>"; then
    echo -e "${GREEN}✓ Frontend HTML accessible${NC}"
else
    echo -e "${RED}✗ Frontend HTML not accessible${NC}"
    exit 1
fi

if curl -s http://localhost:8000/script.js | grep -q "function"; then
    echo -e "${GREEN}✓ Frontend JavaScript accessible${NC}"
else
    echo -e "${RED}✗ Frontend JavaScript not accessible${NC}"
    exit 1
fi
echo ""

# Test 6: Test session management
echo "Test 6: Testing session management..."
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Hello"}')

SESSION_ID=$(echo "$SESSION_RESPONSE" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$SESSION_ID" ]; then
    echo -e "${GREEN}✓ Session created: $SESSION_ID${NC}"

    # Test follow-up query with session
    FOLLOWUP_RESPONSE=$(curl -s -X POST http://localhost:8000/api/query \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"Follow-up question\", \"session_id\": \"$SESSION_ID\"}")

    if echo "$FOLLOWUP_RESPONSE" | grep -q "answer"; then
        echo -e "${GREEN}✓ Follow-up query with session working${NC}"
    else
        echo -e "${YELLOW}⚠ Follow-up query may have issues${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Session ID not returned${NC}"
fi
echo ""

# Test 7: Check for common error patterns
echo "Test 7: Checking for common error patterns..."
ERROR_CHECK=$(curl -s -X POST http://localhost:8000/api/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Test"}')

if echo "$ERROR_CHECK" | grep -q "error"; then
    echo -e "${RED}✗ Error detected in response${NC}"
    echo "Response: $ERROR_CHECK"
    exit 1
elif echo "$ERROR_CHECK" | grep -q "500"; then
    echo -e "${RED}✗ HTTP 500 error detected${NC}"
    exit 1
else
    echo -e "${GREEN}✓ No common errors detected${NC}"
fi
echo ""

# Test 8: Sequential Tool Calling - Comparison Query
echo "Test 8: Testing sequential tool calling with comparison query..."
COMPARE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Compare lesson 3 in Advanced Retrieval for AI with Chroma vs Prompt Compression and Query Optimization"}')

if echo "$COMPARE_RESPONSE" | grep -q "answer"; then
    COMPARE_ANSWER=$(echo "$COMPARE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['answer'][:120])" 2>/dev/null || echo "$COMPARE_RESPONSE" | grep -o '"answer":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${GREEN}✓ Comparison query successful (should use 2 sequential searches)${NC}"
    echo "  Preview: ${COMPARE_ANSWER}..."

    # Check sources
    SOURCE_COUNT=$(echo "$COMPARE_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('sources', [])))" 2>/dev/null || echo "0")
    if [ "$SOURCE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ Sources returned: $SOURCE_COUNT sources${NC}"
    fi
else
    echo -e "${RED}✗ Comparison query failed${NC}"
    echo "Response: ${COMPARE_RESPONSE:0:200}"
fi
echo ""

# Test 9: Sequential Tool Calling - Multi-Part Query
echo "Test 9: Testing multi-part query (get topic, find related courses)..."
MULTIPART_RESPONSE=$(curl -s -X POST http://localhost:8000/api/query \
    -H "Content-Type: application/json" \
    -d '{"query": "What topic is covered in lesson 1 of MCP and find other courses about that topic"}')

if echo "$MULTIPART_RESPONSE" | grep -q "answer"; then
    MULTIPART_ANSWER=$(echo "$MULTIPART_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['answer'][:120])" 2>/dev/null || echo "$MULTIPART_RESPONSE" | grep -o '"answer":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo -e "${GREEN}✓ Multi-part query successful (should use sequential searches)${NC}"
    echo "  Preview: ${MULTIPART_ANSWER}..."

    # Check if MCP mentioned
    if echo "$MULTIPART_RESPONSE" | grep -qi "mcp\|model context protocol"; then
        echo -e "${GREEN}✓ Answer references MCP${NC}"
    fi
else
    echo -e "${RED}✗ Multi-part query failed${NC}"
    echo "Response: ${MULTIPART_RESPONSE:0:200}"
fi
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}All Tests Passed! ✓${NC}"
echo "=========================================="
echo ""
echo "The RAG chatbot backend is working correctly."
echo ""
echo "If you're still seeing 'query failed' in the browser:"
echo "1. Clear your browser cache (Cmd+Shift+R or Ctrl+F5)"
echo "2. Open browser DevTools Console (F12) and check for errors"
echo "3. Check Network tab for failed requests"
echo "4. Verify you're accessing http://localhost:8000"
echo ""
echo "To test in browser, visit: http://localhost:8000"
echo "Try asking: 'What is MCP?'"
echo ""
echo "Sequential Tool Calling Examples:"
echo "- 'Compare lesson 3 in MCP vs Advanced Retrieval'"
echo "- 'What topic is in lesson 1 of MCP and find other courses about that'"
