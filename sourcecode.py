import os
import json
import time
import random
import string
import asyncio
import logging
from datetime import datetime
import sys
import aiohttp
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from aiohttp import FormData

try:
    from aiogram import Bot, Dispatcher, html, F
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.filters import Command, CommandStart, StateFilter
    from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    AIOGRAM_AVAILABLE = True
except ImportError:
    print("Please install aiogram: pip install aiogram")
    AIOGRAM_AVAILABLE = False
    sys.exit(1)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

# Globals
GLOBAL_IMAGE_PATH = None
TELEGRAM_BOT_TOKEN = "bottoken-here"
IMAGE_URL = "https://i.ibb.co/1JJftbJB/hellio.jpg"
DEFAULT_BIO = "F - 22 , wish me on 21 november."
DEFAULT_CAPTION = "Another good day #shein #sheinverse #sheinforall #sheinyourday"
ADMIN_USER_ID = 7832057078
MANDATORY_CHANNEL = "@scripterpromax"
TARGET_USER_ID = "65418936489"  # ritika_raj836
TARGET_USERNAME = "ritika_raj836"

admin_data = {
    'total_follows': 0,
    'followed_users': set(),
    'broadcast_history': []
}
admin_lock = asyncio.Lock()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONCURRENT_LIMIT = 5
semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

membership_cache = {}

async def retry_async_operation(operation, max_retries=5, base_delay=1):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s")
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(delay)

def generate_timestamp() -> str:
    return str(int(time.time() * 1000))

def generate_random_username(length: int = 12) -> str:
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def generate_random_first_name() -> str:
    first_names = ['Alex', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Quinn', 'Avery', 'Drew', 'Skyler', 'Blake', 'Reese', 'Cameron', 'Finley', 'Rowan']
    return random.choice(first_names)

def parse_cookies(cookie_string: str) -> Dict[str, str]:
    cookies = {}
    if not cookie_string:
        return cookies
    cookie_items = cookie_string.split(';')
    for item in cookie_items:
        item = item.strip()
        if '=' in item and len(item.split('=', 1)) == 2:
            key, value = item.split('=', 1)
            if key in ['ds_user_id', 'sessionid', 'csrftoken']:
                if key == 'rur' and value.startswith('"') and value.endswith('"'):
                    value = value[1:-1].replace('\\"', '"')
                cookies[key] = value
    if not all(k in cookies for k in ['ds_user_id', 'csrftoken']):
        raise ValueError("Missing required cookies: ds_user_id or csrftoken")
    return cookies

def extract_user_id(cookies: Dict[str, str]) -> Optional[str]:
    if 'ds_user_id' in cookies:
        return cookies['ds_user_id']
    elif 'sessionid' in cookies:
        session_parts = cookies['sessionid'].split(':')
        if len(session_parts) > 0:
            return session_parts[0]
    return None

def get_csrf_token(cookies: Dict[str, str]) -> str:
    return cookies.get('csrftoken', '')

async def download_image(url: str, filename: str = "temp_image.jpg") -> Optional[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.read()
                with open(filename, 'wb') as f:
                    f.write(content)
                return filename
    except Exception as e:
        logging.error(f"Error downloading image: {str(e)}")
        return None

async def convert_to_professional(session: aiohttp.ClientSession, cookies: Dict[str, str], csrf_token: str) -> Dict[str, Any]:
    url = 'https://www.instagram.com/api/v1/business/account/convert_account/'
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.instagram.com',
        'priority': 'u=1, i',
        'referer': 'https://www.instagram.com/accounts/convert_to_professional_account/',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.176", "Google Chrome";v="142.0.7444.176", "Not_A Brand";v="99.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR3qb7XILBchTMs48AHJmq-comZxS-PUE8qg7KTFEg6hicbS',
        'x-instagram-ajax': '1030728901',
        'x-requested-with': 'XMLHttpRequest',
        'x-web-session-id': f'pry1s7:z98uwx:{random.randint(1000000, 9999999)}'
    }
    headers['x-csrftoken'] = csrf_token
    data = {
        'category_id': '2700',
        'create_business_id': 'true',
        'entry_point': 'ig_web_settings',
        'set_public': 'true',
        'should_bypass_contact_check': 'true',
        'should_show_category': '0',
        'to_account_type': '3',
        'jazoest': '22689'
    }
    async def op():
        async with session.post(url, headers=headers, data=data, cookies=cookies) as resp:
            resp.raise_for_status()
            return await resp.json()
    return await retry_async_operation(op)

async def get_professional_config(session: aiohttp.ClientSession, cookies: Dict[str, str]) -> Dict[str, Any]:
    url = 'https://www.instagram.com/api/v1/business/account/get_professional_conversion_nux_configuration?is_professional_signup_flow=false'
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'priority': 'u=1, i',
        'referer': 'https://www.instagram.com/accounts/convert_to_professional_account/',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.176", "Google Chrome";v="142.0.7444.176", "Not_A Brand";v="99.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR3qb7XILBchTMs48AHJmq-comZxS-PUE8qg7KTFEg6hicbS',
        'x-requested-with': 'XMLHttpRequest',
        'x-web-session-id': f'pry1s7:z98uwx:{random.randint(1000000, 9999999)}'
    }
    headers['x-csrftoken'] = get_csrf_token(cookies)
    async def op():
        async with session.get(url, headers=headers, cookies=cookies) as resp:
            resp.raise_for_status()
            return await resp.json()
    return await retry_async_operation(op)

