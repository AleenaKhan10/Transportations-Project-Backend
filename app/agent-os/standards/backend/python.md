## Python coding standards and best practices

### Code Style and Formatting

- **PEP 8 Compliance**: Follow PEP 8 style guide for Python code including naming conventions, line length (88-100 chars), and whitespace usage
- **Type Hints**: Use type hints for function arguments, return values, and class attributes to improve code clarity and enable static analysis
- **Import Organization**: Group imports in order: standard library, third-party packages, local modules; use absolute imports over relative
- **String Formatting**: Prefer f-strings for string interpolation over .format() or % formatting for better readability and performance
- **List/Dict Comprehensions**: Use comprehensions for simple transformations; avoid complex nested comprehensions that reduce readability
- **Context Managers**: Use context managers (with statements) for resource management (files, database connections, locks)
- **Docstrings**: Include docstrings for all public modules, classes, functions following PEP 257; use triple double-quotes

### Naming Conventions

- **Variables and Functions**: Use snake_case for variable names and function names (e.g., `user_data`, `calculate_total`)
- **Classes**: Use PascalCase for class names (e.g., `UserService`, `DataProcessor`)
- **Constants**: Use UPPER_CASE for constants (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private Members**: Prefix private attributes and methods with single underscore (e.g., `_internal_method`)
- **Module Names**: Use short, lowercase module names; avoid underscores unless necessary for readability
- **Meaningful Names**: Choose descriptive names that reveal intent; avoid abbreviations except widely recognized ones (e.g., `db`, `api`, `url`)

### Functions and Methods

- **Single Responsibility**: Each function should do one thing and do it well; keep functions focused on a single task
- **Function Length**: Keep functions under 50 lines; extract complex logic into helper functions
- **Arguments**: Limit function arguments to 4-5 parameters; use dataclasses or Pydantic models for complex parameter sets
- **Default Arguments**: Avoid mutable default arguments (lists, dicts); use None and initialize in function body
- **Return Values**: Be consistent with return types; use Optional[T] for functions that may return None
- **Side Effects**: Minimize side effects; clearly document functions that modify state or perform I/O operations

### Classes and Objects

- **Class Design**: Follow SOLID principles; keep classes focused with clear responsibilities
- **Dataclasses**: Use @dataclass decorator for simple data containers instead of writing boilerplate __init__ methods
- **Inheritance**: Prefer composition over inheritance; use inheritance only for clear "is-a" relationships
- **Magic Methods**: Implement magic methods (__str__, __repr__, __eq__) for better debugging and object comparison
- **Properties**: Use @property decorator for computed attributes and controlled access to private attributes
- **Class vs Instance Methods**: Use @classmethod for alternate constructors; use @staticmethod for utility functions that don't need instance/class

### Error Handling

- **Specific Exceptions**: Catch specific exception types rather than bare except clauses
- **Custom Exceptions**: Define custom exception classes for domain-specific errors inheriting from appropriate base exceptions
- **Exception Context**: Use `raise ... from ...` to preserve exception context when re-raising or wrapping exceptions
- **Resource Cleanup**: Use try/finally or context managers to ensure cleanup code runs even when exceptions occur
- **Logging**: Log exceptions with full stack traces using logger.exception() in except blocks
- **Fail Fast**: Validate inputs early and raise exceptions immediately rather than allowing invalid state to propagate

### Asynchronous Programming

- **async/await**: Use async/await for I/O-bound operations; avoid blocking operations in async functions
- **Async Context Managers**: Use async with for async resource management (database sessions, HTTP clients)
- **Task Management**: Use asyncio.create_task() for concurrent operations; avoid asyncio.ensure_future()
- **Timeouts**: Implement timeouts for all async operations using asyncio.wait_for() to prevent hanging
- **Async Libraries**: Use async-compatible libraries (httpx, asyncpg, aioboto3) in async contexts
- **Event Loop**: Don't create or manage event loops explicitly; let the framework (FastAPI, asyncio.run) handle it

### Performance and Optimization

- **Lazy Evaluation**: Use generators and iterators for large datasets instead of loading everything into memory
- **Caching**: Use functools.lru_cache or similar for expensive pure functions; consider TTL-based caching for dynamic data
- **String Building**: Use ''.join() for building strings from sequences; avoid repeated string concatenation
- **Data Structures**: Choose appropriate data structures (sets for membership tests, deques for queues, defaultdict for grouping)
- **Profiling**: Profile before optimizing; use cProfile or line_profiler to identify actual bottlenecks
- **Database Queries**: Minimize database round trips; use bulk operations and eager loading where appropriate

### Security Best Practices

- **Input Validation**: Validate and sanitize all user input; use Pydantic models for structured validation
- **SQL Injection**: Never interpolate user input into SQL queries; use parameterized queries or ORM methods
- **Secrets Management**: Never hardcode secrets; use environment variables or secret management services
- **Password Storage**: Hash passwords with bcrypt, argon2, or similar; never store plaintext passwords
- **Authentication**: Use established libraries (python-jose, passlib) for JWT tokens and password hashing
- **Rate Limiting**: Implement rate limiting for public endpoints to prevent abuse and DoS attacks

### Testing Standards

- **Test Organization**: Mirror source structure in test directory; name test files test_<module>.py
- **Test Naming**: Use descriptive test function names: test_<function>_<scenario>_<expected_result>
- **Fixtures**: Use pytest fixtures for common test setup; scope fixtures appropriately (function, class, module, session)
- **Mocking**: Use unittest.mock or pytest-mock for mocking external dependencies and isolating units
- **Assertions**: Use specific assertions (assert == for equality, assert in for membership) over generic assert True
- **Test Data**: Keep test data small and focused; use factories or fixtures for complex object creation

### Logging and Debugging

- **Structured Logging**: Use structured logging with context (user_id, request_id) for better log analysis
- **Log Levels**: Use appropriate log levels: DEBUG for detailed info, INFO for normal flow, WARNING for issues, ERROR for failures
- **Sensitive Data**: Never log passwords, tokens, or PII; sanitize log messages containing user data
- **Performance Logging**: Log slow operations with timing information to identify performance issues
- **Correlation IDs**: Include correlation/request IDs in logs to trace requests through distributed systems

### Dependencies and Environment

- **Virtual Environments**: Always use virtual environments (venv, virtualenv) for project isolation
- **Requirements Files**: Maintain requirements.txt or pyproject.toml with pinned versions for reproducible builds
- **Dependency Updates**: Regularly update dependencies; test thoroughly before deploying updates
- **Minimal Dependencies**: Only include necessary dependencies; avoid large frameworks for simple tasks
- **Environment Variables**: Use python-dotenv or similar for local development; document all required environment variables
- **Python Version**: Specify minimum Python version in project documentation and pyproject.toml

### Code Organization

- **Module Structure**: Organize code into logical modules; avoid circular dependencies
- **Package Layout**: Use src/ layout for packages; include __init__.py files in package directories
- **Configuration**: Centralize configuration in a dedicated config module using Pydantic Settings or similar
- **Constants**: Define constants in a dedicated constants.py or at module level; avoid magic numbers
- **Utility Functions**: Group related utility functions in helper modules; avoid creating "utils dumping ground"
- **Business Logic**: Separate business logic from framework code (routes, views) for better testability

### Documentation

- **README**: Include installation, setup, and basic usage instructions in README.md
- **API Documentation**: Document public APIs with clear docstrings including parameters, return values, and examples
- **Type Annotations**: Use type hints as inline documentation; they serve as executable documentation
- **Comments**: Write comments explaining "why" not "what"; the code should be self-explanatory for "what"
- **Changelog**: Maintain CHANGELOG.md for significant changes, bug fixes, and new features
- **Architecture Docs**: Document high-level architecture decisions and design patterns used

### Backward Compatibility

- **Breaking Changes**: Avoid breaking changes unless specifically required; use deprecation warnings before removal
- **Deprecation Path**: Provide clear migration paths when deprecating functionality; maintain deprecated code for at least one version
- **Version Semantics**: Follow semantic versioning (SemVer) for library code; communicate version changes clearly
- **Default Behavior**: Unless explicitly instructed, do not write additional logic for backward compatibility; clean implementation preferred
