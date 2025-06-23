When writing unit tests in Python:

1. Aim for high code coverage (90%+) with meaningful assertions
2. Use pytest as the testing framework unless another is already established
3. Follow the AAA pattern (Arrange-Act-Assert) for test structure
4. Use descriptive test names that explain the behavior being tested
5. Mock external dependencies using unittest.mock or pytest-mock
6. Use parametrized tests for testing multiple input variations
7. Include both positive and negative test cases
8. Test edge cases and boundary conditions
9. Keep tests independent and isolated from each other
10. Use fixtures for common setup and teardown
11. Mock all external network calls and file system operations
12. Add docstrings to test classes and methods explaining their purpose
13. Use assertions that provide meaningful error messages
14. Avoid test logic (conditionals, loops) when possible
15. Keep tests simple, focused, and maintainable