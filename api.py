#!/usr/bin/env python
# -*- coding: utf-8 -*-`

"""
api.py

Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users.
"""

import endpoints
import logging

from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm, ScoreForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key = messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key = messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(
    user_name = messages.StringField(1),
    email = messages.StringField(2))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'


@endpoints.api(name = 'hangman', version = 'v1')
class HangmanAPI(remote.Service):
        """Game API"""

        @endpoints.method(request_message = USER_REQUEST,
            response_message = StringMessage,
            path = 'user',
            name = 'create_user',
            http_method = 'POST')
        def create_user(self, request):
            """Create a User. Requires a unique username"""

            if User.query(User.name == request.user_name).get():
                raise endpoints.ConflictException('A User with that name already exists!')

            user = User(name = request.user_name, email = request.email)
            user.put()

            return StringMessage(message = 'User {} created!'.format(request.user_name))


        @endpoints.method(request_message = NEW_GAME_REQUEST,
            response_message = GameForm,
            path = 'game',
            name = 'new_game',
            http_method = 'POST')
        def new_game(self, request):
            """Creates new game"""

            user = User.query(User.name == request.user_name).get()

            if not user:
                raise endpoints.NotFoundException('A User with that name does not exist!')

            game = Game.new_game(user.key, request.attempts)

            # Use a task queue to update the average attempts remaining.
            # This operation is not needed to complete the creation of a new game
            # so it is performed out of sequence.
            taskqueue.add(url = '/tasks/cache_average_attempts')

            return game.to_form('Good luck playing Hangman!')


        @endpoints.method(request_message = GET_GAME_REQUEST,
            response_message = GameForm,
            path = 'game/{urlsafe_game_key}',
            name = 'get_game',
            http_method = 'GET')
        def get_game(self, request):
            """Return the current game state."""

            game = get_by_urlsafe(request.urlsafe_game_key, Game)

            if game:
                return game.to_form('Time to make a move!')
            else:
                raise endpoints.NotFoundException('Game not found!')


        @endpoints.method(request_message = MAKE_MOVE_REQUEST,
            response_message = GameForm,
            path = 'game/{urlsafe_game_key}',
            name = 'make_move',
            http_method = 'PUT')
        def make_move(self, request):
            """Makes a move. Returns a game state with message"""

            game = get_by_urlsafe(request.urlsafe_game_key, Game)

            if game.game_over:
                return game.to_form('Game already over!')

            guess = request.guess

            # if the guess is more than one character, we're guessing the word
            if len(guess) > 1:
                # if the guess matches the word, we're done!
                if guess == game.private_word:
                    msg = 'You correctly guessed the whole word!'
                    # copy the private word over to replace all characters
                    game.public_word = game.private_word
                else:
                    msg = 'That is not the word!'
                    # there are no letters to record, but we do mark a missed attempt
                    game.attempts_remaining -= 1

            # otherwise we're working with a single character guess
            else:
                # count how many occurences of that character are in the word
                hit_count = game.private_word.count(guess)

                if hit_count > 0:
                    msg = 'That letter is in the word %s times!' % hit_count
                    # replace the spaces in the public word with this character where necessary
                    private_word = game.private_word
                    char_locations = [i for i, ch in enumerate(private_word) if ch == guess]

                    for location in char_locations:
                        pw = game.public_word
                        pw = pw[:location] + guess + pw[location + 1:]
                        game.public_word = pw
                else:
                    msg = 'That letter is not in the word!'
                    # record the letter miss, and add that letter to the miss pile
                    game.attempts_remaining -= 1
                    game.letters_missed = game.letters_missed + guess

            # if we have the full word, we win!
            if game.public_word == game.private_word:
                msg = msg + ' You win!'
                game.end_game(True)
                return game.to_form(msg)

            # if we have no attempts left, the game is over
            if game.attempts_remaining < 1:
                msg = msg + ' Game over!'
                game.end_game(False)
                return game.to_form(msg)

            # or, the game is still on, so save the current state and return that to the player
            game.put()
            return game.to_form(msg)


        @endpoints.method(response_message = ScoreForms,
            path = 'scores',
            name = 'get_scores',
            http_method = 'GET')
        def get_scores(self, request):
            """Return all scores"""

            return ScoreForms(items = [score.to_form() for score in Score.query()])


        @endpoints.method(request_message = USER_REQUEST,
            response_message = ScoreForms,
            path = 'scores/user/{user_name}',
            name = 'get_user_scores',
            http_method = 'GET')
        def get_user_scores(self, request):
            """Returns all of an individual User's scores"""

            user = User.query(User.name == request.user_name).get()

            if not user:
                raise endpoints.NotFoundException('A User with that name does not exist!')

            scores = Score.query(Score.user == user.key)

            return ScoreForms(items = [score.to_form() for score in scores])


        @endpoints.method(response_message = StringMessage,
            path = 'games/average_attempts',
            name = 'get_average_attempts_remaining',
            http_method = 'GET')
        def get_average_attempts(self, request):
            """Get the cached average moves remaining"""

            return StringMessage(message = memcache.get(MEMCACHE_MOVES_REMAINING) or '')

        @staticmethod
        def _cache_average_attempts():
            """Populates memcache with the average moves remaining of Games"""

            games = Game.query(Game.game_over == False).fetch()

            if games:
                count = len(games)
                total_attempts_remaining = sum([game.attempts_remaining for game in games])
                average = float(total_attempts_remaining) / count
                memcache.set(
                    MEMCACHE_MOVES_REMAINING,
                    'The average moves remaining is {:.2f}'.format(average))


api = endpoints.api_server([HangmanAPI])
