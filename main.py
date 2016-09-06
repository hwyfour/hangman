#!/usr/bin/env python

"""
main.py

This file contains handlers that are called by taskqueue and/or cronjobs.
"""

import logging
import webapp2

from api import HangmanAPI
from google.appengine.api import mail, app_identity
from models import User


class SendReminderEmail(webapp2.RequestHandler):

    def get(self):
        """Send a reminder email each hour to each User with active Games using a cron job."""

        app_id = app_identity.get_application_id()
        users = User.query(User.email != None)
        address = 'noreply@{}.appspotmail.com'.format(app_id)
        subject = 'This is a reminder!'

        for user in users:
            # Ignore this User if they have no active Games
            if len(user.get_games()) == 0:
                continue

            body = 'Hello {}, come back and finish your Hangman game!'.format(user.name)
            # This will send emails, the arguments to send_mail are:
            # from, to, subject, body
            mail.send_mail(address, user.email, subject, body)


class UpdateAverageMovesRemaining(webapp2.RequestHandler):

    def post(self):
        """Update game listing announcement in memcache."""

        HangmanAPI._cache_average_attempts()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_attempts', UpdateAverageMovesRemaining),
], debug = True)
