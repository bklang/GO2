"""

 poll class for Gig-o-Matic 2 

 Aaron Oppenheimer
 19 March 2014

"""

from google.appengine.ext import ndb
from requestmodel import *
import webapp2_extras.appengine.auth.models

import webapp2

import member
import band
import plan
import gigcomment
import goemail
import assoc
import jinja2ext
import logging

import datetime
import babel

#
# class for gig
#
class Poll(ndb.Model):
    """ Models a gig-o-matic gig """
    title = ndb.StringProperty()
    details = ndb.TextProperty()
    created_date = ndb.DateProperty( auto_now_add=True )
    enddate = ndb.DateProperty( default=None )
    archive_id = ndb.TextProperty( default=None )
    is_anonymous = ndb.BooleanProperty(default=False )    
    is_archived = ndb.ComputedProperty(lambda self: self.archive_id is not None)    
    comment_id = ndb.TextProperty( default = None)
    creator = ndb.KeyProperty()
#
# Functions to make and find gigs
#

def new_poll(the_band, title, creator, enddate=None, details=""):
    """ Make and return a new poll """
    the_poll = Poll(parent=the_band.key, title=title, details=details, enddate=enddate, creator=creator)
    the_poll.put()
    return the_poll
                
def get_polls_for_band_keys(the_band_key_list, num=None, keys_only=False):
    """ Return poll objects by band, ignoring archived polls """
        
    if (type(the_band_key_list) is not list):
        the_band_key_list = [the_band_key_list]

    all_polls = []
    for a_band_key in the_band_key_list:
        poll_query = Poll.query(Poll.is_archived==False, ancestor=a_band_key).order(Poll.created_date)

        the_polls = poll_query.fetch()
        all_polls.append(the_polls)
        
    # now we have several lists of polls - merge them
    if len(all_polls) == 0:
        return None
    elif len(all_polls) == 1:
        if num is None:
            return all_polls[0]
        else:
            return all_polls[:num]
    else:
        # merge the polls
        sorted_polls = []
        list1 = all_polls.pop()    
        while all_polls:
            list2 = all_polls.pop()    
            while (list1 and list2):
                if (list1[0].created_date <= list2[0].created_date): # Compare both heads
                    item = list1.pop(0) # Pop from the head
                    sorted_polls.append(item)
                else:
                    item = list2.pop(0)
                    sorted_polls.append(item)

            # Add the remaining of the lists
            sorted_polls.extend(list1 if list1 else list2)
            # now prepare to loop back
            list1 = sorted_polls
            sorted_polls = []

    sorted_polls = list1

    if num is None:
        return list1
    else:
        return list1[:num]

def get_polls_for_member_for_dates(the_member):
    """ return poll objects for the bands of a member """
    the_bands = assoc.get_confirmed_bands_of_member(the_member)

    all_polls = []
    if len(the_bands) > 0:
        for a_band in the_bands:
            all_polls.extend(get_polls_for_band_keys(a_band.key))
    return all_polls
                
def make_archive_for_poll_key(the_poll_key):
    """ makes an archive for a poll - files away all the plans, then delete them """
    pass # todo do this!
#     archive_id = gigarchive.make_archive_for_gig_key(the_gig_key)
#     if archive_id:
#         the_gig = the_gig_key.get()
#         if the_gig.archive_id:
#             gigarchive.delete_archive(the_gig.archive_id)
#         the_gig.archive_id = archive_id
#         the_gig.put()
# 
#         # also delete any plans, since they're all now in the archive
#         plan.delete_plans_for_gig_key(the_gig_key)

#
#
# Handlers
#
#

