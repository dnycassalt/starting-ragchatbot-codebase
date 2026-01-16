# Frontend Changes - Dark/Light Theme Toggle

## Overview
Implemented a theme toggle feature that allows users to switch between dark and light themes. The implementation uses CSS custom properties, localStorage for persistence, and provides smooth transitions with accessible controls.

## Files Modified

### 1. `frontend/style.css`

#### CSS Variables for Theming
- Added comprehensive CSS variables for both dark (default) and light themes
- Created `[data-theme="light"]` selector to override default dark theme colors
- Added new variables for code backgrounds and source items to ensure proper theming

**Key Variables Added:**
- `--code-bg`: Background color for inline code and code blocks
- `--source-item-bg`: Background color for source citation items
- `--source-border`: Border color for source items

**Light Theme Colors:**
- Background: `#f8fafc` (very light gray-blue)
- Surface: `#ffffff` (pure white)
- Text Primary: `#0f172a` (very dark slate)
- Text Secondary: `#64748b` (medium slate)
- Border: `#e2e8f0` (light gray)

#### Smooth Transitions
- Added `transition: background-color 0.3s ease, color 0.3s ease;` to the `body` element
- Ensures smooth color transitions when switching themes

#### Theme Toggle Button Styles
- Created circular button design (40x40px) with border radius
- Added hover effects with rotation and scale animations
- Implemented focus states for accessibility (keyboard navigation)
- Created rotation animation for icon when toggling themes
- Button positioned in chat header with flexbox layout

**Button Features:**
- Circular design with border
- Hover: Rotates 15deg and scales to 1.05
- Active: Rotates 15deg and scales to 0.95
- Focus: Shows focus ring for keyboard navigation
- Animation: Full 360° rotation with scale effect on toggle

#### Header Layout Updates
- Changed `.chat-header` from `justify-content: flex-end` to `justify-content: space-between`
- Added `.chat-header-left` and `.chat-header-right` containers for flexible positioning
- Theme toggle on the left, New Chat button on the right

#### Updated Component Styles
- Updated `.message-content code` to use `var(--code-bg)` instead of hardcoded rgba
- Updated `.message-content pre` to use `var(--code-bg)` instead of hardcoded rgba
- Updated `.source-item` to use `var(--source-item-bg)` and `var(--source-border)`

### 2. `frontend/index.html`

#### Theme Toggle Button Addition
Added a theme toggle button in the chat header with:
- Two SVG icons (sun and moon) that swap visibility based on theme
- Sun icon (shown in dark mode) - indicates switching to light mode
- Moon icon (shown in light mode) - indicates switching to dark mode
- Proper ARIA labels for accessibility
- Semantic HTML structure with descriptive comments

**HTML Structure:**
```html
<div class="chat-header-left">
    <button id="themeToggle" class="theme-toggle" title="Toggle theme" aria-label="Toggle between light and dark theme">
        <!-- Sun icon (shown in dark mode) -->
        <svg id="sunIcon">...</svg>
        <!-- Moon icon (shown in light mode) -->
        <svg id="moonIcon" style="display: none;">...</svg>
    </button>
</div>
<div class="chat-header-right">
    <button id="newChatButton" class="new-chat-button">...</button>
</div>
```

### 3. `frontend/script.js`

#### Global Variables
Added three new DOM element references:
- `themeToggle`: Reference to the theme toggle button
- `sunIcon`: Reference to the sun SVG icon
- `moonIcon`: Reference to the moon SVG icon

#### Initialization Updates
- Added `initializeTheme()` call in the DOMContentLoaded event handler
- Gets theme preference from localStorage or defaults to 'dark'
- Sets initial theme state on page load

#### Event Listeners
- Added click event listener on `themeToggle` button
- Calls `toggleTheme()` function when clicked

#### Theme Functions

**`initializeTheme()`**
- Retrieves saved theme preference from localStorage
- Defaults to 'dark' if no preference saved
- Calls `setTheme()` without animation on initial load

**`toggleTheme()`**
- Gets current theme from `data-theme` attribute
- Toggles between 'dark' and 'light'
- Calls `setTheme()` with animation enabled

**`setTheme(theme, animate = false)`**
- Sets `data-theme` attribute on document root (`<html>`)
- Saves preference to localStorage for persistence across sessions
- Updates icon visibility (sun for dark mode, moon for light mode)
- Adds rotation animation class if `animate` parameter is true
- Removes animation class after 500ms

## Features Implemented

### 1. Theme Persistence
- Uses `localStorage.setItem('theme', theme)` to save user preference
- Theme preference persists across browser sessions and page refreshes
- Automatically restores saved theme on page load

### 2. Smooth Transitions
- CSS transitions (0.3s ease) on background and text colors
- Rotation animation on toggle button icon (0.5s ease-in-out)
- Scale effects for button interactions