async def update_bio(session: aiohttp.ClientSession, cookies: Dict[str, str], csrf_token: str, first_name: str, username: str) -> Dict[str, Any]:
    url = 'https://www.instagram.com/api/v1/web/accounts/edit/'
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.instagram.com',
        'priority': 'u=1, i',
        'referer': 'https://www.instagram.com/accounts/edit/',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.176", "Google Chrome";v="142.0.7444.176", "Not_A Brand";v="99.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR3qb7XILBchTMs48AHJmq-comZxS-PUE8g7KTFEg6hicbS',
        'x-instagram-ajax': '1030728901',
        'x-requested-with': 'XMLHttpRequest',
        'x-web-session-id': f'pry1s7:z98uwx:{random.randint(1000000, 9999999)}'
    }
    headers['x-csrftoken'] = csrf_token
    data = {
        'biography': DEFAULT_BIO,
        'chaining_enabled': 'on',
        'external_url': '',
        'first_name': first_name,
        'username': username,
        'jazoest': '22689'
    }
    async def op():
        async with session.post(url, headers=headers, data=data, cookies=cookies) as resp:
            resp.raise_for_status()
            return await resp.json()
    return await retry_async_operation(op)

async def change_profile_picture(session: aiohttp.ClientSession, cookies: Dict[str, str], csrf_token: str, image_path: str) -> Dict[str, Any]:
    url = 'https://www.instagram.com/api/v1/web/accounts/web_change_profile_picture/'
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'origin': 'https://www.instagram.com',
        'priority': 'u=1, i',
        'referer': 'https://www.instagram.com/accounts/edit/',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.176", "Google Chrome";v="142.0.7444.176", "Not_A Brand";v="99.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR3qb7XILBchTMs48AHJmq-comZxS-PUE8g7KTFEg6hicbS',
        'x-instagram-ajax': '1030728901',
        'x-requested-with': 'XMLHttpRequest',
        'x-web-session-id': f'pry1s7:z98uwx:{random.randint(1000000, 9999999)}'
    }
    headers['x-csrftoken'] = csrf_token
    form = FormData()
    form.add_field('profile_pic', open(image_path, 'rb'), filename=os.path.basename(image_path), content_type='image/jpeg')
    async def op():
        async with session.post(url, headers=headers, data=form, cookies=cookies) as resp:
            resp.raise_for_status()
            return await resp.json()
    return await retry_async_operation(op)

async def check_coppa_status(session: aiohttp.ClientSession, cookies: Dict[str, str], user_id: str) -> tuple:
    url = 'https://www.instagram.com/graphql/query'
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.instagram.com/',
        'priority': 'u=1, i',
        'referer': 'https://www.instagram.com/',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.176", "Google Chrome";v="142.0.7444.176", "Not_A Brand";v="99.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-bloks-version-id': 'fb51dcf4bf4da3cf8bfc28f96ee156f67b02f1fc66bc2885d40cd36dcaf75a04',
        'x-ig-app-id': '936619743392459',
        'x-root-field-name': 'xdt_viewer'
    }
    headers['x-csrftoken'] = get_csrf_token(cookies)
    timestamp = generate_timestamp()
    data = {
        'av': user_id,
        '__d': 'www',
        '__user': '0',
        '__a': '1',
        '__req': '2s',
        '__hs': '20428.HCSV2%3Ainstagram_web_pkg.2.1...0',
        'dpr': '2',
        '__ccg': 'GOOD',
        '__rev': '1030728901',
        '__s': f'pry1s7:z98uwx:{random.randint(1000000, 9999999)}',
        '__hsi': '7580731035905545138',
        '__dyn': '7xeUjG1mxu1syUbFp41twWwIxu13wvoKewSAwHwNw9G2S7o2vwa24o0B-q1ew6ywaq0yE462mcw5Mx62G5UswoEcE7O2l0Fwqo31w9O1lwxwQzXwae4UaEW2G0AEco5G1Wxfxm16wUwtE1wEbUGdG1QwTU9UaQ0Lo6-3u2WE5B08-269wr86C1mgcEed6hEhK2O4Xxui2qi7E5y4UrwHwGwa6bBK4o16UsxWawOwi84q2i1cw',
        '__csr': 'l0AMXsYIDb8IrlhJiYiIth1ozGHAFbtvkyKmLXFoZ5xcBV8GHJlrVd4KWnAOqrlahuYyWsJK8gigWHAiHheKjL-RUSqETye5dajJ4jFO4JALyagnzF49gj8qV4mFby4-XhWm8WKqA9CU-7ynjWyokz9WAyqLUOii48KFUGKF8Wbjyqht3GBiy98yFXyHyohy-bwzzEkAxC7E4y0Co2vz801nSkEjgSXw16q16g3gg4Z0Dw4wg27wh8iyHwZweDw5UwEw3s201z2uE2_yb82qq0fac3dK1JwywzwmpBc1nK8N2wEwho768gmVUyfgkSEjgW5ya0lsayF31na0nScwKxm0i-9wTYEhKHo06Uq0J60acw1J60TE0onwmo',
        '__hsdp': 'g66kamZKHE4xk2oAtZag4HxgJjFjcgVz2Pqb3p25xgs95p6XeK8qzj0ywJehth2gdoZxWcgCuUoDIw8EoBBg89qE4xAUGemWIJ28SeWBF2kDu8BBzE4gEdjJu2q8xa64UkGXwSwpES9xOqm6Fo2ohWyogwoEak7oaQ3aewBxu1bKmh3UG3S0Dp81fe2m0gnw32E0yadxW0Fo6G4EeU2fg1AU30w8K08fwc-bwGx60mCm3S3C9G8DwbK0C4',
        '__hblp': '0n88EfEa872fAwVg9ooy46BwBwQAwr8-18zU898iyaHyVVV8Ki4UkKEcUb7xSWIKFEGEXmh9aHyudrg4it2pFfgWm7ESEJ28y4FoSS-cBGAWxq4ECi6EKFKmF4i6kdyosGV6EKmjK0C4uFrypAbG2efByoW2qAqayUaQ2Kl3Eyfz8nx23GVoiGagd9U5u7onyF981fe2m482hwolKE5i08mwhE521_w8y0UoqxOdxW12woEeUbEgUeVU622p0g9o1j830w8K1dw6QDAxa321dyUa8ybwGx6220Bo5KE424FpU-2aEK252ECEyF8a8swr8y1rwRAQ',
        '__sjsp': 'g5l6hpgFrSWKwi5g9yhTQF0iK52ReBcN3CcbOqb3p25xj62hmhKSWUxG1Kh84a3R2pXxyu2C68cWE4wKazBKHbgydzKEx1mewmiwgEa8y4EcE30wzwdm',
        '__comet_req': '7',
        'fb_dtsg': 'NAfsaJdy10I1Or9tuxalFiRbsjH7tXP9pdVPWxhz6lONyR3chHYBb-A%3A17843729647189359%3A1765026476',
        'jazoest': '26394',
        'lsd': '-xMlyFakDCjzCYXCf9bhWE',
        '__spin_r': '1030728901',
        '__spin_b': 'trunk',
        '__spin_t': timestamp,
        '__crn': 'comet.igweb.PolarisFeedRoute',
        'qpl_active_flow_ids': '379199405',
        'fb_api_caller_class': 'RelayModern',
        'fb_api_req_friendly_name': 'usePolarisCoppaEnforcementStatusViewerQuery',
        'server_timestamps': 'true',
        'variables': '{}',
        'doc_id': '24797863709808827',
        'fb_api_analytics_tags': '["qpl_active_flow_ids=379199405"]'
    }
    async def op():
        async with session.post(url, headers=headers, data=data, cookies=cookies) as resp:
            resp.raise_for_status()
            return await resp.json(), timestamp
    return await retry_async_operation(op)

