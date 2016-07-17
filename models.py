#!/usr/bin/env python

"""
models.py

This file contains the class definitions for the Datastore entities used by the Game.
Because these classes are also regular Python classes, they can include methods
(such as 'to_form' and 'new_game').
"""

import random

from datetime import date
from google.appengine.ext import ndb
from protorpc import messages

from words import get_word


class User(ndb.Model):
    """User profile"""

    name = ndb.StringProperty(required = True)
    email = ndb.StringProperty()


class Game(ndb.Model):
    """Game object"""

    private_word = ndb.StringProperty(required = True)
    public_word = ndb.StringProperty(required = True)
    attempts_allowed = ndb.IntegerProperty(required = True)
    attempts_remaining = ndb.IntegerProperty(required = True, default = 6)
    letters_missed = ndb.StringProperty(required = True)
    game_over = ndb.BooleanProperty(required = True, default = False)
    user = ndb.KeyProperty(required = True, kind = 'User')

    @classmethod
    def new_game(cls, user, attempts):
        """Creates and returns a new game."""

        word = get_word()

        game = Game(user = user,
            private_word = word,
            public_word = '_' * len(word),
            attempts_allowed = attempts,
            attempts_remaining = attempts,
            letters_missed = '',
            game_over = False)

        game_id = Game.allocate_ids(size = 1, parent = user)[0]
        game.key = ndb.Key(Game, game_id, parent = user)

        game.put()

        return game

    def to_form(self, message=''):
        """Returns a GameForm representation of the Game."""

        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.public_word = self.public_word
        form.letters_missed = self.letters_missed
        form.attempts_remaining = self.attempts_remaining
        form.game_over = self.game_over
        form.message = message

        return form

    def end_game(self, won = False):
        """Ends the game - if won is True, the player won. - if won is False, the player lost."""

        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user = self.user,
            date = date.today(),
            won = won,
            attempts_remaining = self.attempts_remaining)
        score.put()


class GameForm(messages.Message):
    """GameForm for outbound game state information"""

    urlsafe_key = messages.StringField(1, required = True)
    user_name = messages.StringField(2, required = True)
    public_word = messages.StringField(3, required = True)
    letters_missed = messages.StringField(4, required = True)
    attempts_remaining = messages.IntegerField(5, required = True)
    game_over = messages.BooleanField(6, required = True)
    message = messages.StringField(7, required = True)


class GameForms(messages.Message):
    """Return multiple GameForms"""

    items = messages.MessageField(GameForm, 1, repeated = True)


class NewGameForm(messages.Message):
    """Used to create a new game"""

    user_name = messages.StringField(1, required = True)
    attempts = messages.IntegerField(2, default = 6)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""

    guess = messages.StringField(1, required = True)


class Score(ndb.Model):
    """Score object"""

    user = ndb.KeyProperty(required = True, kind = 'User')
    date = ndb.DateProperty(required = True)
    won = ndb.BooleanProperty(required = True)
    attempts_remaining = ndb.IntegerProperty(required = True)

    def to_form(self):
        return ScoreForm(
            user_name = self.user.get().name,
            won = self.won,
            date = str(self.date),
            attempts_remaining = self.attempts_remaining)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""

    user_name = messages.StringField(1, required = True)
    date = messages.StringField(2, required = True)
    won = messages.BooleanField(3, required = True)
    attempts_remaining = messages.IntegerField(4, required = True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""

    items = messages.MessageField(ScoreForm, 1, repeated = True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""

    message = messages.StringField(1, required = True)
