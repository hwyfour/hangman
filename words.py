#!/usr/bin/env python

"""
words.py

This file contains a dictionary of words and a method for returning a random one
when initializing a new game.
"""

import random

words = [
    'udacity',
    'university',
    'trouble',
    'international'
]


def get_word():
    """Return a random word from the dictionary"""

    return words[random.choice(range(0, len(words)))]