async def upload_photo(session: aiohttp.ClientSession, cookies: Dict[str, str], image_path: str, upload_id: str) -> Dict[str, Any]:
    url = f'https://i.instagram.com/rupload_igphoto/fb_uploader_{upload_id}'
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'image/jpeg',
        'offset': '0',
        'origin': 'https://www.instagram.com',
        'priority': 'u=1, i',
        'referer': 'https://www.instagram.com/',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-entity-length': str(os.path.getsize(image_path)),
        'x-entity-name': f'fb_uploader_{upload_id}',
        'x-entity-type': 'image/jpeg',
        'x-ig-app-id': '936619743392459',
        'x-instagram-ajax': '1030728901',
        'x-instagram-rupload-params': json.dumps({
            "media_type": 1,
            "upload_id": str(upload_id),
            "upload_media_height": 215,
            "upload_media_width": 215
        }),
        'x-web-session-id': f'pry1s7:z98uwx:{random.randint(1000000, 9999999)}'
    }
    async def op():
        with open(image_path, 'rb') as f:
            data_content = f.read()
            async with session.post(url, headers=headers, data=data_content, cookies=cookies) as resp:
                resp.raise_for_status()
                return await resp.json()
    return await retry_async_operation(op)

async def configure_media_post(session: aiohttp.ClientSession, cookies: Dict[str, str], upload_id: str) -> Dict[str, Any]:
    url = 'https://www.instagram.com/api/v1/media/configure/'
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.instagram.com',
        'priority': 'u=1, i',
        'referer': 'https://www.instagram.com/',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.176", "Google Chrome";v="142.0.7444.176", "Not_A Brand";v="99.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': 'hmac.AR3qb7XILBchTMs48AHJmq-comZxS-PUE8g7KTFEg6hicbS',
        'x-instagram-ajax': '1030728901',
        'x-requested-with': 'XMLHttpRequest',
        'x-web-session-id': f'pry1s7:z98uwx:{random.randint(1000000, 9999999)}'
    }
    headers['x-csrftoken'] = get_csrf_token(cookies)
    data = {
        'archive_only': 'false',
        'caption': DEFAULT_CAPTION,
        'clips_share_preview_to_feed': '1',
        'disable_comments': '0',
        'disable_oa_reuse': 'false',
        'igtv_share_preview_to_feed': '1',
        'is_meta_only_post': '0',
        'is_unified_video': '1',
        'like_and_view_counts_disabled': '0',
        'media_share_flow': 'creation_flow',
        'share_to_facebook': '',
        'share_to_fb_destination_type': 'USER',
        'source_type': 'library',
        'upload_id': str(upload_id),
        'video_subtitles_enabled': '0',
        'jazoest': '22689'
    }
    async def op():
        async with session.post(url, headers=headers, data=data, cookies=cookies) as resp:
            resp.raise_for_status()
            return await resp.json()
    return await retry_async_operation(op)

