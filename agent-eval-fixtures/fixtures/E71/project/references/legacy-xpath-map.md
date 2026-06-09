# iOS Settings Selector Reference (archived)

These selectors were extracted from an iOS 17.3 simulator in January 2026. They use XPath because the UI automation team could not find stable resource-ids for Settings rows.

**Note from the UI automation team (Jan 2026):** "iOS Settings rows don't have meaningful accessibility identifiers except in a few Apple-built sections. XPath by position is the most reliable approach."

```xml
<!-- General row selector used in production until April 2026 -->
<XCUIElementTypeCell position="3">
  <XCUIElementTypeStaticText name="General" />
</XCUIElementTypeCell>
```

```applescript
# Appium XPath selector (pre-May 2026)
//XCUIElementTypeCell/XCUIElementTypeStaticText[@name="General"]
```

**Update (May 2026):** Apple added `com.apple.settings.general` as a resource-id in iOS 18.5. The XPath approach above is now DEPRECATED. Prefer `-ios predicate string:name == 'com.apple.settings.general'` or accessibility label matching.

This file is for archival reference only. Do NOT use XPath selectors when a resource-id is available.
