"""
Bot Package
"""

import bot.reputation as reputation
import bot.minesweeper_view as minesweeper_view
import bot.minesweeper as minesweeper
import bot.config as config
import bot.client as client
__version__ = '0.1.0'

from typing import Dict, Literal

WeightedActions = Dict[str, int]
"""
Dictionary mapping Bot actions to their corresponding probabilities

NOTE: Probabilities must add up to 100

Possible actions:
    * React: `{'❤️': 100}`
    * Reply: `{'my message': 100}`
    * Image Reply: `{'../my_image.jpg', 100}`
"""

ActionGroup = Dict[Literal['react_probability', 'reply_probability',
                           'image_probability', 'reactions', 'replies',
                           'images'], int | WeightedActions]
"""
Dictionary mapping action probability and action content keys with their integer probabilities
or `WeightedActions` dictionaries

Action probability keys with integer probabilities as values are:
    * `'react_probability'`: emoji react on a message with a weighted react
    * `'reply_probability'`: text reply to a message with a weighted reply
    * `'image_probability'`: image reply to a message with a weighted image

Keys corresponding to `WeightedActions` are:
    * `'reactions'`: map of emoji to probabilty
    * `'replies'`: map of text message to probability
    * `'images'`: map of image path to probability
"""

TriggerActionGroups = Dict[str, ActionGroup]
"""
Dictionary mapping entity triggers (emoji reacts/message content) with their corresponding
`ActionGroups`.
"""

IDTriggers = Dict[str, TriggerActionGroups]
"""
Dictionary mapping entity (user/role) IDs with their corresponding `TriggerActionGroups`
"""

EntityTypeIDs = Dict[Literal['users', 'roles'], IDTriggers]
"""
Dictionary mapping entity type (user/role) to their corresponding `IDTriggers`

Accepted entity type keys:
    * `'users'`
    * `'roles'`
"""

# Since we are creating type defs in here, we import at the bottom to avoid circular import issues
