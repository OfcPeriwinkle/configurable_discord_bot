"""
Functions for handling user reputation
"""

import logging

import supabase
from postgrest import APIError


def get_reputation(user_id: int, supabase_client: supabase.Client) -> int | None:
    """
    Get a user's reputation

    Args:
        user_id: The user's ID
        supabase_client: A Supabase client

    Returns:
        The user's reputation or None if the user does not exist
    """

    try:
        res = supabase_client.table('users').select(
            'reputation').eq('discord_id', str(user_id)).execute()
    except APIError as err:
        logging.error('Failed to get reputation for user %d: %s', user_id, err)
        return None

    if len(res.data) == 0:
        logging.error('User %d does not exist', user_id)
        return None

    return res.data[0]['reputation']


def set_reputation(user_id: int, reputation: int, supabase_client: supabase.Client) -> bool:
    """
    Set a user's reputation

    Args:
        user_id: The user's ID
        reputation: The user's new reputation
        supabase_client: A Supabase client

    Returns:
        True if the reputation was set successfully, False otherwise
    """

    try:
        supabase_client.table('users').update(
            {'reputation': reputation}).eq('discord_id', str(user_id)).execute()
    except APIError as err:
        logging.error('Failed to set reputation for user %d: %s', user_id, err)
        return False

    return True


def update_reputation(user_id: int, change_amount: int, supabase_client: supabase.Client) -> bool:
    """
    Update a user's reputation

    Args:
        user_id: The user's ID
        change_amount: The amount to add to the user's reputation
        supabase_client: A Supabase client

    Returns:
        True if the reputation was updated successfully, False otherwise
    """

    try:
        user_rep = supabase_client.table('users').select(
            'reputation').eq('discord_id', str(user_id)).execute()

        if len(user_rep.data) == 0:
            logging.error('User %d does not exist', user_id)
            return False

        new_rep = user_rep.data[0]['reputation'] + change_amount
        return set_reputation(user_id, new_rep, supabase_client)
    except APIError as err:
        logging.error('Failed to update reputation for user %d: %s', user_id, err)
        return False


def get_leaderboard(supabase_client: supabase.Client,
                    descending: bool = True, num: int = 5) -> dict[str, int] | None:
    """
    Get the leaderboard

    Args:
        supabase_client: A Supabase client
        descending: Whether the leaderboard should be sorted in descending order
        num: The number of users to return

    Returns:
        A dictionary mapping user IDs to reputation or None if no users were found or an error
        occurred
    """

    try:
        res = supabase_client.table('users').select('discord_name, reputation').order(
            'reputation', desc=descending).limit(num).execute()
    except APIError as err:
        logging.error('Failed to get leaderboard: %s', err)
        return None

    if len(res.data) == 0:
        return None

    return {user['discord_name']: user['reputation'] for user in res.data}
