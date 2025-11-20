## FastAPI development standards and best practices

### Application Structure

- **Router Organization**: Organize endpoints into logical routers by resource or domain (users, trips, alerts); keep routers focused
- **Router Registration**: Register all routers in main application file with consistent prefix and tag naming
- **Service Layer**: Separate business logic from route handlers; delegate complex operations to service/logic layer
- **Dependency Injection**: Use FastAPI's dependency injection system for database sessions, authentication, and shared resources
- **App Factory Pattern**: For complex applications, use factory pattern to create app instance with configurable settings
- **Multiple Apps**: Split large applications into separate FastAPI apps for different concerns (main API, admin, ingest services)

### Endpoint Design

- **RESTful Routes**: Follow REST conventions with appropriate HTTP methods (GET, POST, PUT, PATCH, DELETE)
- **Path Parameters**: Use path parameters for resource identification (e.g., `/users/{user_id}`)
- **Query Parameters**: Use query parameters for filtering, pagination, sorting, and optional parameters
- **Request Bodies**: Use Pydantic models for request validation; define separate models for create/update operations
- **Response Models**: Define explicit response_model for all endpoints to control serialization and provide API documentation
- **Status Codes**: Return appropriate HTTP status codes (200 OK, 201 Created, 204 No Content, 400 Bad Request, 404 Not Found, 500 Internal Server Error)

### Pydantic Models

- **Model Separation**: Separate models into request, response, and database models; avoid reusing database models as API models
- **Validation Rules**: Use Pydantic validators for complex validation logic; leverage Field() for constraints (min_length, max_length, regex)
- **Config Class**: Use Config class in models to control ORM mode, schema generation, and field population
- **Optional Fields**: Use Optional[T] or T | None for optional fields; set default values appropriately
- **Nested Models**: Use nested Pydantic models for complex data structures; avoid deeply nested structures that reduce clarity
- **Model Inheritance**: Use inheritance for shared fields across models; define base models for common attributes

### Database Integration

- **Session Management**: Use FastAPI dependency injection for database sessions; ensure sessions are properly closed
- **Transaction Handling**: Wrap related operations in transactions using context managers or explicit commit/rollback
- **Connection Pooling**: Configure connection pool settings (pool_size, max_overflow, pool_pre_ping) for production use
- **Async Database**: Use async database drivers (asyncpg, aiomysql) with async route handlers for better performance
- **ORM Integration**: Use SQLModel or SQLAlchemy with Pydantic models for type-safe database operations
- **Retry Logic**: Implement retry logic with decorators for database operations to handle transient connection failures

### Authentication and Authorization

- **OAuth2 Password Flow**: Use FastAPI's OAuth2PasswordBearer for JWT-based authentication
- **Token Generation**: Generate JWT tokens with appropriate expiration times; include necessary claims (sub, exp, iat)
- **Token Validation**: Create dependency function to validate tokens and extract user information
- **Password Hashing**: Use bcrypt or passlib for secure password hashing; never store plaintext passwords
- **Role-Based Access**: Implement RBAC using dependencies that check user roles/permissions
- **Session Management**: Track active sessions in database for token revocation and security auditing

### Dependency Injection

- **Database Dependencies**: Create dependency functions for database sessions with automatic cleanup
- **Authentication Dependencies**: Define reusable dependencies for authentication (get_current_user, require_admin)
- **Shared Logic**: Extract common validation or data retrieval into dependencies to reduce duplication
- **Dependency Scope**: Understand dependency scopes; use yield for cleanup logic (close sessions, connections)
- **Dependency Composition**: Compose dependencies by using other dependencies as parameters
- **Performance**: Cache expensive dependencies using functools.lru_cache when appropriate

### Error Handling

- **HTTPException**: Use HTTPException for expected errors with appropriate status codes and user-friendly messages
- **Custom Exceptions**: Define custom exception classes for domain errors; map to HTTP exceptions in handlers
- **Exception Handlers**: Register global exception handlers for consistent error responses across the application
- **Error Responses**: Return structured error responses with error code, message, and optional details
- **Validation Errors**: Let FastAPI handle Pydantic validation errors automatically; customize format if needed
- **Error Logging**: Log exceptions with context (user_id, endpoint, request_id) for debugging; integrate with Sentry or similar