async def follow_target_user(session: aiohttp.ClientSession, cookies: Dict[str, str], csrf_token: str, target_user_id: str) -> Dict[str, Any]:
    url = 'https://www.instagram.com/graphql/query'
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.instagram.com',
        'priority': 'u=1, i',
        'referer': 'https://www.instagram.com/',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.60", "Google Chrome";v="142.0.7444.60", "Not_A Brand";v="99.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-bloks-version-id': 'fb51dcf4bf4da3cf8bfc28f96ee156f67b02f1fc66bc2885d40cd36dcaf75a04',
        'x-ig-app-id': '936619743392459',
        'x-root-field-name': 'xdt_create_friendship'
    }
    headers['x-csrftoken'] = csrf_token
    spin_t = str(int(time.time()))
    data = {
        'av': target_user_id,
        '__d': 'www',
        '__user': '0',
        '__a': '1',
        '__req': '1k',
        '__hs': '20431.HCSV2%3Ainstagram_web_pkg.2.1...0',
        'dpr': '2',
        '__ccg': 'GOOD',
        '__rev': '1030790060',
        '__s': f'sxreuy%3Apd6ayu%3Apg8p86{random.randint(1000000, 9999999)}',
        '__hsi': '7581799279816732460',
        '__dyn': '7xeUjG1mxu1syaxG4Vp41twWwIxu13wvoKewSAwHwNw9G2Saxa0DU6u3y4o0B-q1ew6ywMwto2awgo9oO0n24oaEnxO1ywOwv89k2C1Fwc60AEC1lwlE-U2exi4UaEW2G0AEco5G1Wxfxm16wUwxwl8vw5ywLyESE7i3vwDwHg2cwMwrUK2K2WE5B08-269wr86C1mgcEed6hEhK3ibK5V89FbxG1oxe6UaUaE2xyVrx60hK798pyFEaU4y16wAwj8',
        '__csr': f'gggvEAG9fd48bhREL5hDnvFtON5Bya8BpchllDWbijx15S8yBXm9vQnymJuj_KtWBh5pICJtAjrjZkFR-L8qmRzFKVpVpbKFplQCayFGChbgyFK-AKUWrrzWTThayWG9CJe9h4Gy9aJdfy8tm9KDBGcAEKuqtBmDWzpWyypAbgvJkcUWUyjCF4-9ATKeBx2dAmqiV8-mm8giK5e8qxeaCw5dwUw05sLBppaqFvU3EK68a42K440bbhExphNU7y0HOKowKpAx-2a9wam3G3a7VaOBxihzIUGfUao19VbU5u8wxxW0-uTgd9E2ZXoTodE7mUvw4Gw2edw2Xo6Wu1kxq3-9yOQU1zBd9omgIw3mGi8whk1tgkKl0fq1lwFULizE6-0ia225588o24w9uUZ1na7GK8N2wFxC2yazQtwYw_oe8r9yla14zo8pS3y6FE4gkbwEgGbDm92EK0qGUO3u0Px3mdUbE169U06Gi0h9wvpeBlwpZ0dy4e0eRLmchuE0Dq8w7ow5Rw1dK1STyRwGV814Egw{random.randint(1000000, 9999999)}',
        '__hsdp': 'gfx099gCjL8W1c2vYGeqybCkwBglRoIgiyqjRahhL3h2NcneG49MYQsVjMhgJ1ff6kwjNgCTSoz6d-49m4A2zxC32Q16wvcEoG66351G0im08Hwvk0jW0hC0c3wg80i2xu2C0I88E1HU2_wbG0uu0LUC0l-19xq',
        '__hblp': '08aEdU5-2C5WwAwyyohwMwNixSi2e12Kcwu8kx659GAQdyo8Xxt5wHwgaby89HUrxO-9XK-quJ2ELxi8hoW9yK596WAV-l38e9qxW6oix56yUalAGt1SidwJG26fAKbgWaCzE98gwTDwRwxAgOF8oxnyAEyiWgOi2e2GbgyUDK4Q7kEeoGrKfz45oO2yi8yo8p9VFE3szUmw8i0J21W3eU4-Ki483cwPKVp8gwwG8xO4E2owb61SKax616wqEpwce10wZK3O4Unwwy8gwzzp8aUfbxR0NGfwcu0EE2_Dyovw-wIxO2e0Jokwd226m48S1kwEwxgC3i1twrWwKxKdh8hx6225e2-FU9E9XO12ucwZwIwSzo4i689dBwFy8',
        '__sjsp': 'gfx0pNQNgCjL8W1c2vYGeqybCkwBglRoIgiyqjRahhL3h2NcneG49MYQsVjMhh3584YYpi1f52rvpycoTUgBoigae6od416w9W',
        '__comet_req': '7',
        'fb_dtsg': 'NAftuRPUL29Cb09Stp1oFqn_XfjhPQ2hJBnEdzk8fC-37p3tCLczmMw%3A17854231342124680%3A1765275200',
        'jazoest': '26232',
        'lsd': 'h7UyspUzcdPXzQjjZ2-zoU',
        '__spin_r': '1030790060',
        '__spin_b': 'trunk',
        '__spin_t': spin_t,
        '__crn': 'comet.igweb.PolarisProfilePostsTabRoute',
        'fb_api_caller_class': 'RelayModern',
        'fb_api_req_friendly_name': 'usePolarisFollowMutation',
        'server_timestamps': 'true',
        'variables': json.dumps({"target_user_id": target_user_id, "container_module": "profile", "nav_chain": "PolarisOneTapAfterLoginRoot:OneTapUpsellPage:1:via_cold_start,PolarisProfilePostsTabRoot:profilePage:2:unexpected"}),
        'doc_id': '9740159112729312'
    }
    async def op():
        async with session.post(url, headers=headers, data=data, cookies=cookies) as resp:
            resp.raise_for_status()
            return await resp.json()
    return await retry_async_operation(op)

selenium_pool = ThreadPoolExecutor(max_workers=3)

