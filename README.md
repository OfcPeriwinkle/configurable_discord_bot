# Configurable Discord Bot

This is a simple Discord bot that can be configured using JSON files. It uses PostgreSQL to persist user reputation scores and provides a few additional features such as a minesweeper game and integration with YouTube's API to fetch recent uploads from configured channels.

This project's motivation is primarily to build some more experience using CI/CD tools, Docker, and Google Cloud Platform. The bot itself
is a just fun little app that is built into a Docker image, uploaded to DockerHub, and then deployed to a GCP computer engine VM.

Since the bot isn't really the focus of this project, please refer to the source code's documentation for how to create a config and extend the bot. If you have any questions please feel free to get in touch and I'll be happy to help!

## Features

- **Configuration**: The bot can be configured using JSON files. You can specify various settings such as response messages, command prefixes, and emoji reactions.

- **User Reputation**: The bot uses PostgreSQL to store and manage user reputation scores. Users can earn reputation points by participating in the server and engaging with other users or by playing games.

- **Minesweeper Game**: The bot includes a simple minesweeper game that users can play within the Discord server.

- **YouTube Integration**: The bot integrates with YouTube's API to fetch recent uploads from configured channels. Users can stay updated with the latest videos from their favorite channels directly within the Discord server.

## Getting Started

1. Clone the repository: 
```bash
git clone git@github.com:OfcPeriwinkle/configurable_discord_bot.git
```
2. Change into the project directory: 
```bash
cd configurable_discord_bot
```

3. Create a virtual environment:
```bash
`python3 -m venv .venv`
```
4. Activate the virtual environment: 
```bash
`source .venv/bin/activate`
```
5. Install the package:
```bash
`pip install -e .`
```
6. Set up environment variables for Discord, Supabase, and YouTube (see below)
7. Run the bot: 
```bash
bot_runner config.json
```

## Environment Variables

* SUPABASE_URL: The URL of your Supabase database.
* SUPABASE_KEY: The API key for your Supabase database.
* DISCORD_TOKEN: The bot token for your Discord bot.
* GOOGLE_API_KEY: The API key for the YouTube Data API.

## Configuration

The bot can be configured by creating a JSON file and pointing the `bot_runner` script at it.