### API Documentation

- **Operation Descriptions**: Provide clear descriptions for endpoints using docstrings or description parameter
- **Tags**: Organize endpoints with tags for logical grouping in documentation UI
- **Response Examples**: Include response examples using OpenAPI examples or response_model_examples
- **Deprecation**: Mark deprecated endpoints using deprecated=True parameter; provide migration guidance
- **Schema Descriptions**: Add descriptions to Pydantic model fields using Field(description="...")
- **Documentation URLs**: Customize docs_url, redoc_url, and openapi_url for branded documentation

### Middleware and CORS

- **CORS Configuration**: Configure CORS middleware with specific allowed origins; avoid allow_origins=["*"] in production
- **Request Middleware**: Use middleware for cross-cutting concerns (logging, request ID, timing)
- **Error Middleware**: Implement error handling middleware to catch unhandled exceptions consistently
- **Authentication Middleware**: Consider authentication middleware for apps requiring auth on all endpoints
- **Compression**: Enable GZip middleware for response compression on text-based responses
- **Trusted Hosts**: Use TrustedHostMiddleware to prevent host header attacks

### Async Best Practices

- **Async Route Handlers**: Use async def for route handlers performing I/O operations (database, API calls)
- **Async Dependencies**: Make dependencies async when they perform I/O; mix async and sync dependencies carefully
- **Background Tasks**: Use BackgroundTasks for fire-and-forget operations that don't need to complete before response
- **Blocking Operations**: Run CPU-bound or blocking operations in thread pools using run_in_executor
- **Async Context Managers**: Use async with for async resources (database sessions, HTTP clients)
- **Concurrent Operations**: Use asyncio.gather() for concurrent async operations when order doesn't matter

### Request/Response Handling

- **Request Validation**: Let Pydantic handle request validation automatically; define constraints in models
- **Response Serialization**: Use response_model to control which fields are serialized in responses
- **File Uploads**: Use UploadFile for file uploads; validate file size and type before processing
- **Streaming Responses**: Use StreamingResponse for large file downloads or SSE endpoints
- **Custom Responses**: Return custom Response types (JSONResponse, HTMLResponse) when default serialization insufficient
- **Response Headers**: Set custom headers using Response parameter in route handlers

### Performance Optimization

- **Database Query Optimization**: Use eager loading (joinedload, selectinload) to avoid N+1 query problems
- **Response Caching**: Implement caching for expensive read operations using Redis or in-memory cache
- **Pagination**: Always paginate list endpoints; use limit/offset or cursor-based pagination
- **Field Selection**: Allow clients to select specific fields to reduce response size and improve performance
- **Connection Pooling**: Properly configure database connection pools for expected concurrent load
- **Async I/O**: Use async handlers and libraries for I/O-bound operations to improve throughput

### Testing FastAPI Applications

- **TestClient**: Use FastAPI's TestClient for integration testing endpoints without running actual server
- **Async Testing**: Use pytest-asyncio and httpx.AsyncClient for testing async endpoints
- **Database Testing**: Use test database or in-memory database; reset state between tests
- **Dependency Override**: Override dependencies for testing using app.dependency_overrides
- **Mock External Services**: Mock external API calls and services to isolate tests
- **Authentication Testing**: Create helper functions to generate test tokens for authenticated endpoints

### Configuration Management

- **Pydantic Settings**: Use Pydantic BaseSettings for configuration with environment variable loading
- **Environment Files**: Support .env files for local development using python-dotenv
- **Secrets**: Load secrets from environment variables or secret management services; never commit secrets
- **Config Validation**: Validate configuration on startup; fail fast if required config missing
- **Multiple Environments**: Support multiple environments (dev, staging, prod) with separate configs
- **Config Access**: Inject config as dependency rather than importing globally for better testability

### Security Best Practices