def sync_generate_redirect_link(cookies: Dict[str, str]) -> tuple:
    driver = None
    max_retries = 3
    for retry_attempt in range(max_retries):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--remote-debugging-port=0")
            driver = webdriver.Chrome(options=chrome_options)
            logging.info("Navigating to Instagram main page...")
            driver.get("https://www.instagram.com")
            logging.info("Adding Instagram cookies...")
            cookies_to_add = []
            for cookie_name, cookie_value in cookies.items():
                if cookie_name in ['ig_did', 'rur']:
                    continue
                cookie_dict = {
                    'name': cookie_name,
                    'value': cookie_value,
                    'domain': '.instagram.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': False,
                    'sameSite': 'Lax'
                }
                cookies_to_add.append(cookie_dict)
            for cookie_dict in cookies_to_add:
                try:
                    driver.add_cookie(cookie_dict)
                except Exception as e:
                    logging.warning(f"Warning: Could not add cookie {cookie_dict['name']}: {str(e)}")
                    continue
            driver.refresh()
            time.sleep(1)
            logging.info("Navigating to Instagram consent page...")
            CONSENT_URL = 'https://www.instagram.com/consent/?flow=ig_biz_login_oauth&params_json={"client_id":"713904474873404","redirect_uri":"https://sheinverse.galleri5.com/instagram","response_type":"code","state":null,"scope":"instagram_business_basic","logger_id":"84155d6f-26ca-484b-a2b2-cf3b579c1fc7","app_id":"713904474873404","platform_app_id":"713904474873404"}&source=oauth_permissions_page_www'
            driver.get(CONSENT_URL)
            time.sleep(1)
            logging.info("Looking for 'Allow' button...")
            allow_button = None
            selectors = [
                "//div[contains(text(), 'Allow')]",
                "//button[contains(text(), 'Allow')]",
                "//div[contains(@class, 'x1i10hfl') and contains(text(), 'Allow')]",
                "//div[contains(@class, 'x1i10hfl') and @role='button' and contains(text(), 'Allow')]",
                "//div[contains(@class, 'x1i10hfl') and @role='button' and text()='Allow']",
                "//div[contains(@class, 'x1i10hfl') and @role='button' and normalize-space()='Allow']",
                "//button[@type='submit' and contains(text(), 'Allow')]",
                "//*[contains(@aria-label, 'Allow')]",
                "//div[@role='button' and contains(., 'Allow')]",
                "//span[contains(text(), 'Allow')]/ancestor::div[@role='button']"
            ]
            button_found = False
            for selector in selectors:
                try:
                    allow_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if allow_button:
                        button_found = True
                        break
                except TimeoutException:
                    continue
            if not button_found:
                all_buttons = driver.find_elements(By.XPATH, "//button | //div[@role='button']")
                for button in all_buttons:
                    if "Allow" in button.text or "allow" in button.text.lower():
                        allow_button = button
                        button_found = True
                        break
            if not allow_button:
                raise Exception("Could not find 'Allow' button after all attempts")
            logging.info("Clicking 'Allow' button...")
            driver.execute_script("arguments[0].click();", allow_button)
            logging.info("Waiting for redirect...")
            redirect_url = None
            oauth_code = None
            max_wait_time = 45
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                current_url = driver.current_url
                logging.info(f"Current URL: {current_url}")
                if "sheinverse.galleri5.com" in current_url and "code=" in current_url:
                    logging.info("Found redirect URL with code!")
                    redirect_url = current_url
                    code_params = parse_qs(urlparse(current_url).query)
                    oauth_code = code_params.get('code', [None])[0]
                    break
                if "instagram.com" not in current_url and "sheinverse.galleri5.com" in current_url:
                    logging.info("Found redirect to sheinverse domain!")
                    redirect_url = current_url
                    code_params = parse_qs(urlparse(current_url).query)
                    oauth_code = code_params.get('code', [None])[0]
                    break
                time.sleep(0.5)
            if redirect_url and oauth_code:
                logging.info(f"✅ Success! Redirect URL with code: {redirect_url}")
                logging.info(f"Extracted OAuth Code: {oauth_code}")
                return redirect_url, oauth_code
            else:
                logging.error("Could not extract code from redirect URL")
                current_url = driver.current_url
                code_params = parse_qs(urlparse(current_url).query)
                oauth_code = code_params.get('code', [None])[0]
                if oauth_code:
                    logging.info(f"Found code in URL: {oauth_code}")
                    return current_url, oauth_code
                raise Exception("No OAuth code found after redirect")
        except WebDriverException as e:
            logging.error(f"WebDriver error on retry {retry_attempt + 1}: {str(e)}")
            if retry_attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise
        except Exception as e:
            logging.error(f"Unexpected error on retry {retry_attempt + 1}: {str(e)}")
            if retry_attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise
        finally:
            if driver:
                driver.quit()
    raise Exception("All retries failed for generate_redirect_link")

async def generate_redirect_link(cookies: Dict[str, str]) -> tuple:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(selenium_pool, sync_generate_redirect_link, cookies)

async def show_admin_panel(message):
    try:
        keyboard = ReplyKeyboardBuilder()
        keyboard.button(text="📊 Statistics")
        keyboard.button(text="📢 Broadcast")
        keyboard.button(text="👥 Followers Report")
        keyboard.button(text="🔧 Settings")
        keyboard.button(text="📤 Export Data")
        keyboard.button(text="🚪 Exit Admin Panel")
        keyboard.adjust(2)
        await message.answer("👑 Admin Panel", reply_markup=keyboard.as_markup(resize_keyboard=True))
        await message.answer("Welcome to the admin panel. Here you can manage the bot and view statistics.")
    except Exception as e:
        logging.error(f"Error in show_admin_panel: {str(e)}")
        await message.answer("❌ Error loading admin panel. Check logs.")

