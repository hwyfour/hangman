#!/usr/bin/env python

"""
models.py

Contains the class definitions for the Datastore entities used by Hangman.
"""

import random

from datetime import date
from google.appengine.ext import ndb
from protorpc import messages

from words import get_word


# Definitions for the User ====================================================================== #

class User(ndb.Model):
    """User object"""

    '''
    win_percentage: The win percentage for all Games belonging to this User
    average_misses: The average number of misses for all Games belonging to this User
    '''
    name = ndb.StringProperty(required = True)
    email = ndb.StringProperty()
    win_percentage = ndb.FloatProperty(default = 0.0)
    average_misses = ndb.FloatProperty(default = 0.0)

    def _get_games(self):
        """Return all Games belonging to this User."""

        return Game.query(ancestor = self.key).fetch()

    def update_stats(self):
        """Update win_percentage and average_misses."""

        games = self._get_games()

        num_games = len(games)

        if num_games < 1:
            return

        wins, misses = 0

        # Tally up the number of wins and misses
        for game in games:
            wins += 1 if game.won else 0
            misses += game.attempts_allowed - game.attempts_remaining

        # Calculate the new statistics
        self.win_percentage = (float(wins) / float(num_games)) * 100
        self.average_misses = float(misses) / float(num_games)

        self.put()

    def get_games(self):
        """Return a collection of all active Games belonging to this User."""

        games = self._get_games()

        game_collection = []

        for game in games:
            # Do not append a Game if it is over or cancelled
            if game.game_over or game.cancelled:
                continue

            game_collection.append(game)

        return game_collection

    def to_form(self):
        """Return a UserForm representation of the User."""

        form = UserForm()
        form.name = self.name
        form.win_percentage = self.win_percentage

        return form


class UserForm(messages.Message):
    """Form for outbound User information"""

    name = messages.StringField(1, required = True)
    win_percentage = messages.FloatField(2, required = True)


class UserForms(messages.Message):
    """Return multiple UserForms"""

    items = messages.MessageField(UserForm, 1, repeated = True)


# Definitions for the Guess ===================================================================== #

class GuessForm(messages.Message):
    """Form for outbound Guess information"""

    guess = messages.StringField(1, required = True)
    miss = messages.BooleanField(2, required = True)
    message = messages.StringField(3, required = True)
    state = messages.StringField(4, required = True)


class GuessForms(messages.Message):
    """Return multiple GuessForms"""

    items = messages.MessageField(GuessForm, 1, repeated = True)


# Definitions for the Game ====================================================================== #

class Game(ndb.Model):
    """Game object"""

    '''
    private_word: The word assigned for this Game - eg. 'boat'
    public_word: The User's current knowledge of the word - eg. '__at'
    guesses: An array of Guesses to track each Guess the User makes
    misses: A set for tracking unique missed Guesses for easy counting
    '''
    private_word = ndb.StringProperty(required = True)
    public_word = ndb.StringProperty(required = True)
    attempts_allowed = ndb.IntegerProperty(required = True)
    attempts_remaining = ndb.IntegerProperty(required = True)
    guesses = ndb.PickleProperty(required = True)
    misses = ndb.PickleProperty()
    game_over = ndb.BooleanProperty(required = True, default = False)
    cancelled = ndb.BooleanProperty(required = True, default = False)
    won = ndb.BooleanProperty(required = True, default = False)
    user = ndb.KeyProperty(required = True, kind = 'User')

    @classmethod
    def new_game(cls, user, attempts = 6):
        """Create a new Game."""

        # Get a random word from our dictionary, brought to you by our imported words.py
        word = get_word()

        # Create the Game, assigning all blanks to the public_word
        game = Game()
        game.private_word = word
        game.public_word = '_' * len(word)
        game.attempts_allowed = attempts
        game.attempts_remaining = attempts
        game.guesses = []
        game.misses = set()
        game.game_over = False
        game.cancelled = False
        game.won = False
        game.user = user

        # Get a unique id for this game
        game_id = Game.allocate_ids(size = 1, parent = user)[0]
        # So we can link this Game as a descendant to this User for easy querying
        game.key = ndb.Key(Game, game_id, parent = user)
        # Store the new Game
        game.put()

        return game

    def guess(self, guess = ''):
        """Make a move with the provided Guess."""

        guess_obj = {
            'guess': guess,
            'miss': False,
            'message': 'You made a guess',
            'state': 'Okay I guess'
        }

        self.guesses.append(guess_obj)
        self.put()

        return guess_obj['message']

    def cancel_game(self):
        """Cancel the Game."""

        self.cancelled = True
        self.put()

    def end_game(self, won = False):
        """End the Game. Accepts a boolean parameter to mark a win or loss."""

        self.game_over = True
        self.won = won
        self.put()

        # A Score is simply the number of misses by the User. Lower is better
        score = Score()
        score.user = self.user
        score.date = date.today()
        score.won = won
        score.misses = self.attempts_allowed - self.attempts_remaining

        # Add the Game to the scoreboard
        score.put()

    def to_form(self, message = ''):
        """Return a GameForm representation of the Game."""

        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.public_word = self.public_word
        form.attempts_remaining = self.attempts_remaining
        form.guesses = self.guesses
        form.game_over = self.game_over
        form.cancelled = self.cancelled
        form.won = self.won
        form.message = message

        return form


class GameForm(messages.Message):
    """Form for outbound Game information"""

    urlsafe_key = messages.StringField(1, required = True)
    user_name = messages.StringField(2, required = True)
    public_word = messages.StringField(3, required = True)
    attempts_remaining = messages.IntegerField(4, required = True)
    guesses = messages.MessageField(GuessForm, 5, repeated = True)
    game_over = messages.BooleanField(6, required = True)
    cancelled = messages.BooleanField(7, required = True)
    won = messages.BooleanField(8, required = True)
    message = messages.StringField(9, required = True)


class GameForms(messages.Message):
    """Return multiple GameForms"""

    items = messages.MessageField(GameForm, 1, repeated = True)


class NewGameForm(messages.Message):
    """Form to create a new Game"""

    user_name = messages.StringField(1, required = True)
    attempts = messages.IntegerField(2, default = 6)


class MakeMoveForm(messages.Message):
    """Form to register a Guess in an existing Game"""

    guess = messages.StringField(1, required = True)


# Definitions for the Score ===================================================================== #

class Score(ndb.Model):
    """Score object"""

    user = ndb.KeyProperty(required = True, kind = 'User')
    date = ndb.DateProperty(required = True)
    won = ndb.BooleanProperty(required = True)
    misses = ndb.IntegerProperty(required = True)

    def to_form(self):
        """Return a ScoreForm representation of the Score."""

        form = ScoreForm()
        form.user_name = self.user.get().name
        form.date = str(self.date)
        form.won = self.won
        form.misses = self.misses

        return form


class ScoreForm(messages.Message):
    """Form for outbound Score information"""

    user_name = messages.StringField(1, required = True)
    date = messages.StringField(2, required = True)
    won = messages.BooleanField(3, required = True)
    misses = messages.IntegerField(4, required = True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""

    items = messages.MessageField(ScoreForm, 1, repeated = True)


# Miscellaneous Definitions ===================================================================== #

class StringMessage(messages.Message):
    """A single outbound StringMessage"""

    message = messages.StringField(1, required = True)
