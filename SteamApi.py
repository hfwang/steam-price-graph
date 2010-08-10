from BeautifulSoup import BeautifulSoup
from BeautifulSoup import NavigableString
from soupselect import select
import urllib


class Game(object):
    def __init__(self, id='0', name='', price=0.0, metascore=None):
        self.id = id
        self.name = name
        self.price = price
        self.metascore = metascore

    thumbnail = property(
        lambda self:'http://cdn.steampowered.com/v/gfx/apps/%s/capsule_sm_120.jpg' % self.id)

    url = property(
        lambda self: 'http://store.steampowered.com/app/%s/' % self.id)

    def __str__(self):
        return '%s - %s' % (self.id, self.name)

    def __repr__(self):
        return self.__str__()


def search_result_url(page=1):
    return 'http://store.steampowered.com/search/?sort_by=Name&sort_order=ASC&category1=998&page=%d' % page


def get_number_of_pages():
    soup = BeautifulSoup(urllib.urlopen(search_result_url()))
    pagination = select(soup, 'div.search_pagination_right a')
    return int(pagination[-2].string)


def get_games(page=1):
    def select_first(soup, selector):
        result = select(soup, selector)
        if result and len(result) > 0:
            return result[0]
        else:
            return None

    def inner_text(soup):
        if isinstance(soup, NavigableString):
            return unicode(soup)
        elif soup.contents:
            return u''.join(inner_text(c) for c in soup.contents)
        else:
            return unicode(soup)

    result = []

    soup = BeautifulSoup(urllib.urlopen(search_result_url(page)))
    games = select(soup, 'a.search_result_row')
    for game in games:
        id = str(game['href'][34:-1])
        name = inner_text(select(game, 'h4')[0])
        price = select_first(game, '.search_price')
        if price and price.contents:
            if price.contents[-1] == 'Free':
                price = float(0)
            else:
                # Grab the last node, which is either the price or the "reduced
                # price"
                price = float(price.contents[-1][5:])
        else:
            price = float(-1)

        metascore = select_first(game, '.search_metascore')
        if metascore and metascore.string:
            metascore = int(metascore.string)
        else:
            metascore = None

        result.append(Game(id=id,
                           name=name,
                           price=price,
                           metascore=metascore))

    return result
