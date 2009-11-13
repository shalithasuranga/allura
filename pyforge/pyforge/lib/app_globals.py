# -*- coding: utf-8 -*-

"""The application's Globals object"""

__all__ = ['Globals']

from pyforge import model as M

class Globals(object):
    """Container for objects available throughout the life of the application.

    One instance of Globals is created during application initialization and
    is available during requests via the 'app_globals' variable.

    """

    def __init__(self):
        """Do nothing, by default."""
        user = M.User.make(login='test_user')
