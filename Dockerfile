FROM python:3.10-slim
WORKDIR /bot
COPY . .
RUN python -m pip install .
CMD [ "bot_runner", "config/test_config.json", "--log-file", "discord.log" ]