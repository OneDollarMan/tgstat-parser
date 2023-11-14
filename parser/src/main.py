import logging
import threading
from time import sleep
import requests
from bs4 import BeautifulSoup
import models
import crud
from db_init import engine
import re

CHANNELS_URL = 'https://tgstat.ru/ratings/channels'
CHATS_URL = 'https://tgstat.ru/ratings/chats'
NEXT_CHANNEL_URLS = []
NEXT_CHAT_URLS = []
lock = threading.Lock()


# get urls for top-100 channels of every category
def get_urls_to_categories(url):
    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
    res = []
    page = requests.get(url=url, headers=headers)
    if page.status_code != 200:
        logging.error('Category urls parsing error')
        return res
    soup = BeautifulSoup(page.text, "html.parser")
    try:
        links_div = soup.find('div', {'class': 'list-group list-group-flush border rounded'})
        links = links_div.find_all('a')
    except AttributeError:
        logging.critical('cant find needed element on page, may be tgstat blocked your ip and asks for auth?')
        return res
    for link in links:
        res.append('https://tgstat.ru/' + link['href'])
    return res


class Parser(threading.Thread):

    def __init__(self, is_chats_parsing=False):
        super().__init__()
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'}
        self.is_chat_parsing = is_chats_parsing

    # main algorithm of parsing
    def run(self):
        while True:
            with lock:
                if self.is_chat_parsing:
                    if len(NEXT_CHAT_URLS) == 0:
                        break
                    url = NEXT_CHAT_URLS.pop(0)
                else:
                    if len(NEXT_CHANNEL_URLS) == 0:
                        break
                    url = NEXT_CHANNEL_URLS.pop(0)
            res = requests.get(url=url, headers=self.headers)
            if res.status_code != 200:
                logging.warning(res)
                break
            else:
                html_channels = self.find_entities_on_page(res)
                for ch in html_channels:
                    ch_obj = self.get_entity_object_from_html(ch)
                    if ch_obj is not None:
                        with lock:
                            if crud.save_entity(ch_obj):
                                logging.warning(f'saved {ch_obj.type} {ch_obj.name} ({ch_obj.category.name})')

    # parses all channels from top-100 page to html form
    def find_entities_on_page(self, res):
        try:
            soup = BeautifulSoup(res.text, "html.parser")
            channels_list = soup.find('div', {'id': 'sticky-center-column'})
            channels_hrefs = channels_list.find_all('a', {'target': '_blank'})
            return channels_hrefs
        except AttributeError:
            logging.critical('cant find entities on page, you got banned(')
        return None

    # transform channel from html to object form
    def get_entity_object_from_html(self, ch):
        tgstat_url = ch['href']
        subs_count = ch.find('div', {'class': 'text-truncate font-14 text-dark mt-n1'}).text.strip()
        if self.is_chat_parsing:
            tg_type = models.TypeEnum.chat
            url = re.findall(r'/chat/(.*?)/stat', tgstat_url)[0]  # get tg alias from tgstat url by regual exp
            subs_count = int(subs_count[:subs_count.find('у') - 1].replace(' ', ''))  # get count of subscribers
        else:
            tg_type = models.TypeEnum.channel
            url = re.findall(r'/channel/(.*?)/stat', tgstat_url)[0]  # get tg alias from tgstat url by regual exp
            subs_count = int(subs_count[:subs_count.find('п') - 1].replace(' ', ''))  # get count of subscribers
        if url[0] != '@':
            url = 'https://t.me/joinchat/' + url
        else:
            url = 'https://t.me/' + url[1:]
        if self.is_entity_in_db(url):
            logging.error(f'telegram entity already exists: {url}')
            return None
        name = ch.find('div', {'class': 'text-truncate font-16 text-dark mt-n1'}).text.strip()
        category_name = ch.find('span', {'class': 'border rounded bg-light px-1'}).text.strip()
        category_id = self.get_category_id(category_name)
        description = self.get_entity_description(tgstat_url)
        return models.TelegramEntity(name=name, url=url, type=tg_type, subs_count=subs_count, description=description,
                                     category_id=category_id)

    def get_entity_description(self, url):
        res = requests.get(url=url, headers=self.headers)
        try:
            soup = BeautifulSoup(res.text, "html.parser")
            desc = soup.find('div', {'class': 'col-12 col-sm-7 col-md-8 col-lg-6'})
            desc = ''.join(desc.find_all(string=True, recursive=True))
            desc = ' '.join(desc.split())
            return desc
        except AttributeError:
            logging.critical('cant find entity description, maybe you got banned?')

    def is_entity_in_db(self, url):
        with lock:
            if crud.get_entity_by_url(url) is None:
                return False
            else:
                return True

    def get_category_id(self, category_name):
        with lock:
            cat = crud.get_category_by_name(category_name)
            if cat is None:
                cat_id = crud.save_category(models.TelegramCategory(name=category_name)).id
            else:
                cat_id = cat.id
            return cat_id


def main():
    models.Base.metadata.create_all(bind=engine)
    global NEXT_CHANNEL_URLS
    global NEXT_CHAT_URLS
    NEXT_CHANNEL_URLS = get_urls_to_categories(CHANNELS_URL)
    NEXT_CHAT_URLS = get_urls_to_categories(CHATS_URL)
    parsers = []
    for _ in range(5):
        parsers.append(Parser())
    for _ in range(5):
        parsers.append(Parser(is_chats_parsing=True))
    for parser in parsers:
        parser.start()


if __name__ == '__main__':
    main()
