import time
from google.appengine.ext import db
import SteamApi

class SteamGame(db.Model):
    '''
    Simple model that stores all that we care about for a given steam game.
    '''
    name = db.StringProperty()
    steam_id = db.StringProperty()
    pickled_price_change_list_date = db.ListProperty(long)
    pickled_price_change_list_price = db.ListProperty(float)

    last_updated_on = db.DateTimeProperty(auto_now=True)
    created_on = db.DateTimeProperty(auto_now_add=True)

    @property
    def last_updated_on_timestamp(self):
        return time.mktime(self.last_updated_on.timetuple())

    @property
    def created_on_timestamp(self):
        return time.mktime(self.created_on.timetuple())

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

    @property
    def last_changed(self):
        if len(self.pickled_price_change_list_date):
            return self.pickled_price_change_list_date[0]
        else:
            return None

    @property
    def price_change_list(self):
        return zip(self.pickled_price_change_list_date, self.pickled_price_change_list_price)

    @staticmethod
    def get_key_name(game_id):
        return str(game_id)

    def to_steam_api(self):
        return SteamApi.Game(
            id=self.steam_id, name=self.name, price=self.current_price)
