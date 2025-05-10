import os
import json
import time
import re
import requests
from requests.cookies import RequestsCookieJar

# Configuration
BASE_URL = 'https://littleskin.cn/'
MAX_RETRY = 3
RETRY_DELAY = 10  # seconds


def load_credentials():
    """Load credentials from environment variable"""
    creds = os.getenv('USER_INFO')
    if not creds:
        raise ValueError("USER_INFO environment variable not set")
    return json.loads(creds)


def load_headers():
    """Load headers from headers.json file"""
    try:
        with open('headers.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("headers.json file not found")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in headers.json")


def extract_csrf(page_text):
    """Extract CSRF token from HTML page"""
    match = re.search(r'<meta name="csrf-token" content="(\w+)">', page_text)
    if not match:
        raise ValueError("CSRF token not found in page")
    return match.group(1)


def build_url(path):
    """Build full URL from path"""
    return BASE_URL + path.lstrip('/')


def perform_login(session, credentials, headers):
    """Perform login to LittleSkin"""
    # Get login page to obtain CSRF token
    login_url = build_url('auth/login')
    home_page = session.get(login_url)
    home_page.raise_for_status()
    csrf = extract_csrf(home_page.text)

    time.sleep(0.5)

    # Perform login
    login_data = {
        'identification': credentials['handle'],
        'keep': False,
        'password': credentials['password']
    }
    login_headers = headers.copy()
    login_headers['X-CSRF-TOKEN'] = csrf

    login_response = session.post(login_url, data=login_data, headers=login_headers)
    login_response.raise_for_status()

    return csrf


def perform_sign(session, headers):
    """Perform daily sign"""
    # Get user page to obtain new CSRF token
    user_url = build_url('user')
    user_page = session.get(user_url)
    user_page.raise_for_status()
    csrf = extract_csrf(user_page.text)

    time.sleep(0.5)

    # Perform sign
    sign_url = build_url('user/sign')
    sign_headers = headers.copy()
    sign_headers['X-CSRF-TOKEN'] = csrf

    sign_response = session.post(sign_url, headers=sign_headers)
    sign_response.raise_for_status()

    return sign_response.json()


def run_task():
    """Main task to perform login and sign"""
    credentials = load_credentials()
    headers = load_headers()

    session = requests.Session()
    session.cookies = RequestsCookieJar()
    session.headers.update(headers)

    csrf = perform_login(session, credentials, headers)
    time.sleep(0.2)

    result = perform_sign(session, headers)
    print(result)
    if result['code'] != 0:
        raise Exception(result['message'])


def main():
    """Main function with retry logic"""
    for attempt in range(MAX_RETRY):
        try:
            run_task()
            break
        except Exception as err:
            print(f"Attempt {attempt + 1} failed: {err}")
            if attempt < MAX_RETRY - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise Exception("签到失败")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
