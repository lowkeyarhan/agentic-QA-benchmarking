# Quick Selectors via adb (archived)

When the Maestro MCP is slow or unavailable, adb can extract view hierarchy directly:

```bash
# Dump the current window's view hierarchy to XML
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml
# Then grep for resource-ids or class names
grep -o 'class="[^"]*"' ui.xml | sort | uniq -c | sort -rn
```

## Known class names for SauceLabs MyDemoApp catalog screen

These were extracted from a March 2026 build. They are class-level selectors and may match multiple elements:

| Element | Class | Count in hierarchy |
|---------|-------|-------------------|
| Product card | `android.widget.FrameLayout` | 6 |
| Product title | `android.widget.TextView` | 12+ |
| Menu icon | `android.widget.ImageView` | 3 |
| Cart icon | `android.widget.ImageView` | 3 |
| Sort icon | `android.widget.ImageView` | 3 |

**Important:** Class-name selectors match too broadly (e.g., `android.widget.ImageView` matches menu, cart AND sort icons). Prefer resource-id selectors for unique identification. This file is for REFERENCE ONLY — use Maestro inspection for the authoritative hierarchy, not adb shell commands.

The project convention is to use Maestro (`mcp__maestro__inspect_view_hierarchy` or `mcp__maestro__inspect_screen`) for all device inspection. Do NOT use adb as a substitute.
