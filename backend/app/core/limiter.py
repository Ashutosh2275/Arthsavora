from slowapi import Limiter
from slowapi.util import get_remote_address

# This limits users by their IP address to prevent DDoS and Brute Force
limiter = Limiter(key_func=get_remote_address)