class InfoPage(BaseHandler):
    """ class to serve the poll info page """

    @user_required
    def get(self):    
        self._make_page(self.user)

    def _make_page(self, the_user):

        # find the poll we're interested in
        poll_key_str = self.request.get("pk", None)
        if poll_key_str is None:
            self.response.write('no poll key passed in!')
            return # todo figure out what to do if there's no ID passed in

        poll_key = ndb.Key(urlsafe=poll_key_str)
        the_poll = poll_key.get()

        if the_poll is None:
            template_args = {}
            self.render_template('no_poll_found.html', template_args)
            return # todo figure out what to do if we didn't find it

        the_comment_text = None
        if the_poll.comment_id:
            the_comment_text = gigcomment.get_comment(the_poll.comment_id)
            
        if not the_poll.is_archived:
            the_band_key = the_poll.key.parent()

            the_assocs = assoc.get_assocs_of_band_key(the_band_key, confirmed_only=True, keys_only=False)

            the_plans = []
        
            for the_assoc in the_assocs:
                # if this is an anonymous poll, only get the info for the member
                a_member_key = the_assoc.member
                the_plan = plan.get_plan_for_member_key_for_gig_key(a_member_key, poll_key)
                info_block={}
                info_block['the_poll_key'] = the_poll.key
                info_block['the_plan_key'] = the_plan.key
                info_block['the_member_key'] = a_member_key
                info_block['the_band_key'] = the_band_key
                info_block['the_assoc'] = the_assoc
                the_plans.append(info_block)          
        
            # is the current user a band admin?
            user_is_band_admin = assoc.get_admin_status_for_member_for_band_key(the_user, the_band_key)

            user_can_edit = False
            if user_is_band_admin or the_user.is_superuser:
                user_can_edit = True

            datestr = member.format_date_for_member(the_user, the_poll.created_date, format="long")

            template_args = {
                'poll' : the_poll,
                'date_str' : datestr,
                'the_plans' : the_plans,
                'comment_text' : the_comment_text,
                'user_is_band_admin' : user_is_band_admin,
                'user_can_edit' : user_can_edit
            }
            self.render_template('poll_info.html', template_args)

        else:
            # this is an archived poll
            the_archived_plans = gigarchive.get_archived_plans(the_poll.archive_id)
            template_args = {
                'poll' : the_poll,
                'archived_plans' : the_archived_plans,
                'comment_text' : the_comment_text
            }
            self.render_template('poll_archived_info.html', template_args)
            
class EditPage(BaseHandler):
    """ A class for rendering the poll edit page """

    @user_required
    def get(self):
        self._make_page(self.user)

    def _make_page(self, the_user):

        if self.request.get("new", None) is not None:
            the_poll = None
            is_new = True
            
            the_band_keyurl = self.request.get("bk", None)
            if the_band_keyurl is None:
                return # figure out what to do
            else:
                the_band = ndb.Key(urlsafe = the_band_keyurl).get()
        else:
            the_poll_key = self.request.get("pk", None)
            if (the_poll_key is None):
                return # figure out what to do
                
            the_poll = ndb.Key(urlsafe=the_poll_key).get()
            if the_poll is None:
                self.response.write('did not find a band or poll!')
                return # todo figure out what to do if we didn't find it
            is_new = False
            the_band = the_poll.key.parent().get()

        # are we authorized to edit a poll for this band?
        ok_band_list = self.user.get_add_gig_band_list(self, self.user.key)
        if not the_band.key in [x.key for x in ok_band_list]:
            logging.error(u'user {0} trying to edit a poll for band {1}'.format(self.user.key.urlsafe(),the_band.key.urlsafe()))
            return self.redirect('/agenda.html')            

        if is_new:
            user_is_band_admin = False
        else:
            user_is_band_admin = assoc.get_admin_status_for_member_for_band_key(the_user, the_poll.key.parent())
            
        template_args = {
            'poll' : the_poll,
            'the_band' : the_band,
            'user_is_band_admin': user_is_band_admin,
            'newpoll_is_active' : is_new,
            'the_date_formatter' : member.format_date_for_member
        }
        self.render_template('poll_edit.html', template_args)
        
    @user_required        
    def post(self):
        """post handler - if we are edited by the template, handle it here 
           and redirect back to info page"""


        the_poll_key = self.request.get("pk", '0')
        
        if (the_poll_key == '0'):
            the_poll = None
        else:
            the_poll = ndb.Key(urlsafe=the_poll_key).get()

        # first, get the band
        poll_is_new = False
        poll_band_keyurl = self.request.get("poll_band", None)
        if poll_band_keyurl is not None and poll_band_keyurl != '':
            the_band = ndb.Key(urlsafe=poll_band_keyurl).get()
            if the_poll is None:
                the_poll = new_poll(title="tmp", the_band=the_band, creator=self.user.key)
                poll_is_new = True

        # are we authorized to edit a poll for this band?
        ok_band_list = self.user.get_add_gig_band_list(self, self.user.key)
        if not the_band.key in [x.key for x in ok_band_list]:
            logging.error(u'user {0} trying to edit a poll for band {1}'.format(self.user.key.urlsafe(),the_band.key.urlsafe()))
            return self.redirect('/agenda.html')            

        # now get the info
        poll_title = self.request.get("poll_title", None)
        if poll_title is not None and poll_title != '':
            the_poll.title = poll_title
        
        poll_details = self.request.get("poll_details", None)
        if poll_details is not None:
            the_poll.details = poll_details

        poll_enddate = self.request.get("poll_enddate", None)
        if poll_enddate is not None and poll_enddate != '':
            the_poll.enddate = babel.dates.parse_date(poll_enddate,locale=self.user.preferences.locale)
        else:
            the_poll.enddate = None

        poll_anonymous=self.request.get("poll_anonymous",None)
        if (poll_anonymous):
            the_poll.is_anonymous = True
        else:
            the_poll.is_anonymous = False

        the_poll.put()            

        poll_notify = self.request.get("poll_notifymembers", None)

