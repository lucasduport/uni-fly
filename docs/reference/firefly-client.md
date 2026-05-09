# Firefly III client

Async httpx wrapper around the [Firefly III v1 REST API][api-docs]. Auth uses a
Personal Access Token created from the Firefly III UI (Profile → OAuth →
Personal Access Tokens).

```python
from unifly_worker.clients.firefly import FireflyClient

async with FireflyClient("http://localhost:8080", token) as fc:
    cat = await fc.create_category("Groceries")
    page = await fc.list_categories()
```

[api-docs]: https://api-docs.firefly-iii.org/

::: unifly_worker.clients.firefly.client.FireflyClient

## Models

::: unifly_worker.clients.firefly.models

## Errors

::: unifly_worker.clients.firefly.errors
