#!/usr/bin/env python3

from flask import Flask, request, jsonify
from config import *
import json
import threading
from time import sleep
from engine_bot import *
from qq_adapter import *

bot_app = Flask(__name__)
webhook_app = Flask(__name__)


@bot_app.route('/', methods=['POST'])
async def bot():
    data = request.get_json()
    if not data['group_id'] in ENABLED_GROUPS:
        # bot only works in enabled groups
        return 'failed'
    commands = {
        'e!help': command_help,
        'e!register': command_register,
        'e!permission': command_permission,
        'e!report': command_report,
        'e!search': command_search,
        'e!ban': command_ban
    }
    await commands[data['message'].strip().split(' ')[0]](data)
    return 'success'


# GitHub webhook
@webhook_app.route('/payload', methods=['POST'])
async def webhook_payload():
    webhook = request.get_json()
    if 'head_commit' in webhook:  # push
        message = '📤 ' + webhook['repository']['name'] + ' 仓库中有了新提交:\n'
        message += webhook['head_commit']['message'] + '\n'
        message += '(由 ' + webhook['head_commit']['committer']['name'] + ' 提交)'
        for group in ENABLED_GROUPS:
            send_group_msg(group_id=group, message=message)
        return 'Success'
    elif 'workflow_run' in webhook:
        if webhook['action'] == 'completed':
            message = '📤 ' + webhook['repository']['name'] + ' 仓库的网页部署完成:\n'
            message += webhook['workflow_run']['head_commit']['message']
            for group in ENABLED_GROUPS:
                send_group_msg(group_id=group, message=message)
            return 'Success'
        else:
            return 'NotImplemented'
    elif 'release' in webhook:
        if webhook['action'] == 'published':
            message = '⏩ [CQ:at,qq=all] 引擎部落服务器发布了新的大版本: ' + webhook['release']['tag_name'] + '!\n'
            message += '更新日志如下:\n'
            message += webhook['release']['body']
            for group in ENABLED_GROUPS:
                send_group_msg(group_id=group, message=message)
            return 'Success'
        else:
            return 'NotImplemented'


@webhook_app.route('/enginetribe', methods=['POST'])
async def webhook_enginetribe():
    webhook = request.get_json()
    if webhook['type'] == 'new_arrival':  # new arrival
        message = '📤 ' + webhook['author'] + ' 上传了新关卡:' + webhook['level_name'] + '\n'
        message += 'ID: ' + webhook['level_id']
        for group in ENABLED_GROUPS:
            send_group_msg(group_id=group, message=message)
        return 'Success'


def run_bot():
    bot_app.run(host=BOT_HOST, port=BOT_PORT, debug=DEBUG_MODE)


def run_webhook():
    webhook_app.run(host=WEBHOOK_HOST, port=WEBHOOK_PORT, debug=DEBUG_MODE)


if __name__ == '__main__':
    if DEBUG_MODE:
        run_bot()
    else:
        threading.Thread(target=run_bot, daemon=True).start()
        threading.Thread(target=run_webhook, daemon=True).start()
        while True:
            sleep(1)
