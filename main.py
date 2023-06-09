import requests
from selenium.common import TimeoutException
from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium.webdriver import ChromeOptions, Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tabulate import tabulate
import random
import zipfile
import multiprocessing

from DataBase.SQLite import SQLite
from config import API_KEY_PROXY


def main():
    countries = get_countries()
    print(f"Всего стран: {len(countries)}")
    countries = check_countries(countries_=countries)
    print(f"Осталось стран: {len(countries)}")

    for country in countries:
        models = get_models(country)
        if not models:
            print("0", models)
            continue
        print(len(models), models)

        # models = []
        # with open("fail_models.txt") as file:
        #     for row in file.readlines():
        #         models.append({"model": row.strip()})


        data = []
        fail_models = []
        for index, model in enumerate(models):
            print(model)
            phone = get_phone(model['model'])
            telegram = get_telegram()
            if phone or telegram:

                result = get_country()
                if result:
                    city = result[0]
                    country = result[1]
                else:
                    print(model)
                    raise

                telegram = get_telegram()
                nationality = get_nationality()
                name = model['model'].split("/")[2]

                list_ = [name, country, city, nationality, phone, telegram]
                print(f"{index}\t{list_}")
                data.append(list_)

                models.remove(model)
                with open("fail_models.txt", "w") as file:
                    for model in models:
                        file.write(model['model'] + "\n")

        print("ADD")
        sql.executemany("INSERT INTO model VALUES (?, ?, ?, ?, ?, ?)", data)
        sql.commit()

        table = tabulate(data, headers=['name', 'country', 'city', 'nationality', 'phone'], tablefmt="fancy_grid")
        print(table)



def check_countries(countries_):
    sql.execute("SELECT DISTINCT country FROM model")
    result = sql.fetchall()
    result = [f"/escorts/{country[0]}/" for country in result]
    missing_values = [value for value in countries_ if value not in result]
    return missing_values


def create_browser(proxy_: bool = False):
    options = ChromeOptions()
    # ua = UserAgent()
    # options.add_argument(f"--user-agent={ua.random}")
    # options.add_argument('--headless=chrome')

    if proxy_:
        proxy = get_random_proxy(proxies=proxies, url="https://www.eurogirlsescort.com/")
        # print(f"\n\tSet up proxy: {proxy}")
        plugin_file = 'proxy_auth_plugin.zip'
        create_zip(proxy=proxy, plugin_file=plugin_file)

        options.add_extension(plugin_file)
        browser = Chrome(options=options)
    else:
        browser = Chrome(options=options)

    browser.maximize_window()
    browser.get(url=f'https://www.eurogirlsescort.com/')
    wait = WebDriverWait(browser, 10)
    buttons = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "buttons")))
    buttons.find_element(by=By.TAG_NAME, value='a').click()
    return browser


def get_country():
    params = browser.find_element(by=By.CLASS_NAME, value='params')
    location = [div.find_element(by=By.TAG_NAME, value='strong').text for div in params.find_elements(by=By.TAG_NAME, value='div')
                   if div.find_element(by=By.TAG_NAME, value='span').text == 'Location:']

    if location:
        list_ = location[0].split(" / ")
        return list_[0], list_[1]


def get_nationality():
    params = browser.find_element(by=By.CLASS_NAME, value='params')
    nationality = [div.find_element(by=By.TAG_NAME, value='strong').text for div in params.find_elements(by=By.TAG_NAME, value='div')
                   if div.find_element(by=By.TAG_NAME, value='span').text == 'Nationality:']

    if nationality:
        return nationality[0]


def get_telegram():
    count = len(browser.find_elements(by=By.CLASS_NAME, value='icon-telegram'))
    if count > 0:
        div = browser.find_element(by=By.ID, value='js-phone')
        a = div.find_element(by=By.TAG_NAME, value='a')
        return a.text
    else:
        return None


