import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_robust_session(retries=3, backoff_factor=1.0, status_forcelist=(500, 502, 503, 504)) -> requests.Session:
    """
    Creates a requests Session with robust retry logic configured.
    Useful for scraping and API calls that might suffer from transient network issues.
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=retries,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        backoff_factor=backoff_factor
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session
