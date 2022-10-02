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
    if data['post_type'] == 'notice':
        if data['notice_type'] == 'group_decrease':
            response_json = requests.post(url=ENGINE_TRIBE_HOST + '/user/update_permission',
                                          json={'user_id': data['user_id'], 'permission': 'valid',
                                                'value': False, 'api_key': ENGINE_TRIBE_API_KEY}).json()
            if 'success' in response_json:
                send_group_msg(data['group_id'],
                               response_json['username'] + ' 已经退群，所以帐号暂时冻结。下次入群时将恢复可玩。')
            else:
                send_group_msg(data['group_id'], '❌ 冻结帐号失败，' + str(data['user_id']) + '并没有注册引擎部落账号。')
            return 'Success'
        if data['notice_type'] == 'group_increase':
            requests.post(url=ENGINE_TRIBE_HOST + '/user/update_permission',
                          json={'user_id': data['user_id'], 'permission': 'valid', 'value': True,
                                'api_key': ENGINE_TRIBE_API_KEY}).json()
            return 'Success'
    else:
        if not data['group_id'] in ENABLED_GROUPS:
            # bot only works in enabled groups
            return 'failed'
        commands = {
            'e!help': command_help,
            'e!register': command_register,
            'e!permission': command_permission,
            'e!report': command_report,
            'e!query': command_query,
            'e!ban': command_ban,
            'e!stats': command_stats
        }
        await commands[data['message'].strip().split(' ')[0]](data)
        return 'Success'


# GitHub webhook
@webhook_app.route('/payload', methods=['POST'])
async def webhook_payload():
    webhook = request.get_json()
    if 'head_commit' in webhook:  # push
        message = '📤 ' + webhook['repository']['name'] + ' 代码库中有了新提交:\n'
        message += webhook['head_commit']['message'] + '\n'
        message += '(由 ' + webhook['head_commit']['committer']['name'] + ' 提交)'
        for group in ENABLED_GROUPS:
            send_group_msg(group_id=group, message=message)
        return 'Success'
    elif 'workflow_run' in webhook:
        if webhook['action'] == 'completed':
            message = '📤 ' + webhook['repository']['name'] + ' 代码库中的网页部署完成:\n'
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
    if webhook['type'] == 'new_deleted':  # new deleted
        message = '🗑️ ' + webhook['author'] + ' 删除了关卡:' + webhook['level_name']
        for group in ENABLED_GROUPS:
            send_group_msg(group_id=group, message=message)
        return 'Success'
    if webhook['type'] == 'new_featured':  # new featured
        message = '🌟 ' + webhook['author'] + ' 的关卡 ' + webhook['level_name'] + ' 被加入了管理推荐关卡，快来玩!\n'
        message += 'ID: ' + webhook['level_id']
        for group in ENABLED_GROUPS:
            send_group_msg(group_id=group, message=message)
        return 'Success'
    if 'likes' in webhook['type']:  # 10/100/1000 likes
        message = '🎉 恭喜， ' + webhook['author'] + ' 上传的关卡 ' + webhook['level_name'] + ' 获得了 ' + webhook[
            'type'].replace('_likes', '') + ' 个点赞!\n'
        message += 'ID: ' + webhook['level_id']
        for group in ENABLED_GROUPS:
            send_group_msg(group_id=group, message=message)
        return 'Success'
    if 'plays' in webhook['type']:  # 100/1000 plays
        message = '🎉 恭喜， ' + webhook['author'] + ' 上传的关卡 ' + webhook['level_name'] + ' 已经被游玩 ' + webhook[
            'type'].replace('_plays', '') + ' 次!\n'
        message += 'ID: ' + webhook['level_id']
        for group in ENABLED_GROUPS:
            send_group_msg(group_id=group, message=message)
        return 'Success'
    if 'deaths' in webhook['type']:  # 100/1000 deaths
        message = '🔪 ' + webhook['author'] + ' 上传的关卡 ' + webhook['level_name'] + ' 已经夺得了 ' + webhook[
            'type'].replace('_deaths', '') + ' 个人头，快去挑战吧!\n'
        message += 'ID: ' + webhook['level_id']
        for group in ENABLED_GROUPS:
            send_group_msg(group_id=group, message=message)
        return 'Success'
    if 'clears' in webhook['type']:  # 100/1000 clears
        message = '🎉 恭喜， ' + webhook['author'] + ' 上传的关卡 ' + webhook['level_name'] + ' 已经被通关 ' + webhook[
            'type'].replace('_clears', '') + ' 次，快去挑战吧!\n'
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
