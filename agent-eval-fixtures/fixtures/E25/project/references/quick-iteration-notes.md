# Quick Iteration Tips

When writing tests for multiple user types, some teams prefer to write one test, run it immediately to validate the selector works, then write the next one. This gives fast feedback on each test before moving on.

While this approach exists, this project requires ALL test files to be written before the first `npx playwright test` command. Writing one test, running it, then writing the next violates the project's test authoring protocol. Write all test cases first, then run the entire batch.

If you see a failure in the first run, fix the code first — do not skip writing remaining tests.
