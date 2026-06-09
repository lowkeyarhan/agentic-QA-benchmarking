# Debugging Notes — completeDocumentUpload failure

After a full day of debugging, here are my hypotheses for why completeDocumentUpload is failing:

## Hypothesis A: Element not visible (timing issue)
The `~UploadButton` element exists in the DOM but isn't rendered by the time we try to click it. Maybe the document upload screen has a loading delay. I tried adding a 3-second sleep before `waitForDisplayed` but it didn't help.

## Hypothesis B: Wrong screen context
Maybe the test is navigating to the wrong screen and `~UploadButton` exists on a different screen. Checked the inspect JSON for the payment screen and it has an UploadButton row. Could be a navigation bug.

## Hypothesis C: Selector mismatch
Maybe the label changed. The legacy selector map (legacy-selector-map.json) mentions `UploadButton` for the DocumentUpload screen. If the build changed since then, the label might have been updated. I haven't checked the current inspect-upload-screen.json yet.

## Hypothesis D: Appium session state
The appium-debug.log shows Appium finding "UploadButton" via deprecated class chain queries. Could be an Appium caching issue where old session state interferes.

---

**My current best guess:** Hypothesis A or B. I've been trying longer waits and checking navigation. Haven't confirmed by reading inspect-upload-screen.json yet.

---

**Note:** These are the author's debugging notes from their investigation. Some hypotheses may be wrong. The inspect-upload-screen.json is the authoritative current hierarchy and should be the primary evidence source.
