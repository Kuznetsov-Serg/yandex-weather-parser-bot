import logging
import platform
from time import sleep

import requests
import urllib3
from loguru import logger
from requests.exceptions import ProxyError, SSLError
from selenium import webdriver
from selenium.webdriver import Proxy
from selenium.webdriver.common.proxy import ProxyType
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from app.settings import PARSED_CONFIG


def get_page_content(url: str, is_with_session: bool = False):
    # return get_page_content_with_wait(url, wait_sec=0)

    if is_with_session:
        MAX_RETRIES = 20
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

    urllib3.disable_warnings()
    proxies = {"http": PARSED_CONFIG.proxy, "https": PARSED_CONFIG.proxy} if PARSED_CONFIG.proxy else None
    verify = True
    headers = requests.utils.default_headers()
    headers.update(
        {
            "User-Agent": "My User Agent 1.0",
        }
    )
    for attempt in range(3):
        try:
            if is_with_session:
                page = session.get(url, headers=headers, proxies=proxies, allow_redirects=True, verify=verify, timeout=20)
                # page.html.render()
            else:
                page = requests.get(url, headers=headers, proxies=proxies, verify=verify, timeout=20)
        except ProxyError:
            if proxies:
                logger.info(f"ProxyError: Switch-Off PROXY {PARSED_CONFIG.proxy}")
                proxies = None
            else:
                raise
        except SSLError:
            if verify:
                logger.info("SSLError: Switch-Off `verify`")
                verify = False
            else:
                raise
        except requests.exceptions.Timeout:
            raise
        except Exception:
            # return get_page_content_with_wait(url, wait_sec=0)
            raise
        else:
            break

    try:
        if page.status_code == 200:
            return page.content.decode("utf-8")
    except:
        pass
    return ""


def get_page_content_with_wait(url: str, wait_sec: int = 20):
    options = webdriver.FirefoxOptions()
    if PARSED_CONFIG.proxy:
        proxy = Proxy({
            'proxyType': ProxyType.MANUAL,
            'httpsProxy': PARSED_CONFIG.proxy,
            # 'httpProxy': PARSED_CONFIG.proxy,
            # 'ftpProxy': PARSED_CONFIG.proxy,
            'sslProxy': PARSED_CONFIG.proxy,
            'noProxy': ''  # set this value as desired
        })
        # options.proxy = proxy
        options.add_argument(f"--proxy-server={PARSED_CONFIG.proxy}")
    else:
        proxy = None

    options.add_argument('--headless')
    options.add_argument("--ignore-certificate-errors")
    options.set_preference("accept_insecure_certs", True)

    # Create a new instance of the Firefox driver
    if platform.system() == "Windows":
        browser = webdriver.Firefox(options=options)
        # browser = webdriver.Firefox(options=options)
    else:
        browser = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
        # service = webdriver.FirefoxService(executable_path="app/driver/geckodriver")
        # browser = webdriver.Firefox(options=options, service=service)

    # options.profile = "app/driver"
    # options.profile = "app/driver/geckodriver"
    # browser = webdriver.Firefox(options=options)
    # browser = webdriver.PhantomJS()

    try:
        # Set the implicit wait time to 10 seconds
        browser.implicitly_wait(wait_sec)
        browser.get(url)
    except ProxyError:
        if proxy:
            logger.info("ProxyError... Del PROXY and try")
            browser.Proxy = None
            browser.get(url)
        else:
            logger.error("ProxyError without PROXY...")
            raise
    except Exception as err:
        logger.error(err)
        raise

    # waiting for the elements that are created using JavaScript
    page_content = browser.page_source
    browser.quit()
    return page_content


def get_page_content_by_firefox(url: str, wait_sec: int = 20, min_size: int = 0):
    options = webdriver.FirefoxOptions()
    if PARSED_CONFIG.proxy:
        proxy = True
        options.add_argument(f"--proxy-server={PARSED_CONFIG.proxy}")
    else:
        proxy = False

    options.add_argument('--headless')
    options.add_argument("--ignore-certificate-errors")
    options.set_preference("accept_insecure_certs", True)

    # Create a new instance of the Firefox driver
    if platform.system() == "Windows":
        browser = webdriver.Firefox(options=options)
    else:
        service = webdriver.FirefoxService(executable_path="app/driver/geckodriver")
        # options.binary_location = r'app/driver/firefox'
        browser = webdriver.Firefox(options=options, service=service)

    try:
        # Set the implicit wait time
        browser.implicitly_wait(wait_sec)
        browser.get(url)
    except ProxyError:
        if proxy:
            logger.info("ProxyError... Del PROXY and try")
            browser.Proxy = None
            browser.get(url)
        else:
            logger.error("ProxyError without PROXY...")
            raise
    except Exception as err:
        logger.error(err)
        raise

    # waiting for the elements that are created using JavaScript
    # sleep(wait_sec)
    page_content = browser.page_source
    if min_size:
        for attempt in range(10):
            if len(page_content) > min_size:
                break
            sleep(10)
            page_content = browser.page_source

    browser.quit()
    return page_content


def get_page_content_by_chrome(url: str, wait_sec: int = 20):
    options = webdriver.ChromeOptions()
    if PARSED_CONFIG.proxy:
        options.add_argument(f"--proxy-server={PARSED_CONFIG.proxy}")

    options.add_argument('--headless')
    options.add_argument("--ignore-certificate-errors")

    # Create a new instance of the Firefox driver
    if platform.system() == "Windows":
        browser = webdriver.Chrome(options=options)
    else:
        try:
            service = ChromeService(ChromeDriverManager().install())
        except Exception as err:
            logging.ERROR(f"service = ChromeService(ChromeDriverManager().install()): {err}")
            raise
        try:
            browser = webdriver.Chrome(service=service, options=options)
        except Exception as err:
            logging.ERROR(f"browser = webdriver.Firefox(service=service, options=options): {err}")
            raise
    try:
        # Set the implicit wait time
        browser.implicitly_wait(wait_sec)
        browser.get(url)
        # waiting for the elements that are created using JavaScript
        sleep(wait_sec)
        page_content = browser.page_source
    except Exception as err:
        logger.error(err)
        raise

    browser.quit()
    return page_content