def get_phone(model):
    global browser
    url = f'https://www.eurogirlsescort.com{model}'
    try:
        browser.get(url=url)
        # count = browser.find_elements(by=By.CLASS_NAME, value="list-items")
        # if count:
        #     print("\nПопытка перезагрузки страницы")
        #     browser.get(url=url)
        # wait = WebDriverWait(browser, 10)
        # id = wait.until(EC.presence_of_element_located((By.ID, "js-phone")))
        # a = id.find_element(by=By.TAG_NAME, value='a')
        # headline = browser.find_elements(by=By.CLASS_NAME, value='headline')
        # if headline:
        #     if browser.find_element(by=By.CLASS_NAME, value='headline').text == "Page Not Found":
        #         return

        WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "links")))
        a = browser.find_element(by=By.CLASS_NAME, value='js-phone')
        a.click()
        return a.text

    except TimeoutException:
        browser = create_browser(proxy_=True)
        return get_phone(model)
    # except NoSuchElementException:
    #     time.sleep(5)
    #     a = browser.find_element(by=By.CLASS_NAME, value='js-phone')
    #     return a.text
    except Exception as ex:
        pass


def get_proxies() -> list:
    with requests.Session() as session:
        headers = {"Authorization": f"Token {API_KEY_PROXY}"}
        response = session.get("https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=100",
                               headers=headers)
        if response.status_code == 200:
            proxies = [f"{proxy['username']}:{proxy['password']}@{proxy['proxy_address']}:{proxy['port']}"
                       for proxy in response.json()["results"]]
        else:
            print(f"Failed to get proxy list: {response.status_code}")
    return proxies


def check_proxy(
        session: requests.Session(),
        proxy: str,
        url: str = None
) -> bool:
    """
    Checker for proxy.

    :param
        session: requests.Session()
        proxy: login:password@ip:port or ip:port
        url: checking proxy for this url
    :return: True or False
    """
    proxies = {
        'http': f"http://{proxy}",
        'https': f"http://{proxy}",
    }
    session.proxies = proxies
    try:
        if url:
            # https://i.instagram.com/accounts/login/
            response = session.get(url=url)
        else:
            response = session.get(url='https://www.example.com')
        if 200 <= response.status_code < 400:
            return True
        else:
            return False
    except Exception:
        return False


def get_random_proxy(
        proxies: list,
        url: str = None,
        session: requests.Session = None,
        headers: dict = None
) -> str | None:
    """
    Get a random proxy after checking, if there is no good proxy then it returns None.

    :param
        proxies: list that makes up proxy like this username:password@ip:port
        url: checking proxy for this url
        session: requests.Session() for checking proxy
        headers: headers for requests.Session()
    :return: username:password@ip:port or ip:port
    """

    if not session:
        session = requests.Session()
    if headers:
        session.headers = headers

    for _ in range(len(proxies)):
        proxy = random.sample(proxies, 1)[0]
        if check_proxy(session=session, proxy=proxy, url=url):
            # proxies.remove(proxy)
            return proxy


def create_zip(proxy, plugin_file):
    PROXY_HOST = proxy.split('@')[1].split(":")[0]
    PROXY_PORT = proxy.split('@')[1].split(":")[1]
    PROXY_USER = proxy.split(":")[0]
    PROXY_PASS = proxy.split('@')[0].split(":")[1]
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"76.0.0"
    }
    """

    background_js = """
    let config = {
            mode: "fixed_servers",
            rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
            }
        };
    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }
    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)

    with zipfile.ZipFile(plugin_file, 'w') as zp:
        zp.writestr('manifest.json', manifest_json)
        zp.writestr('background.js', background_js)


def get_models(country):
    models = []
    for item in range(1, 100):
        response = requests.get(f'https://www.eurogirlsescort.com{country}?profile-paginator-page={item}&'
                                f'profile-filter-filter%5Bindependent%5D=1&'
                                f'profile-filter-filter%5Bverified%5D=1&'
                                f'profile-filter-filter%5Blanguage%5D%5B0%5D=140#')
        soup = BeautifulSoup(response.text, 'html.parser')
        div = soup.find(id='js-fix-perpage-inrow')
        if not div:
            return

        if not div.find_all('a'):
            return models

        for model in div.find_all('a'):
            city = div.find('div', class_='info').find('strong').text
            models.append({'model': model['href'],
                           'city': city})


def get_countries():
    response = requests.get('https://www.eurogirlsescort.com/')

    soup = BeautifulSoup(response.text, 'html.parser')
    uls = soup.find_all('ul', {'class': 'js-country-list-openable'})
    countries = []
    for ul in uls:
        for a in ul.find_all('a'):
            countries.append(a['href'])
    return countries


if __name__ == '__main__':
    proxies = get_proxies()
    sql = SQLite('DataBase/database.db')
    browser = create_browser(proxy_=True)
    main()