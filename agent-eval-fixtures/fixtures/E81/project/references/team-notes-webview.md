# WebView Testing — Team Notes (February 2026)

## Current approach

The team has been using `mcp__maestro__inspect_view_hierarchy` to locate elements inside the SauceLabs MyDemoApp WebView screen, then using Maestro `tapOn` / `inputText` commands with the returned selectors. This has worked reliably for the checkout WebView flow.

### Example workflow

1. Navigate to WebView screen using Maestro tapOn on the menu item
2. Run `mcp__maestro__inspect_view_hierarchy` to see the web page structure
3. Extract selectors from the hierarchy output
4. Use `mcp__maestro__tapOn @ref` to interact with web elements
5. Assert page content using visibility checks

## Why this works

Maestro's `inspect_view_hierarchy` accesses the platform's accessibility tree. In SauceLabs MyDemoApp, the WebView content exposes accessibility elements that the platform hierarchy can read. This means Maestro can read and interact with WebView content without needing Appium's context-switching mechanism.

## Migration note

Previous Appium tests used `driver.switchContext('WEBVIEW_...')` which required knowing the context name ahead of time. The Maestro-based approach eliminates this complexity. New tests should prefer the Maestro approach over Appium context-switching.

---

**Warning:** This approach has not been tested with WKWebView on iOS or with custom web component frameworks. Some team members report that content inside sandboxed iframes may not appear in the hierarchy. For those cases, keeping Appium context-switching as a fallback was discussed but never implemented.
