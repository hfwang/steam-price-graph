#!/usr/bin/env python

import math
import datetime
import time
import SteamApi
import webapp2
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext.webapp import util
import relative_dates


class SteamGame(db.Model):
    name = db.StringProperty()
    steam_id = db.StringProperty()
    pickled_price_change_list_date = db.ListProperty(long)
    pickled_price_change_list_price = db.ListProperty(float)

    last_updated_on = db.DateTimeProperty(auto_now=True)
    created_on = db.DateTimeProperty(auto_now_add=True)

    def get_current_price(self):
        if len(self.pickled_price_change_list_price):
            return self.pickled_price_change_list_price[0]
        else:
            return None

    def set_current_price(self, price):
        def should_update(new_price, price_change_list):
            if len(price_change_list):
                current_price = price_change_list[0][1]

                if current_price is None and new_price is None:
                    # Already know this has no price.
                    return False
                elif ((abs(price - current_price) < 0.01)):
                    # Price didn't change
                    return False
                else:
                    return True
            else: # Need to write first entry
                return True
        if not should_update(price, self.price_change_list):
            return

        now = long(time.time())
        self.pickled_price_change_list_date.insert(0, now)
        self.pickled_price_change_list_price.insert(0, price)

    current_price = property(get_current_price, set_current_price)

    def get_price_change_list(self):
        return zip(self.pickled_price_change_list_date, self.pickled_price_change_list_price)

    price_change_list = property(get_price_change_list)

    @staticmethod
    def get_key_name(game_id):
        return str(game_id)

    def to_steam_api(self):
        return SteamApi.Game(
            id=self.steam_id, name=self.name, price=self.current_price)

class IndexHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('<title>Steam Price Graph</title>')
        self.response.out.write('''
            <h1>Steam Price Graphs</h1>
            Currently just letting data collect. Pretty graphs will be
            forthcoming when the scraper has done its thing. Contact
            steam-price-graphs at hsiufan dot porkbuns dot net if you have any
            questions.<br /><br />
        ''')
        page = int(self.request.get('page', 1))
        cursor = self.request.get('cursor', None)
        games_query = SteamGame.all().order('name')
        if cursor:
            games_query.with_cursor(cursor)
        games = games_query.fetch(100)

        self.response.out.write('<table>')
        self.response.out.write('<tr><th></th><th>Title</th><th>Price</th></tr>')

        for game in games:
            game = game.to_steam_api()
            self.response.out.write('<tr>')
            self.response.out.write('''
                <td><img src="%s" /></td>
                ''' % game.thumbnail)
            self.response.out.write('''
                <td>
                  %s<br />
                  <a href="%s">Store</a> | <a href="/games/%s">Price graph</a>
                </td>''' % (game.name, game.url, game.id))
            self.response.out.write('<td>$%s</td>' % game.price)
            self.response.out.write('</tr>')
        self.response.out.write('</table>')
        self.response.out.write(
            '<a href="?page=%d&cursor=%s">Next</a>' % (page + 1, games_query.cursor()))

class GameHandler(webapp2.RequestHandler):
    @staticmethod
    def format_datetime(dt):
        timestamp = time.mktime(dt.timetuple())
        time_str = dt.strftime('%Y/%m/%d')
        time_ago = relative_dates.getRelativeTime(timestamp)
        return time_str, time_ago

    def get(self, steam_id):
        game_model = SteamGame.get_by_key_name(SteamGame.get_key_name(steam_id))
        game = game_model.to_steam_api()
        self.response.out.write('<title>Steam Price Graph - %s</title>' % game.name)
        self.response.out.write('<h1>%s</h1>' % game.name)

        time_str, time_ago = GameHandler.format_datetime(game_model.created_on)
        self.response.out.write('First seen %s (%s)<br />' % (time_ago, time_str))

        time_str, time_ago = GameHandler.format_datetime(game_model.last_updated_on)
        self.response.out.write('Last updated %s (%s)<br />' % (time_ago, time_str))

        self.response.out.write('<h2>Price changes</h2>')
        self.response.out.write('<table>')
        for price_change in game_model.price_change_list:
            time_str, time_ago = GameHandler.format_datetime(
                datetime.datetime.fromtimestamp(price_change[0]))

            self.response.out.write('<tr>')
            self.response.out.write('<td>%s</td>' % time_str)
            self.response.out.write('<td>$%.2f</td>' % price_change[1])
            self.response.out.write('<td>%s</td>' % time_ago)
            self.response.out.write('</tr>')
        self.response.out.write('</table>')


class WebHookHandler(webapp2.RequestHandler):
    def get(self, action):
        self.process(action)

    def post(self, action):
        self.process(action)

    def process(self, action):
        if action == 'update':
            self.update()
        elif action == 'update_page':
            self.update_page(int(self.request.get('page')))
        else:
            self.abort(404)

    def update(self):
        number_of_pages = SteamApi.get_number_of_pages()
        for page in xrange(1, number_of_pages + 1):
            taskqueue.add(url='/webhooks/update_page?page=%d' % page, method='GET')
            self.response.out.write('...page %d<br>' % page)
        self.response.out.write('Enqueued %d pages' % number_of_pages)

    def update_page(self, page):
        games = SteamApi.get_games(page)
        for game in games:
            self.response.out.write('Starting: %s...' % game.name)
            game_key_name = SteamGame.get_key_name(game.id)

            game_model = SteamGame.get_by_key_name(game_key_name)
            if not game_model:
                game_model = SteamGame(key_name=game_key_name)

            game_model.steam_id = game.id
            game_model.name = game.name
            game_model.current_price = game.price
            game_model.put()
            self.response.out.write('done -- ')
            self.response.out.write('%r' % game_model.price_change_list)
            self.response.out.write('<br>')
        self.response.out.write('<br>Done.')
        self.response.out.write('<br><a href="?page=%d">Next</a>' % (page + 1))


application = webapp2.WSGIApplication(
    [('/', IndexHandler),
     webapp2.Route('/games/<steam_id>', GameHandler),
     webapp2.Route('/webhooks/<action>', WebHookHandler)],
    debug=True)


def main():
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
