#!/usr/bin/env python

"""
models.py

Contains the class definitions for the Datastore entities used by the Game.
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

    '''
    private_word: the word assigned for this game eg. 'boat'
    public_word: the player's current knowledge of the word eg. '__at'
    letters_missed: a string containing all the letters the player has guessed incorrectly
    '''
    private_word = ndb.StringProperty(required = True)
    public_word = ndb.StringProperty(required = True)
    attempts_allowed = ndb.IntegerProperty(required = True)
    attempts_remaining = ndb.IntegerProperty(required = True)
    letters_missed = ndb.StringProperty(required = True)
    game_over = ndb.BooleanProperty(required = True, default = False)
    cancelled = ndb.BooleanProperty(required = True, default = False)
    user = ndb.KeyProperty(required = True, kind = 'User')

    @classmethod
    def new_game(cls, user, attempts = 6):
        """Creates and returns a new Game."""

        # Get a random word from our dictionary, brought to you by our imported words.py
        word = get_word()

        # Create the game, assigning all blanks to the public_word
        game = Game(user = user,
            private_word = word,
            public_word = '_' * len(word),
            attempts_allowed = attempts,
            attempts_remaining = attempts,
            letters_missed = '')

        # Get a unique id for this game
        game_id = Game.allocate_ids(size = 1, parent = user)[0]
        # So we can link this game as a descendant to this user for easy querying
        game.key = ndb.Key(Game, game_id, parent = user)
        # Store the new game
        game.put()

        return game

    def to_form(self, message = ''):
        """Returns a GameForm representation of the Game."""

        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.public_word = self.public_word
        form.letters_missed = self.letters_missed
        form.attempts_remaining = self.attempts_remaining
        form.game_over = self.game_over
        form.cancelled = self.cancelled
        form.message = message

        return form

    def cancel_game(self):
        """Cancels the game."""

        self.cancelled = True
        self.put()

    def end_game(self, won = False):
        """Ends the game - if won is True, the player won. - if won is False, the player lost."""

        self.game_over = True
        self.put()

        # A score is simply the number of guesses remaining
        score = Score(user = self.user,
            date = date.today(),
            won = won,
            attempts_remaining = self.attempts_remaining)

        # Add the game to the score 'board'
        score.put()


class GameForm(messages.Message):
    """Form for outbound Game information"""

    urlsafe_key = messages.StringField(1, required = True)
    user_name = messages.StringField(2, required = True)
    public_word = messages.StringField(3, required = True)
    letters_missed = messages.StringField(4, required = True)
    attempts_remaining = messages.IntegerField(5, required = True)
    game_over = messages.BooleanField(6, required = True)
    cancelled = messages.BooleanField(7, required = True)
    message = messages.StringField(8, required = True)


class GameForms(messages.Message):
    """Return multiple GameForms"""

    items = messages.MessageField(GameForm, 1, repeated = True)


class NewGameForm(messages.Message):
    """Form to create a new game"""

    user_name = messages.StringField(1, required = True)
    attempts = messages.IntegerField(2, default = 6)


class MakeMoveForm(messages.Message):
    """Form to make a move in an existing game"""

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
    """Form for outbound Score information"""

    user_name = messages.StringField(1, required = True)
    date = messages.StringField(2, required = True)
    won = messages.BooleanField(3, required = True)
    attempts_remaining = messages.IntegerField(4, required = True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""

    items = messages.MessageField(ScoreForm, 1, repeated = True)


class StringMessage(messages.Message):
    """A single outbound string message"""

    message = messages.StringField(1, required = True)
