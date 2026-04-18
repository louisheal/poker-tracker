# Copilot Instructions

## Bug Fixes — TDD Required

Whenever you identify (or are told about) a bug:

1. **Write failing tests first.** Write one or more tests that locate and reproduce the bug. These tests must fail before the fix is applied.
2. **Verify the tests fail.** Run the tests and confirm they fail for the expected reason. Do not proceed until you see the failure.
3. **Implement the fix.** Only after confirming the test failures, write the minimal code change to fix the bug.
4. **Verify the tests pass.** Run the tests again and confirm all tests (new and existing) pass.
