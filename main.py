#!/usr/bin/env python

"""
main.py

This file contains handlers that are called by taskqueue and/or cronjobs.
"""

import logging
import webapp2

from api import GuessANumberApi
from google.appengine.api import mail, app_identity
from models import User


class SendReminderEmail(webapp2.RequestHandler):

    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""

        app_id = app_identity.get_application_id()
        users = User.query(User.email != None)
        address = 'noreply@{}.appspotmail.com'.format(app_id)
        subject = 'This is a reminder!'

        for user in users:
            body = 'Hello {}, try out Guess A Number!'.format(user.name)
            # This will send test emails, the arguments to send_mail are:
            # from, to, subject, body
            mail.send_mail(address, user.email, subject, body)


class UpdateAverageMovesRemaining(webapp2.RequestHandler):

    def post(self):
        """Update game listing announcement in memcache."""

        GuessANumberApi._cache_average_attempts()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_attempts', UpdateAverageMovesRemaining),
], debug = True)
