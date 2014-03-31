#
#  caldav server class for Gig-o-Matic 2 
#
# Aaron Oppenheimer
# 29 March 2014
#
from google.appengine.ext import ndb
from requestmodel import *
import webapp2_extras.appengine.auth.models

import webapp2
import logging

import gig
import datetime
from pytz.gae import pytz

def make_cal_header(the_band):
    header="""BEGIN:VCALENDAR
PRODID:-//Gig-o-Matic//Gig-o-Matic 2//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:{0}
X-WR-CALDESC:{2}
"""

# X-WR-TIMEZONE:{1}

    return header.format(the_band.name,'',"Gig-o-Matic calendar for {0}".format(the_band.name))

def make_cal_footer():
    return "END:VCALENDAR\n"

def make_event(the_gig, the_band):
# 
#     event="""BEGIN:VEVENT
# DTSTART:{1}
# DTEND:{2}
# DTSTAMP:20140329T155645Z
# UID:3jba27qkcfjmf9elvfs909fgdk@google.com
# CREATED:20140329T154445Z
# DESCRIPTION:
# LAST-MODIFIED:20140329T154445Z
# LOCATION:
# SEQUENCE:0
# STATUS:CONFIRMED
# SUMMARY:{0}
# TRANSP:OPAQUE
# END:VEVENT
# """

    summary = the_gig.title

    if the_band.timezone:
        tzoffset = datetime.datetime.now(pytz.timezone(the_band.timezone)).dst()
        
    print '\n\n tzoffset={0}\n\n'.format(tzoffset)

    start_date = the_gig.date
    if the_gig.enddate:
        end_date = the_gig.enddate
    else:
        end_date = start_date
        
    if tzoffset:
        start_date = start_date - tzoffset
        end_date = end_date - tzoffset

    dtstart = start_date.strftime("%Y%m%d")
    dtend = end_date.strftime("%Y%m%d")    

    starthour = -1
    endhour = -1
    
    if the_gig.calltime_dt:
        call_time = the_gig.calltime_dt
        if tzoffset:
            call_time = call_time - tzoffset
        starthour = call_time.hour
        startmin = call_time.minute

    elif the_gig.settime_dt: # only use the set time if there's no call time
        starthour = the_gig.settime_dt.hour
        startmin = the_gig.settime_dt.minute

    et = None
    if the_gig.endtime_dt:
        endhour = the_gig.endtime_dt.hour
        endmin = the_gig.endtime_dt.minute
    elif starthour >= 0:
            endhour = starthour + 1
            endmin = startmin

    if starthour >= 0:
        dtstart = '{0}T{1:02d}{2:02d}00Z'.format(dtstart,starthour,startmin)
    if endhour >= 0:
        dtend = '{0}T{1:02d}{2:02d}00Z'.format(dtend,endhour,endmin)

    the_url = 'http://gig-o-matic.appspot.com/gig_info.html?gk={0}'.format(the_gig.key.urlsafe())

    event="""BEGIN:VEVENT
DTSTART:{1}
DTEND:{2}
DESCRIPTION:{3}
LOCATION: {4}
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:{0}
TRANSP:OPAQUE
URL:{5}
END:VEVENT
"""
    event=event.format(summary, dtstart, dtend, the_gig.details, the_gig.address, the_url)
    return event

#####
#
# Page Handlers
#
#####

class RequestHandler(BaseHandler):
    """Handle a CalDav request"""

    def get(self, *args, **kwargs):
        print 'got get request'

        bk = kwargs['bk']
            
        the_band_key = ndb.Key(urlsafe=bk);
        the_band = the_band_key.get()

        info = '{0}'.format(make_cal_header(the_band))

        all_gigs = gig.get_gigs_for_band_keys(the_band_key)
        for a_gig in all_gigs:
            if a_gig.is_confirmed:
                info = '{0}{1}'.format(info, make_event(a_gig, the_band))

        info = '{0}{1}'.format(info, make_cal_footer())
        self.response.write(info)
            
    def post(self):    
        print 'got post request'
            