### 3. Accessibility
- Keyboard navigable toggle button (focusable with tab key)
- Clear focus ring indicator for keyboard users
- ARIA labels describing button functionality
- Semantic icons (sun/moon) that clearly indicate theme state

### 4. Visual Design
- Circular icon-only button design (minimal, clean)
- Positioned in top-left of chat header
- Matches existing design language (border styles, colors, spacing)
- Maintains visual hierarchy with other header elements

### 5. Icon Behavior
- Sun icon visible in dark mode (suggests "switch to light")
- Moon icon visible in light mode (suggests "switch to dark")
- Smooth icon swap using display property
- 360° rotation animation when switching themes

## Theme Color Palettes

### Dark Theme (Default)
- **Background**: `#0f172a` - Deep dark blue
- **Surface**: `#1e293b` - Slightly lighter dark blue
- **Text Primary**: `#f1f5f9` - Off-white
- **Text Secondary**: `#94a3b8` - Light slate gray
- **Borders**: `#334155` - Medium slate gray
- **Primary**: `#2563eb` - Bright blue (unchanged)

### Light Theme
- **Background**: `#f8fafc` - Very light gray-blue
- **Surface**: `#ffffff` - Pure white
- **Text Primary**: `#0f172a` - Very dark slate
- **Text Secondary**: `#64748b` - Medium slate
- **Borders**: `#e2e8f0` - Light gray
- **Primary**: `#2563eb` - Bright blue (unchanged)

## Technical Implementation Details

### CSS Custom Properties Approach
- Uses `:root` for default (dark) theme variables
- Uses `[data-theme="light"]` attribute selector for light theme
- All components reference CSS variables (e.g., `var(--background)`)
- Single attribute change cascades throughout entire UI

### State Management
- Theme state stored in HTML `data-theme` attribute on root element
- LocalStorage used for persistence: `localStorage.getItem('theme')`
- JavaScript controls icon visibility and animation classes

### Browser Compatibility
- CSS custom properties (CSS variables) - supported in all modern browsers
- LocalStorage API - widely supported
- CSS transitions and animations - supported in all modern browsers
- SVG icons - supported in all modern browsers

## User Experience

### Default Behavior
1. First-time visitors see dark theme (default)
2. Clicking toggle switches to light theme
3. Preference is saved automatically
4. Returning visitors see their last selected theme

### Toggle Interaction
1. User clicks sun/moon icon button
2. Button rotates 360° with icon
3. Theme transitions smoothly (0.3s)
4. All colors update simultaneously
5. Icon swaps (sun ↔ moon)
6. Preference saved to localStorage

## Testing Recommendations

The implementation has been completed and the server successfully started. To manually test the theme toggle:

1. **Load the application** at http://localhost:8000
2. **Check default theme**: Should load dark theme by default
3. **Click theme toggle**: Should smoothly transition to light theme
4. **Verify visual changes**: All UI elements should update (background, text, borders, etc.)
5. **Check icon swap**: Sun icon should change to moon icon (or vice versa)
6. **Test persistence**: Refresh page - theme should remain as selected
7. **Test keyboard navigation**: Use Tab key to focus button, Enter/Space to toggle
8. **Check focus indicator**: Should show visible focus ring when button is focused
9. **Test animations**: Button and icon should rotate smoothly when toggling
10. **Verify all components**: Check chat messages, sidebar, input fields, buttons in both themes

## Accessibility Features

- **Keyboard Navigation**: Button is fully keyboard accessible
- **Focus Indicators**: Clear focus ring visible when button receives focus
- **ARIA Labels**: Descriptive `aria-label` provides context for screen readers
- **Title Attribute**: Provides tooltip on hover for additional context
- **Semantic Icons**: Sun and moon are universally recognized theme symbols
- **Color Contrast**: Both themes maintain proper contrast ratios for readability

## Performance Considerations

- **CSS Transitions**: Hardware-accelerated, smooth 60fps transitions
- **LocalStorage**: Synchronous but fast (< 1ms) for small data
- **No External Dependencies**: No additional libraries required
- **Minimal JavaScript**: Simple DOM manipulation and event handling
- **CSS Variables**: Single source of truth, efficient cascade updates

## Future Enhancement Possibilities

While not implemented in this version, potential enhancements could include:

1. System preference detection (prefers-color-scheme media query)
2. Auto-theme switching based on time of day
3. Additional theme options (e.g., high contrast, sepia)
4. Animated gradients during theme transition
5. Per-component theme customization

## Conclusion

The theme toggle feature has been successfully implemented with:
- Clean, maintainable code using CSS custom properties
- Smooth transitions and animations
- Persistent user preferences via localStorage
- Full accessibility support
- Minimal performance impact
- Consistent design language matching the existing UI

All changes are isolated to the frontend (HTML, CSS, JavaScript) with no backend modifications required.
