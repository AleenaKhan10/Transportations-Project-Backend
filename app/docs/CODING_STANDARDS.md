# Coding Standards & Best Practices

## Configuration Management

### Environment Variables
- **Do not use `os.getenv()` directly** in application code.
- All environment variables must be defined in `app/config.py` using the Pydantic `BaseSettings` model.
- Access configuration values via the `settings` object imported from `config`.

**Example:**
```python
# Bad
import os
secret = os.getenv("MY_SECRET")

# Good
from config import settings
secret = settings.MY_SECRET
```
