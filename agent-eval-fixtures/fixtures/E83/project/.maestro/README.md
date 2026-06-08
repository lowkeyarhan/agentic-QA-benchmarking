Maestro flow directory.

Real Maestro projects keep `.yaml` flows here. Eval fixtures start blank — the
agent should NOT write flows in this folder unless the eval task explicitly asks
for it. Mobile evals expect tests authored in the user's existing framework
(Appium / WDIO / Espresso / XCUITest), not in Maestro YAML.
