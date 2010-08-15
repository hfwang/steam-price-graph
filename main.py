#!/usr/bin/env python

import math
import datetime
import time
import os

from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

from templates import helpers
from mako.lookup import TemplateLookup
import models
import SteamApi
import webapp2


class RenderMako(object):
  def __init__(self, *args, **kwargs):
    self._lookup = TemplateLookup(*args, **kwargs)

  def __getattr__(self, template_name):
    template_name = '%s.mako.html' % template_name
    return self._lookup.get_template(template_name)


class BaseHandler(webapp2.RequestHandler):
    '''
    Yet another request handler wrapper to add the right dash of
    functionality. Sigh.
    '''
    renderer_ = RenderMako(directories=['templates'], format_exceptions=True)

    def render(self, basename):
        values = {'h': helpers, 'c': self}
        self.response.out.write(
            getattr(BaseHandler.renderer_, basename).render_unicode(**values))


class IndexHandler(BaseHandler):
    PAGE_SIZE = 20

    def get(self):
        self.page = int(self.request.get('page', 1))
        cursor = self.request.get('cursor', None)
        self.games_query = models.SteamGame.all().order('-pickled_price_change_list_date')

        offset = 0
        if cursor:
            self.games_query.with_cursor(cursor)
        else:
            offset = (self.page - 1) * IndexHandler.PAGE_SIZE
        self.games = self.games_query.fetch(IndexHandler.PAGE_SIZE, offset=offset)

        self.render('index')


class GameHandler(BaseHandler):
    @staticmethod
    def format_datetime(dt):
        timestamp = time.mktime(dt.timetuple())
        time_str = dt.strftime('%Y/%m/%d')
        time_ago = relative_dates.getRelativeTime(timestamp)
        return time_str, time_ago

    def get(self, steam_id):
        self.game_model = models.SteamGame.get_by_key_name(models.SteamGame.get_key_name(steam_id))
        if not self.game_model:
            self.abort(404)  # could not find game
        self.game = self.game_model.to_steam_api()

        self.render('game')


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
            game_key_name = models.SteamGame.get_key_name(game.id)

            game_model = models.SteamGame.get_by_key_name(game_key_name)
            if not game_model:
                game_model = models.SteamGame(key_name=game_key_name)

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
