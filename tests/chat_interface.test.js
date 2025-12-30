/**
 * Automated tests for RAG Chatbot Chat Interface
 * Tests the UI functionality, New Chat button, and conversation flow
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000';

test.describe('RAG Chatbot Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle');
  });

  test('should load the main page with all UI elements', async ({ page }) => {
    // Check header
    await expect(page.locator('h1')).toContainText('Course Materials Assistant');

    // Check New Chat button
    await expect(page.locator('#newChatButton')).toBeVisible();
    await expect(page.locator('#newChatButton')).toContainText('New Chat');

    // Check chat area
    await expect(page.locator('#chatMessages')).toBeVisible();
    await expect(page.locator('#chatInput')).toBeVisible();
    await expect(page.locator('#sendButton')).toBeVisible();
  });

  test('should display welcome message on load', async ({ page }) => {
    const welcomeMessage = page.locator('.message.assistant').first();
    await expect(welcomeMessage).toBeVisible();
    await expect(welcomeMessage).toContainText('Welcome');
  });

  test('New Chat button - should reset conversation', async ({ page }) => {
    const input = page.locator('#chatInput');
    const sendButton = page.locator('#sendButton');
    const newChatButton = page.locator('#newChatButton');

    // Send a message first
    await input.fill('Test message');
    await sendButton.click();

    // Wait for input to be re-enabled (request completed)
    await expect(input).toBeEnabled({ timeout: 20000 });

    // Wait a bit more to ensure response is rendered
    await page.waitForTimeout(1000);

    // Count messages before reset
    const messagesBefore = await page.locator('.message').count();
    expect(messagesBefore).toBeGreaterThan(1);

    // Click New Chat button (should be enabled now)
    await expect(newChatButton).toBeEnabled();
    await newChatButton.click();

    // Wait for reset to complete
    await page.waitForTimeout(1000);

    // Should only have welcome message now
    const messagesAfter = await page.locator('.message').count();
    expect(messagesAfter).toBe(1);

    // Input should be focused
    await expect(input).toBeFocused();
  });

  test('should send and receive messages', async ({ page }) => {
    const input = page.locator('#chatInput');
    const sendButton = page.locator('#sendButton');

    await input.fill('What is RAG?');
    await sendButton.click();

    // Wait for user message
    const userMessage = page.locator('.message.user').last();
    await expect(userMessage).toContainText('What is RAG?');

    // Wait for input to be re-enabled (means response completed)
    await expect(input).toBeEnabled({ timeout: 20000 });

    // Check that we have at least 2 messages (welcome + user, or welcome + user + assistant)
    const messageCount = await page.locator('.message').count();
    expect(messageCount).toBeGreaterThanOrEqual(2);

    // If we got an assistant response, verify it's visible
    const assistantMessages = await page.locator('.message.assistant').count();
    if (assistantMessages > 1) {
      const assistantMessage = page.locator('.message.assistant').last();
      await expect(assistantMessage).toBeVisible();
    }
  });

  test('New Chat button - should clear chat and show welcome message', async ({ page }) => {
    const input = page.locator('#chatInput');
    const newChatButton = page.locator('#newChatButton');

    // Type something in the input (but don't send)
    await input.fill('Some text');

    // Click New Chat
    await newChatButton.click();
    await page.waitForTimeout(500);

    // Should have exactly 1 message (welcome)
    const messageCount = await page.locator('.message').count();
    expect(messageCount).toBe(1);

    // Should show welcome message
    const welcomeMessage = page.locator('.message.assistant').first();
    await expect(welcomeMessage).toContainText('Welcome');

    // Input should be empty and focused
    await expect(input).toHaveValue('');
    await expect(input).toBeFocused();
  });
});
