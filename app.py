#!/usr/bin/env python3

from flask import Flask, request
from config import *
import threading
from time import sleep
from engine_bot import *
from qq_adapter import *
import aiohttp

bot_app = Flask(__name__)
webhook_app = Flask(__name__)


@bot_app.route('/', methods=['POST'])
async def bot():
    data = request.get_json()
    if data['post_type'] == 'notice':
        if data['notice_type'] == 'group_decrease':
            async with aiohttp.request(method='POST',
                                       url=ENGINE_TRIBE_HOST + '/user/update_permission',
                                       json={'user_id': data['user_id'], 'permission': 'valid',
                                             'value': False, 'api_key': ENGINE_TRIBE_API_KEY}) as response:
                response_json = await response.json()
            if 'success' in response_json:
                await send_group_msg(data['group_id'],
                                     f'{response_json["username"]} ({data["user_id"]}) 已经退群，'
                                     f'所以帐号暂时冻结。下次入群时将恢复可玩。')
            else:
                await send_group_msg(data['group_id'], f'❌ 冻结帐号失败，{data["user_id"]} 并没有注册引擎部落账号。')
        if data['notice_type'] == 'group_increase':
            async with aiohttp.request(method='POST',
                                       url=ENGINE_TRIBE_HOST + '/user/update_permission',
                                       json={'user_id': data['user_id'], 'permission': 'valid',
                                             'value': True, 'api_key': ENGINE_TRIBE_API_KEY}):
                pass
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
            'e!unban': command_unban,
            'e!stats': command_stats,
            'e!random': command_random,
            'e!server': command_server
        }
        for command in commands:
            if data['message'].startswith(command):
                _command = command
                command_function = commands[command]
                break
        try:
            data['parameters'] = data['message'].replace(_command, '').strip()
            await command_function(data)
        except UnboundLocalError:
            await send_group_msg(data['group_id'], '❌ 命令用法不正确。')
    return 'Success'


# GitHub webhook
@webhook_app.route('/payload', methods=['POST'])
async def webhook_payload():
    webhook = request.get_json()
    if 'head_commit' in webhook:  # push
        message = f'📤 {webhook["repository"]["name"]} 代码库中有了新提交:\n' \
                  f'{webhook["head_commit"]["message"]}\n' \
                  f'By {webhook["head_commit"]["committer"]["name"]}'
        for group in ENABLED_GROUPS:
            await send_group_msg(group_id=group, message=message)
        return 'Success'
    elif 'workflow_run' in webhook:
        if webhook["action"] == 'completed':
            message = f'📤 {webhook["repository"]["name"]} 代码库中的网页部署完成:\n' \
                      f'webhook["workflow_run"]["head_commit"]["message"]'
            for group in ENABLED_GROUPS:
                await send_group_msg(group_id=group, message=message)
            return 'Success'
        else:
            return 'NotImplemented'
    elif 'release' in webhook:
        if webhook["action"] == 'published':
            message = f'⏩ [CQ:at,qq=all] 引擎部落服务器发布了新的大版本: {webhook["release"]["tag_name"]} !\n' \
                      f'更新日志如下:\n' \
                      f'{webhook["release"]["body"]}'
            for group in ENABLED_GROUPS:
                await send_group_msg(group_id=group, message=message)
            return 'Success'
        else:
            return 'NotImplemented'


@webhook_app.route('/enginetribe', methods=["POST"])
async def webhook_enginetribe():
    webhook = request.get_json()
    message = ''
    if webhook["type"] == 'new_arrival':  # new arrival
        message = f'📤 {webhook["author"]} 上传了新关卡: {webhook["level_name"]}\n' \
                  f'ID: {webhook["level_id"]}'
    if webhook["type"] == 'new_featured':  # new featured
        message = f'🌟 {webhook["author"]} 的关卡 {webhook["level_name"]} 被加入了管理推荐关卡，快来玩!\n' \
                  f'ID: {webhook["level_id"]}'
    if 'likes' in webhook["type"]:  # 10/100/1000 likes
        message = f'🎉 恭喜，{webhook["author"]} 的关卡 {webhook["level_name"]} 获得了 ' \
                  f'{webhook["type"].replace("_likes", "")} 个点赞!\n' \
                  f'ID: {webhook["level_id"]}'
    if 'plays' in webhook["type"]:  # 100/1000 plays
        message = f'🎉 恭喜，{webhook["author"]} 的关卡 {webhook["level_name"]} 已经被游玩了 ' \
                  f'{webhook["type"].replace("_plays", "")} 次!\n' \
                  f'ID: {webhook["level_id"]}'
    if 'deaths' in webhook["type"]:  # 100/1000 deaths
        message = f'🔪 {webhook["author"]} 的关卡 {webhook["level_name"]} 已经夺得了 ' \
                  f'{webhook["type"].replace("_deaths", "")} 个人头，快去挑战吧!\n' \
                  f'ID: {webhook["level_id"]}'
    if 'clears' in webhook["type"]:  # 100/1000 clears
        message = f'🎉 恭喜，{webhook["author"]} 的关卡 {webhook["level_name"]} 已经被通关 ' \
                  f'{webhook["type"].replace("_clears", "")} 次，快去挑战吧!\n' \
                  f'ID: {webhook["level_id"]}'
    if not message:
        for group in ENABLED_GROUPS:
            await send_group_msg(group_id=group, message=message)
        return 'Success'
    else:
        return 'NotImplemented'


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
            sleep(10)
