"""
Example Celery task for smoke testing
"""
import time
from celery import shared_task


@shared_task(name="example.echo")
def echo(message: str) -> str:
    return f"echo: {message}"


@shared_task(name="example.add")
def add(x: int, y: int) -> int:
    time.sleep(0.1)
    return x + y