async def show_statistics(message):
    async with admin_lock:
        stats_message = f"📊 Bot Statistics\n\n"
        stats_message += f"Total Follows: {admin_data['total_follows']}\n"
        stats_message += f"Unique Users Followed: {len(admin_data['followed_users'])}\n"
        stats_message += f"Broadcast History: {len(admin_data['broadcast_history'])} messages\n"
        stats_message += f"\nLast 5 Follow Actions:\n"
        recent_follows = admin_data['broadcast_history'][-5:] if admin_data['broadcast_history'] else []
        for i, follow in enumerate(reversed(recent_follows), 1):
            stats_message += f"{i}. {follow}\n"
    await message.answer(stats_message)

async def broadcast_message(message, bot):
    await message.answer("📢 Broadcast Message")
    await message.answer("Enter the message you want to broadcast to all users:")
    await message.answer("This feature would broadcast messages to all users.")

async def show_followers_report(message):
    async with admin_lock:
        report_message = f"👥 Followers Report\n\n"
        report_message += f"Total Follows Completed: {admin_data['total_follows']}\n"
        report_message += f"Target User: {TARGET_USERNAME}\n"
        report_message += f"Followers Gained: {admin_data['total_follows']} (estimated)\n"
        report_message += f"\nFollow Status: Active\n"
    await message.answer(report_message)

async def handle_admin_command(message, bot):
    text = message.text
    if text == "📊 Statistics":
        await show_statistics(message)
    elif text == "📢 Broadcast":
        await broadcast_message(message, bot)
    elif text == "👥 Followers Report":
        await show_followers_report(message)
    elif text == "🔧 Settings":
        await message.answer("🔧 Settings\n\nThis section would contain bot configuration options.")
    elif text == "📤 Export Data":
        await message.answer("📤 Export Data\n\nThis would export bot data and statistics.")
    elif text == "🚪 Exit Admin Panel":
        await message.answer("Exiting admin panel...")
        await message.answer("Use /start to access the main menu.")
    else:
        await message.answer("Unknown command. Please use the buttons in the admin panel.")

async def is_user_in_channel(bot: Bot, user_id: int) -> bool:
    now = time.time()
    if user_id in membership_cache and now < membership_cache[user_id][1]:
        return membership_cache[user_id][0]
    for attempt in range(3):
        try:
            member = await bot.get_chat_member(MANDATORY_CHANNEL, user_id)
            is_member = member.status in ['member', 'administrator', 'creator']
            membership_cache[user_id] = (is_member, now + 300)
            return is_member
        except Exception as e:
            logging.error(f"Error checking membership for {user_id}: {str(e)}")
            if attempt < 2:
                await asyncio.sleep(1 * (2 ** attempt))
    return False

class InstagramAutomationBot:
    def __init__(self):
        self.session = None
        self.cookies = {}
        self.user_id = None
        self.csrf_token = None

    async def init_session(self):
        if self.session is None:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def set_cookies(self, cookie_string: str):
        self.cookies = parse_cookies(cookie_string)
        self.user_id = extract_user_id(self.cookies)
        self.csrf_token = get_csrf_token(self.cookies)

    async def full_setup(self, message) -> str:
        await self.init_session()
        try:
            async with semaphore:
                if not GLOBAL_IMAGE_PATH or not os.path.exists(GLOBAL_IMAGE_PATH):
                    raise Exception("Global image not available. Bot startup failed.")
                first_name = generate_random_first_name()
                username = generate_random_username()
                logging.info(f"Generated random first name: {first_name}")
                logging.info(f"Generated random username: {username}")
                progress_message = await message.answer("⏳ Starting Instagram setup...")
                await progress_message.edit_text("⏳ Converting to professional account...")
                result = await convert_to_professional(self.session, self.cookies, self.csrf_token)
                if result.get('status') != 'ok':
                    raise Exception(f"Failed to convert to professional account: {result}")
                await progress_message.edit_text("⏳ Getting professional configuration...")
                config = await get_professional_config(self.session, self.cookies)
                if config.get('status') != 'ok':
                    raise Exception(f"Failed to get professional configuration: {config}")
                await progress_message.edit_text("⏳ Updating bio...")
                result = await update_bio(self.session, self.cookies, self.csrf_token, first_name, username)
                if result.get('status') != 'ok':
                    raise Exception(f"Failed to update bio: {result}")
                await progress_message.edit_text("⏳ Changing profile picture...")
                result = await change_profile_picture(self.session, self.cookies, self.csrf_token, GLOBAL_IMAGE_PATH)
                if result.get('status') != 'ok':
                    raise Exception(f"Failed to change profile picture: {result}")
                logging.info(f"Following target user {TARGET_USERNAME} for user {self.user_id}")
                follow_result = await follow_target_user(self.session, self.cookies, self.csrf_token, TARGET_USER_ID)
                if follow_result.get('status') == 'ok':
                    async with admin_lock:
                        if self.user_id not in admin_data['followed_users']:
                            admin_data['total_follows'] += 1
                            admin_data['followed_users'].add(self.user_id)
                        admin_data['broadcast_history'].append(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} - User {self.user_id} followed {TARGET_USERNAME}")
                    logging.info(f"Follow action successful for user {self.user_id}")
                else:
                    logging.warning(f"Follow action failed for user {self.user_id} after retries")
                await progress_message.edit_text("⏳ Checking COPPA status...")
                coppa_result, upload_id = await check_coppa_status(self.session, self.cookies, self.user_id)
                if coppa_result.get('status') != 'ok':
                    raise Exception(f"Failed to check COPPA status: {coppa_result}")
                await progress_message.edit_text("⏳ Uploading photo...")
                upload_result = await upload_photo(self.session, self.cookies, GLOBAL_IMAGE_PATH, upload_id)
                if upload_result.get('status') != 'ok':
                    raise Exception(f"Failed to upload photo: {upload_result}")
                await progress_message.edit_text("⏳ Configuring media post...")
                post_result = await configure_media_post(self.session, self.cookies, upload_id)
                if post_result.get('status') != 'ok':
                    raise Exception(f"Failed to create post: {post_result}")
                media_id = post_result.get('media', {}).get('id')
                logging.info(f"Post ID: {media_id}")
                await progress_message.edit_text("⏳ Generating redirect link...")
                redirect_url, oauth_code = await generate_redirect_link(self.cookies)
                if redirect_url and oauth_code:
                    result_msg = "🎉 All tasks completed successfully!\n\n"
                    result_msg += f"Post ID: {media_id}\n"
                    result_msg += f"Redirect URL: {redirect_url}\n"
                    result_msg += f"OAuth Code: {oauth_code}"
                else:
                    result_msg = "❌ Failed to generate redirect link after retries"
                return result_msg
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            return f"❌ Error after retries: {str(e)}"
        finally:
            await self.close_session()

    async def generate_redirect_link_only(self, message) -> str:
        await self.init_session()
        try:
            async with semaphore:
                await message.answer("⏳ Generating redirect link...")
                redirect_url, oauth_code = await generate_redirect_link(self.cookies)
                if redirect_url and oauth_code:
                    return f"🎉 Successfully generated redirect link!\n\nRedirect URL: {redirect_url}\nOAuth Code: {oauth_code}"
                else:
                    return "❌ Failed to generate redirect link after retries"
        except Exception as e:
            logging.error(f"Error generating redirect link: {str(e)}")
            return f"❌ Error after retries: {str(e)}"
        finally:
            await self.close_session()