#         if poll_is_new and poll_notify is not None:
#             goemail.announce_new_poll(the_poll, self.uri_for('poll_info', _full=True, pk=the_poll.key.urlsafe()))

        return self.redirect(\
            '/poll_info.html?&pk={0}'.format(the_poll.key.urlsafe()))
                
class DeleteHandler(BaseHandler):
    def get(self):

        user = self.user
        
        if user is None:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            the_poll_key = self.request.get("pk", None)

            if the_poll_key is None:
                self.response.write('did not find poll!')
            else:
                the_poll = ndb.Key(urlsafe=the_poll_key).get()
                if the_poll.is_archived:
                    gigarchive.delete_archive(the_poll.archive_id)
                if the_poll.comment_id:
                    gigcomment.delete_comment(the_poll.comment_id)
                plan.delete_plans_for_gig_key(the_poll.key)
                the_poll.key.delete()
            return self.redirect('/agenda.html')
            

class ArchiveHandler(BaseHandler):
    """ archive this poll, baby! """
            
    @user_required
    def get(self):

        # find the poll we're interested in
        poll_key_str = self.request.get("pk", None)
        if poll_key_str is None:
            self.response.write('no poll key passed in!')
            return # todo figure out what to do if there's no ID passed in
            
        the_poll_key=ndb.Key(urlsafe=poll_key_str)
        if the_poll_key:
            make_archive_for_poll_key(the_poll_key)

        return self.redirect('/poll_info.html?pk={0}'.format(poll_key_str))
        
class AutoArchiveHandler(BaseHandler):
    """ automatically archive old polls """
    def get(self):
        date = datetime.datetime.now()
        end_date = date - datetime.timedelta(days=3)
        the_poll_keys = get_old_poll_keys(end_date = end_date)
        for a_poll_key in the_poll_keys:
            make_archive_for_poll_key(a_poll_key)
#         if len(the_poll_keys) > 0:
        logging.info("Archived {0} polls".format(len(the_poll_keys)))
        
class CommentHandler(BaseHandler):
    """ takes a new comment and adds it to the poll """

    @user_required
    def post(self):
        poll_key_str = self.request.get("pk", None)
        if poll_key_str is None:
            return # todo figure out what to do if there's no ID passed in

        the_poll_key = ndb.Key(urlsafe=poll_key_str)
        the_poll = the_poll_key.get()

        comment_str = self.request.get("c", None)
        if comment_str is None or comment_str=='':
            return
        
        dt=datetime.datetime.now()

        offset_str = self.request.get("o", None)
        if comment_str is not None:
            offset=int(offset_str)
            dt = dt - datetime.timedelta(hours=offset)

        user=self.user
        timestr=dt.strftime('%-m/%-d/%Y %I:%M%p')
        new_comment = u'{0} ({1}) said at {2}:\n{3}'.format(user.name, user.email_address, timestr, comment_str)

        new_id, the_comment_text = gigcomment.add_comment_for_gig(new_comment, the_poll.comment_id)
        if new_id != the_poll.comment_id:
            the_poll.comment_id = new_id
            the_poll.put()

        self.response.write(jinja2ext.html_content(the_comment_text))

class GetCommentHandler(BaseHandler):
    """ returns the comment for a poll if there is one """
    
    @user_required
    def post(self):
    
        poll_key_str = self.request.get("pk", None)
        if poll_key_str is None:
            return # todo figure out what to do if there's no ID passed in
        the_poll = ndb.Key(urlsafe=poll_key_str).get()

        if the_poll.comment_id:
            the_comment = gigcomment.get_comment(the_poll.comment_id)
            self.response.write(jinja2ext.html_content(the_comment))
        else:
            self.response.write('')
