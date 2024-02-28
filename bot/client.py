"""
Bot Client

Handles Discord sessions and contains code for the Bot's actions
"""

import logging
import random
import time
from typing import Dict, List

import discord
import requests
import supabase
from discord.ext import commands

from bot.config import BotConfig, BotActions
from bot.minesweeper_view import MinesweeperView
from bot.reputation import get_reputation, get_leaderboard, update_reputation

logger = logging.getLogger('discord')


def time_description(seconds: int) -> str:
    """
    Get a string representing a very approximate description of a time in seconds.

    Args:
        seconds: the time to get a description for as an integer representing number of seconds

    Returns:
        A string approximately describing the time in seconds, minutes, or hours

        Ex: 4000 seconds -> "about 1 hour"
    """

    if seconds < 60:
        adjusted_time = seconds
        unit = 'second'
    elif seconds < 3600:
        adjusted_time = seconds // 60
        unit = 'minute'
    else:
        adjusted_time = seconds // 3600
        unit = 'hour'

    return f'about {adjusted_time} {unit}{"s" if adjusted_time > 1 else ""}'

# TODO: Add Logging
# TODO: Export bot functionality into cogs


class BotClient(commands.Bot):
    """
    Bot and related Discord client session manager

    All non-command callback functionality is implemented by overriding the corresponding default
    implementation (i.e. on_ready()). The discord.py package will do all the hard work of handling
    incoming events and Python's method resolution order (MRO) will handle the rest.

    Command callbacks are created with the `Bot.command()` decorator. Because of this, new custom
    commands can be added within __init__ itself.
    """

    _REACT_ACTION = 0
    _REPLY_ACTION = 1
    _IMAGE_ACTION = 2

    def __init__(self, config: BotConfig, supabase_client: supabase.Client,
                 google_api_key: str = None):
        """
        Create a new Bot session

        Args:
            config: a BotConfig describing how this session will behave
            supabase_client: a Supabase client for interacting with the Supabase database
            google_api_key: (Optional) the Google API key to enable !news commands, if None !news
                becomes a no op; defaults to None
        """

        # Config
        self._guild_id = config.guild
        self._allowed_channels = config.allowed_channels
        self._true_replies = config.true_replies
        self._commands_config = config.commands
        self._message_actions = config.message_actions
        self._reaction_actions = config.reaction_actions
        self._supabase_client = supabase_client
        self._google_api_key = google_api_key

        # Runtime state
        self._active_cooldowns = {}

        # Set intents (basically a Discord bot's permissions and scopes) and create bot
        intents = discord.Intents.default()

        # pylint: disable=assigning-non-slot
        intents.members = True
        intents.message_content = True
        # pylint: enable=assigning-non-slot

        super().__init__(intents=intents, command_prefix='!')

        @self.check
        async def check_guild_and_channel(ctx):
            """
            Global check for commands to make sure they are called from an allowed guild or channel
            """

            if ctx.guild.id != self._guild_id:
                return False

            if ctx.channel.id not in self._allowed_channels:
                return False

            return True

        ###########################################################################################
        # User commands                                                                           #
        ###########################################################################################

        @self.command(name='eightball', help='The Bot gifts you wisdom from beyond')
        async def eightball(ctx):
            """
            User command: causes Bot to send a quote

            TODO: Change config format to have roles/users by message rather than messages by
            roles/users, right now we have a lot of repeats and it's a bit annoying
            """

            config = self._commands_config.get('eightball', None)

            if config is None or not await self._is_caller_valid(ctx, config):
                return

            responses = []
            response_weights = []

            # Check for user response overrides
            users = config['actions'].get('users', None)

            if users is not None:
                user_id = str(ctx.author.id)
                user_responses = users.get(user_id, None)

                if user_responses is not None:
                    responses.append(random.choice(user_responses))
                    response_weights.append(config['response_category_probability']['user'])

            # Get role response
            roles = config['actions'].get('roles', None)

            if roles is not None:
                first_role_id = self._get_random_matching_role(
                    ctx.author.roles, [int(key) for key in roles.keys()])

                if first_role_id is not None:
                    responses.append(random.choice(roles[str(first_role_id)]))
                    response_weights.append(config['response_category_probability']['role'])

            # Get generic response
            generic = config['actions'].get('GENERIC', None)

            if generic is not None:
                responses.append(random.choice(generic))
                response_weights.append(config['response_category_probability']['generic'])

            await ctx.send(random.choices(responses, response_weights, k=1)[0])

            cmd_cooldown = self._active_cooldowns.get(ctx.command.name, None)

            if cmd_cooldown is None:
                self._active_cooldowns[ctx.command.name] = {
                    'all': time.time() + random.choice(config['cooldowns'])
                }
            else:
                self._active_cooldowns[ctx.command.name]['all'] = time.time() + random.choice(
                    config['cooldowns'])

        @self.command(name='news',
                      help='The Bot sends you the latest in news and entertainment')
        async def news(ctx):
            """
            User command: causes Bot to send the latest video from a random youtube channel
            """

            if self._google_api_key is None:
                return

            config = self._commands_config['news']

            if config is None or not await self._is_caller_valid(ctx, config):
                return

            # Get the uploads playlist for a random youtube chanel
            channel_payload = {
                'part': 'contentDetails',
                'id': random.choice(config['youtube_channel_ids']),
                'maxResults': 1,
                'key': self._google_api_key
            }
            channel_list_r = requests.get(
                'https://youtube.googleapis.com/youtube/v3/channels', params=channel_payload,
                timeout=5)

            try:
                channel_list_r.raise_for_status()
            except requests.exceptions.HTTPError as err:
                await ctx.send(f'Uploads playlist fetch recieved {str(err)}')

            uploads_id = channel_list_r.json(
            )['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # PlaylistItems.list to get most recent upload
            playlist_items_payload = {
                'part': ['contentDetails'],
                'playlistId': uploads_id,
                'maxResults': 1,
                'key': self._google_api_key
            }
            playlist_items_list_r = requests.get(
                'https://youtube.googleapis.com/youtube/v3/playlistItems',
                params=playlist_items_payload, timeout=5)

            try:
                channel_list_r.raise_for_status()
            except requests.exceptions.HTTPError as err:
                await ctx.send(f'Latest upload fetch received {str(err)}')

            video_id = playlist_items_list_r.json(
            )['items'][0]['contentDetails']['videoId']

            await ctx.send(f'https://youtube.com/watch?v={video_id}')

            cmd_cooldown = self._active_cooldowns.get(ctx.command.name, None)

            if cmd_cooldown is None:
                self._active_cooldowns[ctx.command.name] = {
                    'all': time.time() + random.choice(config['cooldowns'])
                }
            else:
                self._active_cooldowns[ctx.command.name]['all'] = time.time() + random.choice(
                    config['cooldowns'])

        @self.command(name='ms', help='Minesweeper: Find the mines!')
        async def minesweeper(ctx, dimensions: int = 4, bombs: int = 3):
            """
            User command: create a minesweeper clone using Discord views and buttons
            """

            config = self._commands_config['ms']

            if config is None or not await self._is_caller_valid(ctx, config):
                return

            if not 1 < dimensions <= 5:
                await ctx.send(content='Invalid dimensions')
                return

            if not 0 < bombs <= dimensions ** 2:
                await ctx.send(content='Invalid number of aircraft')
                return

            # Update cooldown
            cmd_cooldown = self._active_cooldowns.get(ctx.command.name, None)
            role_id = self._get_random_matching_role(
                ctx.author.roles, [int(key) for key in config['role_cooldowns'].keys()])

            if role_id is None:
                cooldown_times = config['cooldowns']
            else:
                cooldown_times = range(*config['role_cooldowns'][str(role_id)])

            if cmd_cooldown is None:
                self._active_cooldowns[ctx.command.name] = {
                    'users': {ctx.author.id: time.time() + random.choice(cooldown_times)},
                }
            else:
                self._active_cooldowns[ctx.command.name]['users'][ctx.author.id] = \
                    time.time() + random.choice(cooldown_times)

            logger.info('Set cooldown for %s to %s', ctx.author.display_name,
                        self._active_cooldowns[ctx.command.name]['users'][ctx.author.id])

            # Setup game board initial state
            embed = discord.Embed(
                title=f'{ctx.author.display_name} must find the mines!',
                color=discord.Color.blurple())
            embed.add_field(name='Mines:', value=bombs)
            embed.add_field(name='Moves:', value=0)

            view = MinesweeperView(
                board_dimension=dimensions,
                num_bombs=bombs,
                embed=embed,
                user=ctx.author,
                supabase_client=self._supabase_client)

            await ctx.reply(view=view, embed=embed)
            await view.wait()

        @self.command(name='me', help='Check your reputation')
        async def reputation_check(ctx):
            """
            User command: check your reputation

            Args:
                user_name: (Optional) the name of the user to check the reputation of; if not
                    provided, the reputation of the caller will be checked
            """

            reputation = get_reputation(ctx.author.id, self._supabase_client)

            embed = discord.Embed(
                title=f'{ctx.author.display_name}\'s Reputation',
                color=discord.Color.blurple())
            embed.add_field(name='Score:', value=reputation)

            await ctx.reply(embed=embed)

        @self.command(name='lb', help='Check the reputation leaderboard')
        async def reputation_leaderboard(ctx, order: str = 't'):
            """
            User command: check the reputation leaderboard
            """

            order = order.lower()

            if order not in ['b', 't']:
                await ctx.reply('Invalid argument. Must be "b" or "t"')
                return

            descending = order == 't'
            leaderboard = get_leaderboard(self._supabase_client, descending)

            if leaderboard is None:
                return

            embed = discord.Embed(
                title=f'{"Honorable" if descending else "Shameful"} Leaderboard',
                color=discord.Color.blurple())

            for i, (user, rep) in enumerate(leaderboard.items()):
                embed.add_field(
                    name=f'{i + 1}. {user}',
                    value=f'Score: {rep}',
                    inline=False)

            await ctx.reply(embed=embed)

    async def _is_caller_valid(self, ctx, command_config: dict) -> bool:
        """
        Verify that a caller for a command is valid and that no cooldown is currently active

        Args:
            ctx: the command's context
            command_config: a dictionary describing the command's configuration, must include keys
                `'enabled'`, `'restricted_roles'`, `'restricted_users`', `'cooldown_message_prob'`,
                and `'cooldown_messages'`

        Returns:
            True if caller is valid; False otherwise
        """

        if not command_config['enabled'] or ctx.author.id in command_config['restricted_users']:
            return False

        restricted_role = self._get_random_matching_role(
            ctx.author.roles, command_config['restricted_roles'])

        if restricted_role is not None:
            await ctx.send(f'Try again in about {random.randint(2, 30)} '
                           f'{random.choice(["weeks", "months", "years"])}')
            return False

        """
        Cooldowns are stored as a dictionary with the command name as the key, and a dictionary
        containing the cooldowns for the command as the value. The cooldowns dictionary has two
        keys: 'all' and 'users'. The 'all' key contains the cooldown for all users, and the
        'users' key contains a dictionary of user IDs mapped to their cooldowns.

         Example:
        {
            'bs': {
                'all': 1234567890.0,
                'users': {
                    1234567890: 1234567890.0
                }
            }
        }

        Right now, the 'user' cooldowns take precedence over the 'all' cooldowns. This means that
        if a user has a cooldown, they will not be able to use the command even if the 'all'
        cooldown has expired.
        """
        cooldowns = self._active_cooldowns.get(ctx.command.name, None)
        logger.info('Cooldowns for %s: %s', ctx.command.name, cooldowns)

        all_cooldown = None
        user_cooldowns = None

        if cooldowns is not None:
            all_cooldown = cooldowns.get('all', None)
            user_cooldowns = cooldowns.get('users', None)

        in_cooldown = False

        if all_cooldown is not None and time.time() < all_cooldown:
            in_cooldown = True
            cooldown_time = all_cooldown

        if user_cooldowns is not None and ctx.author.id in user_cooldowns:
            user_cooldown = user_cooldowns[ctx.author.id]

            if time.time() < user_cooldown:
                in_cooldown = True
                cooldown_time = user_cooldown

        if in_cooldown:
            if random.randint(0, 100) < command_config['cooldown_message_prob']:
                time_desc = time_description(int(cooldown_time - time.time()))
                await ctx.send(f'{random.choice(command_config["cooldown_messages"])}\n'
                               f'Try again in {time_desc}')
            return False

        return True

    ###############################################################################################
    # Event handlers                                                                              #
    ###############################################################################################

    def _is_event_valid(self, guild_id: int, channel_id: int, author: discord.Member) -> bool:
        """
        Verify that an event is in the valid guild or channel and that the author is human

        Args:
            guild_id: the id of the guild the event is in
            channel_id: the id of the channel the event is in
            author: the author `discord.Member` of the event

        Returns:
            True if the event is valid; False otherwise
        """

        if guild_id != self._guild_id:
            return False
        if channel_id not in self._allowed_channels:
            return False
        if author.id == self.user.id or author.bot:
            return False

        return True

    async def on_ready(self):
        """
        Event handler: triggered by a successful websocket connection
        """

        logger.info('%s has connected to Discord!', self.user.name)

        # TODO: Multi-guild support and scope select by guild
        supabase_users = self._supabase_client.table('users').select('discord_id').execute().data
        supabase_user_ids = {int(user['discord_id']) for user in supabase_users}

        guild_members = {member.id: member for member in self.guilds[0].members if not member.bot}
        ids_not_in_db = set(guild_members.keys()) - supabase_user_ids

        user_rows = [{'discord_id': discord_id,
                      'discord_name': guild_members[discord_id].name,
                     'is_admin': False} for discord_id in ids_not_in_db]

        res = self._supabase_client.table('users').insert(user_rows).execute()
        logger.info('Added %s users to the database', len(res.data))

    async def on_member_join(self, member: discord.Member):
        """
        Event handler: triggered when a new user joins the guild

        Args:
            member: the `discord.Member` that joined
        """

        if member.bot:
            return

        self._supabase_client.table('users').insert(
            {'discord_id': member.id, 'discord_name': member.name, 'is_admin': False}).execute()

        logger.info('New user joined: %s (%s)', member.name, member.id)

    async def _handle_message_action(self, actions: BotActions,
                                     message: discord.Message) -> bool:
        """
        Perform a randomly selected action triggered by a message

        Args:
            actions: the `BotActions` to be performed
            message: the `discord.Message` that triggered the action

        Returns:
            True if an action was performed; otherwise False
        """

        action_prob = actions.react_probability + \
            actions.reply_probability + actions.image_probability
        noop_prob = 100 - action_prob

        # Determine what action should be taken: emoji react, text reply, noop
        action = random.choices(
            population=[BotClient._REACT_ACTION,
                        BotClient._REPLY_ACTION,
                        BotClient._IMAGE_ACTION, None],
            weights=[actions.react_probability,
                     actions.reply_probability,
                     actions.image_probability, noop_prob],
            k=1)[0]

        if action is None:
            return False

        match action:
            case BotClient._REACT_ACTION:
                choice = random.choices(
                    actions.reacts, actions.reaction_weights, k=1)[0]
                await message.add_reaction(choice)
            case BotClient._REPLY_ACTION:
                choice = random.choices(
                    actions.replies, actions.reply_weights, k=1)[0]

                if self._true_replies:
                    await message.reply(choice)
                else:
                    ctx = await self.get_context(message)
                    await ctx.send(choice)
            case BotClient._IMAGE_ACTION:
                choice = random.choices(
                    actions.images, actions.image_weights, k=1)[0]
                await message.reply(file=discord.File(choice))
            case _:
                raise ValueError(f'Action {action} is not valid')

        # Action occurred
        return True

    def _get_random_matching_role(
            self, roles: List[discord.Role], role_ids: List[int]) -> int | None:
        """
        Get a randomly selected matching role if at least one exists between them

        Args:
            roles: a list of `discord.Role` that a user has
            role_ids: a list of role IDs that have actions attributed to them

        Returns:
            A randomly selected matching role ID or None if no IDs match
        """

        entity_role_ids = [role.id for role in roles]
        matching_roles = [id for id in role_ids if id in entity_role_ids]

        if len(matching_roles) == 0:
            return None

        return random.choice(matching_roles)

    def _get_action_for_message(self, lowered_message: str,
                                action_group: Dict[str, BotActions]) -> BotActions | None:
        """
        Get the first relevant action from a processed action group based on message content. If no
        relevant action is found, a `'GENERIC'` key is checked.

        Args:
            lowered_message: the message content as a str only containing lowercase characters
            action_group: a dictionary mapping substrings to `BotActions`

        Returns:
            BotActions for the first matching substring found in `lowered_message`. None if no
            substring is found or if there is no `'GENERIC'` key.
        """

        # Find actions matching text within the message
        for text, actions in action_group.items():
            if text in lowered_message:
                return actions

        # Check for generic actions
        if 'GENERIC' in action_group:
            return action_group['GENERIC']

        return None

    async def on_message(self, message: discord.Message) -> None:
        """
        Event handler: triggers when a messages is sent
        """

        if not self._is_event_valid(message.guild.id, message.channel.id, message.author):
            return

        # See if a command was called
        ctx = await self.get_context(message)

        if ctx.valid:
            await self.process_commands(message)
            return

        if self._message_actions is None:
            return

        # Message did not contain a command; see if the author has user actions
        user_id = message.author.id
        uniform_content = message.content.lower()

        if self._message_actions.user_actions is not None and \
                user_id in self._message_actions.user_actions:
            actions = self._get_action_for_message(uniform_content,
                                                   self._message_actions.user_actions[user_id])

            if actions is not None and await self._handle_message_action(actions, message):
                return

        # No user action performed; check role actions
        if self._message_actions.role_actions is not None:
            first_role_id = self._get_random_matching_role(
                message.author.roles, self._message_actions.role_actions.keys())

            # If not matching role ID was found, there are no other actions to perform
            if first_role_id is None:
                return

            actions = self._get_action_for_message(
                uniform_content, self._message_actions.role_actions[first_role_id])

            if actions is not None and await self._handle_message_action(actions, message):
                return

    def _change_user_reputation(self, reactor: discord.Member,
                                author: discord.Member, emoji: str) -> int | None:
        """
        Change the reputation of a user based on a reaction

        Args:
            reactor: the member who reacted to the message
            author: the member who posted the message
            emoji: the emoji that was reacted with

        Returns:
            The value of the reputation change or None if no action was performed
        """

        if reactor.id == author.id:
            return None

        # Check if the reactor has any user reputation changes
        user_reactions = self._reaction_actions.user_actions.get(reactor.id, {})
        actions = user_reactions.get(emoji, None)
        rep_change = None if actions is None else actions.reputation_change

        if rep_change is not None:
            if not update_reputation(author.id, rep_change, self._supabase_client):
                return None

            return rep_change

        # There were no user reputation changes; check role reputation changes
        reactor_role = self._get_random_matching_role(
            reactor.roles, self._reaction_actions.role_actions.keys())
        role_reactions = self._reaction_actions.role_actions.get(reactor_role, {})
        actions = role_reactions.get(emoji, None)
        rep_change = None if actions is None else actions.reputation_change

        if rep_change is None:
            return None

        if not update_reputation(author.id, actions.reputation_change, self._supabase_client):
            return None

        return rep_change

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Event handler: handles emoji reactions being added to messages
        """

        if not self._is_event_valid(payload.guild_id, payload.channel_id, payload.member):
            return

        if self._reaction_actions is None:
            return

        channel = self.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # Change message author's reputation if they aren't the sender
        rep_change = self._change_user_reputation(
            payload.member, message.author, payload.emoji.name)

        if rep_change is not None:
            await channel.send(f'{message.author.display_name} has been '
                               f'{"awarded" if rep_change > 0 else "fined"} {abs(rep_change)} '
                               'reputation points')

        # Give user actions the opportunity to trigger
        if self._reaction_actions.user_actions is not None and \
                payload.member.id in self._reaction_actions.user_actions:

            # Check if reaction emoji has relevant actions
            emoji_actions = self._reaction_actions.user_actions[payload.member.id]
            actions = emoji_actions.get(payload.emoji.name, None)

            if actions is not None:
                if await self._handle_message_action(actions, message):
                    return

        # No user action performed; check role actions
        if self._reaction_actions.role_actions is not None:
            first_role_id = self._get_random_matching_role(
                payload.member.roles, self._reaction_actions.role_actions.keys())

            # If not matching role ID was found, there are no other actions to perform
            if first_role_id is None:
                return

            # Check if reaction emoji has relevant actions
            emoji_actions = self._reaction_actions.role_actions[first_role_id]
            actions = emoji_actions.get(payload.emoji.name, None)

            if actions is not None:
                if await self._handle_message_action(actions, message):
                    return
