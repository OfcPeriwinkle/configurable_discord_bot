#!/usr/bin/env python
"""
Bot Runner

Main script for running the Bot with a config json
"""

import argparse
import dotenv
import logging
import os

import supabase
import discord.utils

from bot.config import BotConfig
from bot.client import BotClient


def get_args():
    """
    Get command line arguments
    """

    parser = argparse.ArgumentParser('bot_runner',
                                     description='Configurable Discord Bot for various tasks.')
    parser.add_argument('config',
                        help='Path to the .json file containing a Bot configuration (see docs).')
    parser.add_argument('--debug', action='store_true', help='Set logging to DEBUG level.')
    parser.add_argument('--log-file', type=str, default=None,
                        help='Set the path to a file where the logger should write its output; '
                        'defaults to discord.log')

    return parser.parse_args()


def main():
    """
    Run a Bot instance
    """

    args = get_args()
    config = BotConfig(args.config)

    # Load environment variables if a .env file exists
    if os.path.exists('.env'):
        dotenv.load_dotenv()

    supabase_client = supabase.create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    bot = BotClient(config, supabase_client, google_api_key=os.getenv('GOOGLE_API_KEY'))

    handler = discord.utils.MISSING

    if args.log_file:
        handler = logging.FileHandler(filename=args.log_file, encoding='utf-8', mode='w')

    bot.run(os.getenv('DISCORD_TOKEN'), log_handler=handler,
            log_level=logging.DEBUG if args.debug else logging.INFO)


if __name__ == '__main__':
    main()
