"""
TrustGuard - Rate Limiting

WHY: Without rate limiting, anyone could spam our API with thousands of requests
     and crash the server or run up our compute costs. Rate limiting says
     "you can only make X requests per minute."

HOW: We use slowapi (a FastAPI wrapper around the 'limits' library).
     It tracks requests per IP address using in-memory storage.
     If someone exceeds the limit, they get a 429 "Too Many Requests" error.

INTERVIEW TIP: "I added rate limiting to prevent API abuse. Detection endpoints
are expensive (they run ML models), so I limit those to 10/minute. Auth endpoints
get 5/minute to prevent brute-force password attacks."
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Track requests by IP address
# In production, you'd use Redis instead of in-memory storage
limiter = Limiter(key_func=get_remote_address)
