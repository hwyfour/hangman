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
    """User profile"""

    '''
    win_percentage: the win percentage comparing this user's wins to all their other games
    average_misses: the average number of misses for all games belonging to this user
    '''
    name = ndb.StringProperty(required = True)
    email = ndb.StringProperty()
    win_percentage = ndb.FloatProperty(default = 0.0)
    average_misses = ndb.FloatProperty(default = 0.0)

    def update_stats(self):
        """Updates win_percentage and average_misses."""

        # Retrieve all games that belong to this user
        games = Game.query(ancestor = self.key).fetch()

        wins = 0
        misses = 0
        num_games = len(games)

        if num_games < 1:
            return

        # Tally up the number of wins and missed guesses
        for game in games:
            wins += 1 if game.won else 0
            misses += game.attempts_allowed - game.attempts_remaining

        # Calculate the new statistics
        self.win_percentage = (float(wins) / float(num_games)) * 100
        self.average_misses = float(misses) / float(num_games)

        self.put()

    def to_form(self):
        """Returns a UserForm representation of the User."""

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


# Definitions for the Game ====================================================================== #

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
    guesses = ndb.IntegerProperty(required = True)
    letters_missed = ndb.StringProperty(required = True)
    game_over = ndb.BooleanProperty(required = True, default = False)
    cancelled = ndb.BooleanProperty(required = True, default = False)
    won = ndb.BooleanProperty(required = True, default = False)
    user = ndb.KeyProperty(required = True, kind = 'User')

    @classmethod
    def new_game(cls, user, attempts = 6):
        """Creates and returns a new Game."""

        # Get a random word from our dictionary, brought to you by our imported words.py
        word = get_word()

        # Create the game, assigning all blanks to the public_word
        game = Game()
        game.private_word = word
        game.public_word = '_' * len(word)
        game.attempts_allowed = attempts
        game.attempts_remaining = attempts
        game.guesses = 0
        game.letters_missed = ''
        game.game_over = False
        game.cancelled = False
        game.won = False
        game.user = user

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
        form.guesses = self.guesses
        form.game_over = self.game_over
        form.cancelled = self.cancelled
        form.won = self.won
        form.message = message

        return form

    def cancel_game(self):
        """Cancels the Game."""

        self.cancelled = True
        self.put()

    def end_game(self, won = False):
        """Ends the Game. Accepts a boolean parameter to mark a win or loss."""

        self.game_over = True
        self.won = won
        self.put()

        # A score is simply the number of misses by the user, lower is better
        score = Score()
        score.user = self.user
        score.date = date.today()
        score.won = won
        score.misses = self.attempts_allowed - self.attempts_remaining

        # Add the game to the score 'board'
        score.put()


class GameForm(messages.Message):
    """Form for outbound Game information"""

    urlsafe_key = messages.StringField(1, required = True)
    user_name = messages.StringField(2, required = True)
    public_word = messages.StringField(3, required = True)
    letters_missed = messages.StringField(4, required = True)
    attempts_remaining = messages.IntegerField(5, required = True)
    guesses = messages.IntegerField(6, required = True)
    game_over = messages.BooleanField(7, required = True)
    cancelled = messages.BooleanField(8, required = True)
    won = messages.BooleanField(9, required = True)
    message = messages.StringField(10, required = True)


class GameForms(messages.Message):
    """Return multiple GameForms"""

    items = messages.MessageField(GameForm, 1, repeated = True)


class NewGameForm(messages.Message):
    """Form to create a new Game"""

    user_name = messages.StringField(1, required = True)
    attempts = messages.IntegerField(2, default = 6)


class MakeMoveForm(messages.Message):
    """Form to make a move in an existing Game"""

    guess = messages.StringField(1, required = True)


# Definitions for the Score ===================================================================== #

class Score(ndb.Model):
    """Score object"""

    user = ndb.KeyProperty(required = True, kind = 'User')
    date = ndb.DateProperty(required = True)
    won = ndb.BooleanProperty(required = True)
    misses = ndb.IntegerProperty(required = True)

    def to_form(self):
        """Returns a ScoreForm representation of the Score."""

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
