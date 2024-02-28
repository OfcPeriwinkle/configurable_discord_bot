"""
Bot Config

Handles config parsing
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

from bot import EntityTypeIDs, TriggerActionGroups, WeightedActions


@dataclass
class BotActions:
    """
    Actions the Bot may perform when an event occurs
    """

    # Actions and their weights are separate since the decision logic is based on random.choices
    # which expects two lists, one of a sample population and another of its weights
    react_probability: int | None = None
    reacts: List[str] | None = None
    reaction_weights: List[int] | None = None

    reply_probability: int | None = None
    replies: List[str] | None = None
    reply_weights: List[int] | None = None

    image_probability: int | None = None
    images: List[str] | None = None
    image_weights: List[int] | None = None

    reputation_change: int | None = None


@dataclass
class BotEntityActions:
    """
    Group of user and role-dependent Bot actions for different trigger phrases or reaction emoji
    reactions

    Args:
        user_actions: (Optional) dictionary mapping user_ids to trigger phrases/emojis and their
            corresponding actions; defaults to None
        role_actions: (Optional) dictionary mapping role_ids to trigger phrases/emojis and their
            corresponding actions; defaults to None
    """

    user_actions: Dict[int, Dict[str, BotActions]] | None = None
    role_actions: Dict[int, Dict[str, BotActions]] | None = None


class BotConfig:
    """
    Bot's interface for the config file
    """

    def __init__(self, config_path: str):
        """
        Create a new `BotConfig` instance

        Args:
            config_path: the path to the config file to process
        """

        with open(config_path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)

        # Process mandatory config
        self.guild = config['guild']
        self.allowed_channels = config['allowed_channels']
        self.true_replies = config['true_replies']
        self.commands = config['commands']

        # Process message and reaction action groups
        self.message_actions = None
        self.reaction_actions = None

        if 'message_actions' in config:
            self.message_actions = self._process_entity_actions(
                config['message_actions'])
        if 'reaction_actions' in config:
            self.reaction_actions = self._process_entity_actions(
                config['reaction_actions'])

    @staticmethod
    def _process_entity_actions(entity_types: EntityTypeIDs) -> BotEntityActions:
        """
        Process actions for user and role entities

        Args:
            entity_types: An `EntityTypeIDs` dictionary

        Returns:
            A `BotEntityActions` object
        """

        user_actions = {}
        if 'users' in entity_types:
            for user_id, trigger_actions in entity_types['users'].items():
                user_actions[int(user_id)] = BotConfig._process_trigger_action_groups(
                    trigger_actions)

        role_actions = {}
        if 'roles' in entity_types:
            for role_id, trigger_actions in entity_types['roles'].items():
                role_actions[int(role_id)] = BotConfig._process_trigger_action_groups(
                    trigger_actions)

        return BotEntityActions(user_actions, role_actions)

    @staticmethod
    def _get_weighted_actions(actions: WeightedActions) -> Tuple[List[str], List[int]]:
        """
        Given a `WeightedActions` dictionary, process actions and their weights and return them as
        two lists within a tuple

        Args:
            actions: A `WeightedActions` dictionary

        Returns:
            A tuple containing two lists `(actions, weights)`
        """

        processed_actions = list(actions.keys())
        processed_action_weights = list(actions.values())

        return processed_actions, processed_action_weights

    @staticmethod
    def _process_trigger_action_groups(
            trigger_action_groups: TriggerActionGroups) -> Dict[str, BotActions]:
        """
        Process `TriggerActionGroups` by creating `BotActions` objects for each trigger

        Args:
            trigger_action_groups: A `TriggerActionGroups` dictionary

        Returns:
            A dictionary where each key is a trigger and each value is its corresponding
            `BotActions` object
        """

        processed_actions = {}
        for trigger, action_group in trigger_action_groups.items():
            # Process emoji reactions
            # TODO: support custom emoji
            react_prob = action_group.get('react_probability', 0)
            react_actions = action_group.get('reactions', None)
            reacts, react_weights = None, None

            if react_actions is not None:
                reacts, react_weights = BotConfig._get_weighted_actions(react_actions)

            # Process text responses
            reply_prob = action_group.get('reply_probability', 0)
            reply_actions = action_group.get('replies', None)
            replies, reply_weights = None, None

            if reply_actions is not None:
                replies, reply_weights = BotConfig._get_weighted_actions(reply_actions)

            # Process image responses
            image_prob = action_group.get('image_probability', 0)
            image_actions = action_group.get('images', None)
            images, image_weights = None, None

            if image_actions is not None:
                images, image_weights = BotConfig._get_weighted_actions(image_actions)

            if react_prob + reply_prob + image_prob > 100:
                raise ValueError(f'Sum of action probabilities for trigger {trigger} must '
                                 'equal 100')

            rep_change = action_group.get('reputation_change', None)

            # This doesn't really need to be it's own class, in fact performance-wise it would be
            # slightly better to just make this a dict without all the sugar a class adds, but I
            # like using intellisense so 🤷‍♂️
            processed_actions[trigger] = BotActions(
                react_prob, reacts, react_weights,
                reply_prob, replies, reply_weights,
                image_prob, images, image_weights,
                rep_change)

        return processed_actions
