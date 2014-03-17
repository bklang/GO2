#
#  email_throttle class for Gig-o-Matic 2 
#
# Aaron Oppenheimer
# 10 March 2014
#
from google.appengine.ext import ndb
from requestmodel import *
import webapp2_extras.appengine.auth.models
from google.appengine.api import mail

import webapp2
from debug import *
import datetime
import logging


def email_stats_key(member_name='email_stats_key'):
    """Constructs a Datastore key for a Stats entity with stats_name."""
    return ndb.Key('email_stats', stats_name)

class EmailStats(ndb.Model):
    """ class to hold statistics """
    band = ndb.KeyProperty()
    date = ndb.DateProperty(auto_now_add=True)
    number_emails = ndb.IntegerProperty()
    
def get_band_email_stats(the_band_key, the_date):
    """ Return all the stats we have for a band """
    if the_date:
        stats_query = EmailStats.query( EmailStats.band==the_band_key, EmailStats.date==the_date).order(EmailStats.date)
    else:
        stats_query = EmailStats.query( EmailStats.band==the_band_key).order(EmailStats.date)
    the_stats = stats_query.fetch()
    return the_stats
    
def delete_band_email_stats(the_band_key):
    """ delete all email stats for a band """
    stats_query = EmailStats.query( EmailStats.band==the_band_key)
    the_stats = stats_query.fetch(keys_only=True)
    ndb.delete_multi(the_stats)

def register_email_sent(the_band_key):
    """ update the stats for this band """
    the_stats = get_band_email_stats(the_band_key=the_band_key, the_date=datetime.date.today())
    if the_stats:
        if len(the_stats) == 1:
            the_stat = the_stats[0]
            the_stat.number_emails = the_stat.number_emails + 1
        else:
            return # todo this is an error
    else:
        the_stat = EmailStats(band=the_band_key, number_emails=1)

    logging.error("set email count to {0}".format(the_stat.number_emails))
    the_stat.put()

def send_email(the_band_key, the_email):
    """ save some stats, then send the email """
    
    register_email_sent(the_band_key)
        
    try:
        the_email.send()
    except:
        logging.error('failed to send email!')
