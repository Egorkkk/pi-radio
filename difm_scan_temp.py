import requests
from bs4 import BeautifulSoup
import json
from pprint import pprint

def fetch_difm_structure():
    url = "https://www.di.fm/"

    # Максимально похожие на браузер заголовки
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "TE": "trailers"
    }

    session = requests.Session()
    session.headers.update(headers)

    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке страницы: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    genres = {}

    # Поиск жанров и каналов
    genre_headers = soup.find_all('h2', class_='heading')
    for header in genre_headers:
        genre_name = header.get_text(strip=True)
        if not genre_name:
            continue

        # Ищем контейнер со списком каналов (класс может меняться, поэтому ищем гибко)
        channel_container = header.find_next_sibling('div', class_='channel-grid')
        if not channel_container:
            # Если класс не совпадает, попробуем найти любой следующий div, содержащий ссылки
            channel_container = header.find_next_sibling('div')
            if not channel_container or not channel_container.find_all('a', class_='channel'):
                continue

        channels = []
        for link in channel_container.find_all('a', class_='channel'):
            name_span = link.find('span', class_='channel-name')
            if name_span:
                channels.append(name_span.get_text(strip=True))
            else:
                # Запасной вариант
                text = link.get_text(strip=True)
                if text:
                    channels.append(text)

        if channels:
            genres[genre_name] = channels

    return genres

if __name__ == "__main__":
    print("Загрузка структуры каналов di.fm...")
    data = fetch_difm_structure()

    if data:
        print("\nНайденные жанры и станции:\n")
        pprint(data, width=120, sort_dicts=False)
        with open("difm_stations.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\nРезультат сохранён в файл 'difm_stations.json'")
    else:
        print("Не удалось получить данные.")