#!/usr/bin/env python3

from flask import Flask, request, jsonify
from config import *
import threading
from time import sleep
from engine_bot import *
from qq_adapter import *

bot_app = Flask(__name__)
webhook_app = Flask(__name__)


@bot_app.route('/', methods=['POST'])
def bot():
    data = request.get_json()
    if not data['group_id'] in ENABLED_GROUPS:
        # bot only works in enabled groups
        return 'failed'
    commands = {'e!help': command_help}
    commands[data['message']](data)
    return 'success'


def run_bot():
    bot_app.run(host=HOST, port=BOT_PORT, debug=DEBUG_MODE)


def run_webhook():
    webhook_app.run(host=HOST, port=WEBHOOK_PORT, debug=DEBUG_MODE)


if __name__ == '__main__':
    if DEBUG_MODE:
        run_bot()
    else:
        threading.Thread(target=run_bot, daemon=True).start()
        threading.Thread(target=run_webhook, daemon=True).start()
        while True:
            sleep(1)