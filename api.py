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

from models import User, UserForms
from models import GuessForm, GuessForms
from models import Game, GameForm, GameForms, NewGameForm, MakeMoveForm
from models import Score, ScoreForms
from models import StringMessage

from utils import get_by_urlsafe


USER_REQUEST = endpoints.ResourceContainer(
    user_name = messages.StringField(1),
    email = messages.StringField(2))

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key = messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key = messages.StringField(1),)

HIGH_SCORES_REQUEST = endpoints.ResourceContainer(
    number_of_results = messages.IntegerField(1),)

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
            """Create a new User. Requires a unique username."""

            user = User.query(User.name == request.user_name).get()

            if user:
                raise endpoints.ConflictException('A User with that name already exists!')

            user = User(name = request.user_name, email = request.email)
            user.put()

            return StringMessage(message = 'User {} created!'.format(request.user_name))


        @endpoints.method(request_message = USER_REQUEST,
            response_message = GameForms,
            path = 'user/{user_name}/games',
            name = 'get_user_games',
            http_method = 'GET')
        def get_user_games(self, request):
            """Return all Games for the given User."""

            user = User.query(User.name == request.user_name).get()

            if not user:
                raise endpoints.NotFoundException('A User with that name does not exist!')

            return user.get_gameforms()


        @endpoints.method(response_message = UserForms,
            path = 'user/rankings',
            name = 'get_user_rankings',
            http_method = 'GET')
        def get_user_rankings(self, request):
            """Return all Users ranked by their win percentage."""

            # Update statistics for all Users
            for user in User.query():
                user.update_stats()

            # Generate the list of ranked Users, ranked from high to low win %
            # Ties broken by the average misses of the tied Users, lower wins
            users = User.query().order(-User.win_percentage, User.average_misses)

            return UserForms(items = [user.to_form() for user in users])


        @endpoints.method(request_message = NEW_GAME_REQUEST,
            response_message = GameForm,
            path = 'game',
            name = 'new_game',
            http_method = 'POST')
        def new_game(self, request):
            """Create a new Game."""

            user = User.query(User.name == request.user_name).get()

            if not user:
                raise endpoints.NotFoundException('A User with that name does not exist!')

            game = Game.new_game(user.key, request.attempts)

            # Use a task queue to update the average attempts remaining.
            # This operation is not needed to complete the creation of a new game
            # so it is performed out of sequence.
            taskqueue.add(url = '/tasks/cache_average_attempts')

            return game.to_form('Game created! Good luck!')


        @endpoints.method(request_message = GET_GAME_REQUEST,
            response_message = GameForm,
            path = 'game/{urlsafe_game_key}',
            name = 'get_game',
            http_method = 'GET')
        def get_game(self, request):
            """Return the Game specified by the provided key."""

            game = get_by_urlsafe(request.urlsafe_game_key, Game)

            if not game:
                raise endpoints.NotFoundException('A Game with that key does not exist!')

            return game.to_form()


        @endpoints.method(request_message = GET_GAME_REQUEST,
            response_message = GameForm,
            path = 'game/{urlsafe_game_key}/cancel',
            name = 'cancel_game',
            http_method = 'PUT')
        def cancel_game(self, request):
            """Cancel the Game specified by the provided key."""

            game = get_by_urlsafe(request.urlsafe_game_key, Game)

            if not game:
                raise endpoints.NotFoundException('A Game with that key does not exist!')

            if game.game_over:
                return game.to_form('This Game is already over!')

            game.cancel_game()

            return game.to_form('This Game is now cancelled!')


        @endpoints.method(request_message = GET_GAME_REQUEST,
            response_message = GuessForms,
            path = 'game/{urlsafe_game_key}/history',
            name = 'get_game_history',
            http_method = 'GET')
        def get_game_history(self, request):
            """Return the history for the Game specified by the provided key."""

            game = get_by_urlsafe(request.urlsafe_game_key, Game)

            if not game:
                raise endpoints.NotFoundException('A Game with that key does not exist!')

            return game.get_guessforms()


        @endpoints.method(request_message = MAKE_MOVE_REQUEST,
            response_message = GameForm,
            path = 'game/{urlsafe_game_key}',
            name = 'make_move',
            http_method = 'PUT')
        def make_move(self, request):
            """Make a move in the Game specified by the provided key."""

            game = get_by_urlsafe(request.urlsafe_game_key, Game)

            if not game:
                raise endpoints.NotFoundException('A Game with that key does not exist!')

            if game.game_over:
                return game.to_form('This Game is already over!')

            message = game.guess(request.guess)

            return game.to_form(message)


        @endpoints.method(response_message = ScoreForms,
            path = 'scores',
            name = 'get_scores',
            http_method = 'GET')
        def get_scores(self, request):
            """Return all Scores."""

            return ScoreForms(items = [score.to_form() for score in Score.query()])


        @endpoints.method(request_message = HIGH_SCORES_REQUEST,
            response_message = ScoreForms,
            path = 'scores/high',
            name = 'get_high_scores',
            http_method = 'GET')
        def get_high_scores(self, request):
            """Return ranked Scores. Low is better. Limit of 5 or set by the provided value."""

            scores = Score.query().order(Score.misses).fetch(request.number_of_results or 5)

            return ScoreForms(items = [score.to_form() for score in scores])


        @endpoints.method(request_message = USER_REQUEST,
            response_message = ScoreForms,
            path = 'scores/user/{user_name}',
            name = 'get_user_scores',
            http_method = 'GET')
        def get_user_scores(self, request):
            """Return all Scores for the given User."""

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
            """Get the cached average moves remaining."""

            return StringMessage(message = memcache.get(MEMCACHE_MOVES_REMAINING) or '')

        @staticmethod
        def _cache_average_attempts():
            """Populate memcache with the average moves remaining of all Games."""

            games = Game.query(Game.game_over == False).fetch()

            if games:
                count = len(games)
                total_attempts_remaining = sum([game.attempts_remaining for game in games])
                average = float(total_attempts_remaining) / count
                memcache.set(
                    MEMCACHE_MOVES_REMAINING,
                    'The average moves remaining is {:.2f}'.format(average))


api = endpoints.api_server([HangmanAPI])
