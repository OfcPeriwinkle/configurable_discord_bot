import logging

import discord
import supabase

from bot.minesweeper import Board
from bot.reputation import update_reputation


class MinesweeperButton(discord.ui.Button):
    def __init__(self, x: int, y: int, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await view.dig(self.x, self.y, interaction)


class MinesweeperView(discord.ui.View):
    SCORING_MIN_BOMBS = 5

    def __init__(self, board_dimension: int, num_bombs: int,
                 embed: discord.Embed, user: discord.User, supabase_client: supabase.Client):
        """
        Create a new MinesweeperView instance
        """

        super().__init__()
        self.board_dimension = board_dimension
        self.num_bombs = num_bombs
        self.embed = embed
        self.user = user
        self.supabase_client = supabase_client

        raw_win_val = 0.5 * (((self.num_bombs ** 2) / (self.board_dimension ** 2)) + self.num_bombs)
        self.win_val = int(round(raw_win_val, 0))

        logging.info('User started minesweeper (User: %s, Board: %s, Bombs: %s, Win Value: %s)',
                     self.user.display_name, self.board_dimension, self.num_bombs, self.win_val)

        self.moves = 0
        self.game = Board(dim_size=self.board_dimension, num_bombs=self.num_bombs)
        self.buttons = []

        for row in range(self.board_dimension):
            button_row = []

            for col in range(self.board_dimension):
                button = MinesweeperButton(
                    x=row, y=col, label='\u200b', row=row, style=discord.ButtonStyle.blurple)
                button_row.append(button)

                self.add_item(button)

            self.buttons.append(button_row)

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        return interaction.user == self.user

    async def dig(self, x: int, y: int, interaction: discord.Interaction):
        """
        Dig for a bomb at a specific coordinate

        Args:
            x: the x coordinate
            y: the y coordinate
            interaction: the interaction that was triggered by a click event
        """

        victory = False
        self.moves += 1

        safe = self.game.dig(x, y)

        if not safe:
            # Picked a mine
            visible_board = self.game.board
        elif len(self.game.dug) >= self.board_dimension ** 2 - self.num_bombs:
            victory = True
            visible_board = self.game.board
        else:
            visible_board = self.game.visible_board

        # Update view to match game state
        for row in range(self.board_dimension):
            for col in range(self.board_dimension):
                board_value = visible_board[row][col]
                button = self.buttons[row][col]

                if board_value not in (0, '*'):
                    button.label = board_value

                if board_value != '\u200b':
                    button.disabled = True
                    button.style = discord.ButtonStyle.gray

                if board_value == '*' and not victory:
                    button.style = discord.ButtonStyle.red
                    button.emoji = '💥' if (row, col) == (x, y) else '💣'
                elif board_value == '*' and victory:
                    button.style = discord.ButtonStyle.success
                    button.emoji = '⛳️'

        self.embed.set_field_at(1, name='Moves:', value=self.moves)

        if victory:
            logging.info('User won minesweeper (User: %s)', interaction.user.display_name)

            self.embed.title = f'{interaction.user.display_name} found all the mines!'
            self.embed.color = discord.Color.green()

            if update_reputation(interaction.user.id, self.win_val, self.supabase_client):
                self.embed.add_field(name='Reputation:',
                                     value=f'You have been awarded {self.win_val} reputation '
                                     f'point{"s" if self.win_val > 1 else ""}!')
            self.stop()
        elif not safe:
            logging.info('User failed minesweeper (User: %s)', interaction.user.display_name)

            self.embed.title = f'{interaction.user.display_name} blew up!'
            self.embed.color = discord.Color.red()

            rep_change = int(round(self.win_val / 3, 0))

            if update_reputation(interaction.user.id, -rep_change, self.supabase_client):
                self.embed.add_field(name='Reputation:',
                                     value=f'You have been fined {rep_change} reputation '
                                     f'point{"s" if rep_change > 1 else ""}.')
            self.stop()
        else:
            self.embed.title = f'{interaction.user.display_name} selected: {x}, {y}'

        await interaction.response.edit_message(view=self, embed=self.embed)
