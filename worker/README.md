# Worker

The worker deliberately imports the same installed Python package as the API instead of
maintaining a second dependency graph. Its entry point is `app.worker:celery_app`, and Compose
runs it from the shared backend image. This directory documents that boundary without duplicating
runtime code.