- **Input Validation**: Rely on Pydantic for input validation; define strict schemas with appropriate constraints
- **SQL Injection Prevention**: Use ORM/query builders with parameterized queries; never interpolate user input into SQL
- **XSS Prevention**: Sanitize output when rendering HTML; use Content-Security-Policy headers
- **CSRF Protection**: Implement CSRF tokens for state-changing operations in web forms
- **Rate Limiting**: Implement rate limiting using middleware or decorators to prevent abuse
- **Security Headers**: Set security headers (X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security)

### Logging and Monitoring

- **Structured Logging**: Use structured logging with JSON format for better log parsing and analysis
- **Request Logging**: Log incoming requests with method, path, status code, and response time
- **Correlation IDs**: Add correlation ID to requests for tracing through distributed systems
- **Error Logging**: Log errors with full stack traces and request context for debugging
- **Performance Metrics**: Track endpoint performance metrics (response time, error rate, throughput)
- **Health Checks**: Implement /health and /ready endpoints for container orchestration and monitoring

### API Versioning

- **URL Versioning**: Version APIs using URL path (e.g., /v1/users) for clear, visible versioning
- **Router Prefixes**: Use router prefixes to organize versioned endpoints
- **Deprecation Strategy**: Maintain old versions while new version stabilizes; communicate deprecation timeline
- **Breaking Changes**: Only introduce breaking changes in new major versions
- **Shared Logic**: Extract shared logic between versions to avoid duplication
- **Documentation**: Clearly document version differences and migration guides

### WebSocket Support

- **WebSocket Endpoints**: Define WebSocket endpoints using @app.websocket decorator
- **Connection Management**: Track active connections; implement proper connection lifecycle (accept, receive, send, close)
- **Error Handling**: Handle WebSocket errors gracefully; close connections on unrecoverable errors
- **Authentication**: Implement authentication for WebSocket connections using tokens or cookies
- **Broadcasting**: Use connection manager pattern for broadcasting messages to multiple clients
- **Heartbeat**: Implement ping/pong heartbeat to detect dead connections

### Background Jobs

- **BackgroundTasks**: Use FastAPI's BackgroundTasks for simple async operations that don't block response
- **Task Queues**: Use Celery, ARQ, or similar for complex background jobs requiring persistence and retry
- **Job Monitoring**: Implement job status tracking for long-running operations
- **Error Handling**: Handle background task errors appropriately; implement retry logic for transient failures
- **Resource Cleanup**: Ensure background tasks clean up resources properly
- **Performance**: Don't overload BackgroundTasks; use dedicated task queue for heavy workloads

### Code Organization

- **Router Files**: Keep router files focused on endpoint definitions; delegate logic to service layer
- **Business Logic**: Place business logic in logic/ or services/ directory separate from route handlers
- **Models Directory**: Organize database models, Pydantic schemas, and DTOs in models/ directory
- **Utils and Helpers**: Create focused utility modules for reusable functions; avoid generic "utils" dumping ground
- **Dependencies File**: Centralize common dependencies in dedicated file (e.g., dependencies.py)
- **Main Application**: Keep main.py focused on app creation, middleware, and router registration

### Deployment Considerations

- **Environment Variables**: Externalize all configuration; use environment variables for deployment-specific settings
- **Startup Events**: Use @app.on_event("startup") for initialization (database connections, cache warming)
- **Shutdown Events**: Use @app.on_event("shutdown") for cleanup (close connections, flush logs)
- **Process Management**: Run with production ASGI server (uvicorn, hypercorn) behind reverse proxy (nginx, traefik)
- **Worker Configuration**: Configure worker count based on available CPU cores and expected I/O blocking
- **Health Monitoring**: Implement health check endpoints for load balancers and orchestration platforms

### API Best Practices

- **Idempotency**: Make PUT and DELETE operations idempotent; use idempotency keys for POST operations when needed
- **Bulk Operations**: Provide bulk endpoints for operations on multiple resources to reduce round trips
- **Partial Updates**: Support PATCH for partial updates; validate that at least one field is being updated
- **Filtering**: Support filtering on list endpoints using query parameters; validate filter values
- **Sorting**: Allow sorting on list endpoints; validate sort fields and directions
- **Hypermedia**: Consider adding HATEOAS links in responses for API discoverability (optional)
