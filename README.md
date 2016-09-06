# Hangman

Hangman built on Google App Engine

## Set-Up Instructions

1. Update the value of `application` in app.yaml to the app ID you have registered in the App
Engine admin console and would like to use to host your instance of this sample.
2. Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.

## Game Description

Hangman is a simple guessing game. Each game starts with a random unknown word that the player
must try and guess. Additionally, each game has a set number of attempts before the game ends.
This number of attempts can be set when creating the game to allow for variable difficulty.

Each guess can be either a character or an attempt at the whole word. If the player does not
discover the word within the set number of attempts, the game ends and the player loses.

## Score Keeping

Each time a player wins a game, a score is recorded that contains the number of missed guesses
that the player attempted. A lower number of missed attempts is better and thus constitutes a
better score. When ranking players, the win percentage over all of a player's games is used as the
primary score. In the event of a tie, players are compared by their average number of misses over
all of their played games.

## Files

 - api.py: Contains API endpoints and simple logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including heavy game logic.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.
 - words.py: Helper function for supplying a random word to the new game.

## Endpoints

### create_user

    Path: 'user'
    Method: POST
    Parameters: user_name, email (optional)
    Returns: Message confirming creation of the User.
    Description:
        Creates a new User.
        Will raise a ConflictException if a User with that user_name already exists.

### get_user_games

    Path: 'user/{user_name}/games'
    Method: GET
    Parameters: user_name, email (optional)
    Returns: GameForms containing all active Games for the User.
    Description:
        Returns all active Games for the given User.
        Will raise a NotFoundException if a User with that user_name can't be found.

### get_user_rankings

    Path: 'user/rankings'
    Method: GET
    Parameters: None
    Returns: UserForms containing all Users ranked according to their score as described below.
    Description:
        Returns all Users ranked by their win percentage, descending.
        Ties are settled by average missed guesses, ascending.

### new_game

    Path: 'game'
    Method: POST
    Parameters: user_name, attempts
    Returns: GameForm with initial game state.
    Description:
        Creates a new Game for the given User.
        Will raise a NotFoundException if a User with that user_name can't be found.
        Adds a task to a task queue to update the average guesses remaining for active Games.

### get_game

    Path: 'game/{urlsafe_game_key}'
    Method: GET
    Parameters: urlsafe_game_key
    Returns: GameForm with current game state.
    Description:
        Returns the current state of a Game.
        Will raise a NotFoundException if a Game with that key can't be found.

### cancel_game

    Path: 'game/{urlsafe_game_key}/cancel'
    Method: PUT
    Parameters: urlsafe_game_key
    Returns: GameForm with current game state.
    Description:
        Cancels the Game specified by the provided key.
        Does not cancel Games that are already ended.
        Will raise a NotFoundException if a Game with that key can't be found.

### get_game_history

    Path: 'game/{urlsafe_game_key}/history'
    Method: GET
    Parameters: urlsafe_game_key
    Returns: GuessForms with all Guesses for this Game.
    Description:
        Returns the Guess history for the Game specified by the provided key.
        Will raise a NotFoundException if a Game with that key can't be found.

### make_move

    Path: 'game/{urlsafe_game_key}'
    Method: PUT
    Parameters: urlsafe_game_key, guess
    Returns: GameForm with new game state.
    Description:
        Registers a Guess for the Game specified by the provided key.
        A Guess cannot be registered if the Game is already over.
        Returns the current state of the Game.
        If this Guess causes the Game to end, a Score will be created.
        Will raise a NotFoundException if a Game with that key can't be found.

### get_scores

    Path: 'scores'
    Method: GET
    Parameters: None
    Returns: ScoreForms.
    Description:
        Returns all Scores in the database (unordered).

### get_high_scores

    Path: 'scores/high'
    Method: GET
    Parameters: number_of_results
    Returns: ScoreForms.
    Description:
        Returns all Scores in the database, ordered from low to high.
        Results can be limited by the provided limit value, or a defualt of 5.

### get_user_scores

    Path: 'scores/user/{user_name}'
    Method: GET
    Parameters: user_name, email (optional)
    Returns: ScoreForms.
    Description:
        Returns all Scores for the given User (unordered).
        Will raise a NotFoundException if a User with that user_name can't be found.

### get_average_attempts_remaining

    Path: 'games/average_attempts'
    Method: GET
    Parameters: None
    Returns: StringMessage
    Description:
        Returns the average number of attempts remaining for all active Games.
        Retrieves value from a previously cached memcache key.

## Models

### User

    Stores information about a User.

    Contains
        user_name - (Required) - The User's name
        email - (Optional) - The User's email address
        win_percentage - The win percentage for all Games belonging to this User
        average_misses - The average number of misses for all Games belonging to this User

### Game

    Stores information about a Game.
    Associated with User model via KeyProperty.

    Contains
        private_word - The word assigned for this Game - eg. 'boat'
        public_word - The User's current knowledge of the word - eg. '__at'
        attempts_allowed - The number of attempts allowed for this Game
        attempts_remaining - The number of attempts remaining for this Game
        guesses - An array of Guesses to track each Guess the User makes
        guesses_set - A set for tracking unique Guesses for easy lookup
        game_over - A boolean for tracking if this Game is over
        cancelled - A boolean for tracking if this Game is cancelled
        won - A boolean for tracking if this Game is won
        user - The User who owns this Game, tracked via KeyProperty

### Score

    Stores the score for completed (won) games.
    Associated with User model via KeyProperty.

    Contains
        user_name - The User's name
        date - The date this score was recorded
        won - A boolean for tracking if this Game is won
        misses - The number of misses made before this Game was won

## Forms

### UserForm

    A representation of a User
    Contains
        name - The User's name
        win_percentage - The percentage of won Games over all this User's Games

### UserForms

    A container for multiple UserForm objects

### GuessForm

    A representation of a Guess
    Contains
        guess - The Guess value
        miss - A boolean for if this Guess was in the word
        message - The resulting message alerting the User of the affect of their Guess
        state - The state of the known word after this Guess is made

### GuessForms

    A container for multiple GuessForm objects

### GameForm

    A representation of a Game
    Contains
        urlsafe_key - The unique key for this Game
        user_name - The username of the User this Game belongs to
        public_word - The User's current knowledge of the word - eg. '__at'
        attempts_remaining - The number of attempts remaining for this Game
        guesses - An array of Guesses to track each Guess the User makes
        game_over - A boolean for tracking if this Game is over
        cancelled - A boolean for tracking if this Game is cancelled
        won - A boolean for tracking if this Game is won
        message - The resulting message alerting the User of the state of this Game

### GameForms

    A container for multiple GameForm objects

### NewGameForm

    Used to create a new Game
    Contains
        user_name - The username of the User this Game belongs to
        attempts - The number of attempts this Game should allow

### MakeMoveForm

    Used to register a Guess in a Game
    Contains
        guess - The Guess passed by the User

### ScoreForm

    A representation of a Score
    Contains
        user_name - The User's name
        date - The date this score was recorded
        won - A boolean for tracking if this Game is won
        misses - The number of misses made before this Game was won

### ScoreForms

    A container for multiple ScoreForm objects

### StringMessage

    A general purpose String container
