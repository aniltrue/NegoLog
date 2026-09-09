Core library API
================

The classes below are imported from the current public checkout during the
documentation build. Read the repository README for complete tournament and web
examples; implementation and migration changes are tracked in ``MAINTENANCE.md``.

Preferences and actions
-----------------------

.. autoclass:: nenv.Preference
   :members: get_utility, get_bid_at, get_random_bid

.. autoclass:: nenv.Bid

.. autoclass:: nenv.Issue

.. autoclass:: nenv.Offer

.. autoclass:: nenv.Accept

Sessions and extensions
-----------------------

.. autoclass:: nenv.AbstractAgent
   :members: initiate, receive_offer, act, terminate

.. autoclass:: nenv.Session

.. autoclass:: nenv.SessionManager

.. autoclass:: nenv.SessionLogs

.. autoclass:: nenv.Tournament

.. autoclass:: nenv.BidSpace
