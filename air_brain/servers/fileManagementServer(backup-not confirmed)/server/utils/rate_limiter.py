from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

class RateLimiter:
    def __init__(self, max_requests=100, time_window=timedelta(minutes=1)):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, ip_address: str) -> bool:
        with self.lock:
            current_time = datetime.utcnow()
            # Clean up old requests
            self.requests[ip_address] = [
                req_time for req_time in self.requests[ip_address]
                if current_time - req_time <= self.time_window
            ]

            # Check if rate limit is exceeded
            if len(self.requests[ip_address]) >= self.max_requests:
                return False

            # Add new request
            self.requests[ip_address].append(current_time)
            return True

    def get_remaining_requests(self, ip_address: str) -> int:
        with self.lock:
            current_time = datetime.utcnow()
            valid_requests = [
                req_time for req_time in self.requests[ip_address]
                if current_time - req_time <= self.time_window
            ]
            return max(0, self.max_requests - len(valid_requests)) 