class BotStates(StatesGroup):
    waiting_for_cookies_full = State()
    waiting_for_cookies_redirect = State()
    admin_panel = State()

def create_main_keyboard():
    keyboard = ReplyKeyboardBuilder()
    keyboard.button(text="🚀 Full Setup")
    keyboard.button(text="🔗 Generate Redirect Link")
    keyboard.button(text="👑 Admin Panel" if ADMIN_USER_ID == 7832057078 else "ℹ️ Help")
    keyboard.adjust(1)
    return keyboard.as_markup(resize_keyboard=True, one_time_keyboard=False)

async def main():
    global GLOBAL_IMAGE_PATH
    logging.info("Downloading shared image at startup...")
    GLOBAL_IMAGE_PATH = await download_image(IMAGE_URL)
    if not GLOBAL_IMAGE_PATH:
        logging.error("Failed to download image at startup. Exiting.")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    @dp.message(CommandStart())
    async def process_start_command(message: Message):
        if not await is_user_in_channel(bot, message.from_user.id):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(text="🔄 Check Again", callback_data="check_membership")]
            ])
            await message.answer(
                f"🚫 Welcome! To use this bot, you must first join our channel: {MANDATORY_CHANNEL}\n\n"
                "After joining, click 'Check Again' to start.",
                reply_markup=keyboard
            )
            return
        await message.answer(f"👋 Welcome to Instagram Automation Bot!", reply_markup=create_main_keyboard())
        await message.answer("I can help you automate Instagram account setup and management.")

    @dp.callback_query(F.data == "check_membership")
    async def check_membership_callback(callback: CallbackQuery):
        if await is_user_in_channel(bot, callback.from_user.id):
            await callback.message.edit_text("✅ Membership verified! Starting bot...", reply_markup=None)
            await process_start_command(callback.message)
        else:
            await callback.answer("❌ Still not joined. Please join the channel and try again.", show_alert=True)

    @dp.message(F.text == "🚀 Full Setup")
    async def process_full_setup(message: Message, state: FSMContext):
        if not await is_user_in_channel(bot, message.from_user.id):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(text="🔄 Check Again", callback_data="check_membership")]
            ])
            await message.answer(
                f"🚫 You must join {MANDATORY_CHANNEL} to use this feature.",
                reply_markup=keyboard
            )
            return
        await message.answer("🔑 Please provide your Instagram cookies in string format:")
        await message.answer("Example: datr=pl_3aJCx0389hjjnGwBOOuzb; ig_did=9547662E-59B7-43A9-BA9A-DD7A767AF000; ...")
        await state.set_state(BotStates.waiting_for_cookies_full)

    @dp.message(BotStates.waiting_for_cookies_full)
    async def process_cookies_full(message: Message, state: FSMContext):
        if not await is_user_in_channel(bot, message.from_user.id):
            await state.clear()
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(text="🔄 Check Again", callback_data="check_membership")]
            ])
            await message.answer(
                f"🚫 Membership check failed. Join {MANDATORY_CHANNEL} first.",
                reply_markup=keyboard
            )
            return
        cookie_string = message.text.strip()
        await state.clear()
        if not cookie_string:
            await message.answer("❌ No cookies provided. Please try again.", reply_markup=create_main_keyboard())
            return
        try:
            bot_instance = InstagramAutomationBot()
            await bot_instance.set_cookies(cookie_string)
            result = await bot_instance.full_setup(message)
            await message.answer(result, reply_markup=create_main_keyboard())
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}", reply_markup=create_main_keyboard())

    @dp.message(F.text == "🔗 Generate Redirect Link")
    async def process_redirect_link(message: Message, state: FSMContext):
        if not await is_user_in_channel(bot, message.from_user.id):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(text="🔄 Check Again", callback_data="check_membership")]
            ])
            await message.answer(
                f"🚫 You must join {MANDATORY_CHANNEL} to use this feature.",
                reply_markup=keyboard
            )
            return
        await message.answer("🔑 Please provide your Instagram cookies in string format:")
        await message.answer("Example: datr=pl_3aJCx0389hjjnGwBOOuzb; ig_did=9547662E-59B7-43A9-BA9A-DD7A767AF000; ...")
        await state.set_state(BotStates.waiting_for_cookies_redirect)

    @dp.message(BotStates.waiting_for_cookies_redirect)
    async def process_cookies_redirect(message: Message, state: FSMContext):
        if not await is_user_in_channel(bot, message.from_user.id):
            await state.clear()
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(text="🔄 Check Again", callback_data="check_membership")]
            ])
            await message.answer(
                f"🚫 Membership check failed. Join {MANDATORY_CHANNEL} first.",
                reply_markup=keyboard
            )
            return
        cookie_string = message.text.strip()
        await state.clear()
        if not cookie_string:
            await message.answer("❌ No cookies provided. Please try again.", reply_markup=create_main_keyboard())
            return
        try:
            bot_instance = InstagramAutomationBot()
            await bot_instance.set_cookies(cookie_string)
            result = await bot_instance.generate_redirect_link_only(message)
            await message.answer(result, reply_markup=create_main_keyboard())
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}", reply_markup=create_main_keyboard())

    @dp.message(F.text == "👑 Admin Panel")
    async def process_admin_panel(message: Message, state: FSMContext):
        if message.from_user.id != ADMIN_USER_ID:
            await message.answer("❌ Access denied. This feature is only available to administrators.")
            return
        try:
            await show_admin_panel(message)
            await state.set_state(BotStates.admin_panel)
        except Exception as e:
            logging.error(f"Error in process_admin_panel: {str(e)}")
            await message.answer("❌ Admin panel failed to load. Check logs.")

    @dp.message(BotStates.admin_panel)
    async def process_admin_command(message: Message, state: FSMContext):
        if message.from_user.id != ADMIN_USER_ID:
            await message.answer("❌ Access denied. This feature is only available to administrators.")
            return
        await handle_admin_command(message, bot)

    @dp.message(F.text == "ℹ️ Help")
    async def process_help(message: Message):
        if not await is_user_in_channel(bot, message.from_user.id):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(text="🔄 Check Again", callback_data="check_membership")]
            ])
            await message.answer(
                f"🚫 Join {MANDATORY_CHANNEL} to access help and features.",
                reply_markup=keyboard
            )
            return
        await message.answer("📋 Available options:")
        await message.answer("🚀 Full Setup - Complete Instagram setup (Professional account + Post + Redirect link)")
        await message.answer("🔗 Generate Redirect link - Generate only redirect link")
        if message.from_user.id == ADMIN_USER_ID:
            await message.answer("👑 Admin Panel - Access admin controls and statistics")
        await message.answer("ℹ️ Help - Show this help message")
        await message.answer("Use the buttons below to navigate.", reply_markup=create_main_keyboard())

    @dp.message()
    async def process_text_message(message: Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state is None:
            if not await is_user_in_channel(bot, message.from_user.id):
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                    [InlineKeyboardButton(text="🔄 Check Again", callback_data="check_membership")]
                ])
                await message.answer(
                    f"🚫 Unknown command. Join {MANDATORY_CHANNEL} to use the bot.",
                    reply_markup=keyboard
                )
                return
            if any(keyword in message.text.lower() for keyword in ['datr=', 'sessionid=', 'csrftoken=']):
                await message.answer("🔑 Detected cookie format. Would you like to use these cookies for Full Setup?")
                keyboard = ReplyKeyboardBuilder()
                keyboard.button(text="✅ Use for Full Setup")
                keyboard.button(text="❌ Cancel")
                keyboard.adjust(1)
                await state.update_data(cookies=message.text.strip())
                await message.answer("Click the button below to proceed:", reply_markup=keyboard.as_markup(resize_keyboard=True, one_time_keyboard=True))
                return
            await message.answer("❓ Unknown command. Use the buttons below or type /start to see available options.", reply_markup=create_main_keyboard())

    @dp.message(F.text == "✅ Use for Full Setup")
    async def process_use_cookies_full(message: Message, state: FSMContext):
        if not await is_user_in_channel(bot, message.from_user.id):
            await state.clear()
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}")],
                [InlineKeyboardButton(text="🔄 Check Again", callback_data="check_membership")]
            ])
            await message.answer(
                f"🚫 Join {MANDATORY_CHANNEL} first.",
                reply_markup=keyboard
            )
            return
        data = await state.get_data()
        cookie_string = data.get('cookies', '')
        await state.clear()
        if not cookie_string:
            await message.answer("❌ No cookies found. Please try again.", reply_markup=create_main_keyboard())
            return
        try:
            bot_instance = InstagramAutomationBot()
            await bot_instance.set_cookies(cookie_string)
            result = await bot_instance.full_setup(message)
            await message.answer(result, reply_markup=create_main_keyboard())
        except Exception as e:
            await message.answer(f"❌ Error: {str(e)}", reply_markup=create_main_keyboard())

    @dp.message(F.text == "❌ Cancel")
    async def process_cancel(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("Operation cancelled.", reply_markup=create_main_keyboard())

    try:
        await dp.start_polling(bot)
    finally:
        selenium_pool.shutdown(wait=True)
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")