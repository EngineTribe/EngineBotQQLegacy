#!/usr/bin/env python3

from flask import Flask, request
from config import *
import threading
from time import sleep
from engine_bot import *
from qq_adapter import *
import aiohttp
import rapidjson as json

bot_app = Flask(__name__)
webhook_app = Flask(__name__)


def get_cmdline(message: str) -> str | None:
    for line in message.splitlines(keepends=False):
        line = line.strip()
        if line.startswith("e!"):
            return line
    return None


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
                await send_group_msg(data['group_id'],
                                     f'{data["user_id"]} 已退群，但并没有注册引擎部落账号。所以不进行操作。')
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
            'e!server': command_server,
            'e!execute': command_execute
        }
        command_function = None
        _command: str = ''
        cmdline = get_cmdline(data['message'])
        if cmdline is None:
            # 匹配 cmdline 失败
            return 'Unknown command'
        for command in commands:
            if cmdline.startswith(command):
                _command = command
                command_function = commands[command]
                break
        if (command_function is not None) and (_command != ''):
            data['message'] = data['message'].strip()
            data['parameters'] = cmdline.replace(_command, '').strip()
            retval = await command_function(data)
            return retval if retval is not None else 'Success'
        else:
            if cmdline is not None:
                await send_group_msg(data['group_id'], f'❌ 未知命令: {cmdline}')
            return 'Unknown command'


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
                      f'{webhook["workflow_run"]["head_commit"]["message"]}'
            for group in ENABLED_GROUPS:
                await send_group_msg(group_id=group, message=message)
            return 'Success'
    elif 'release' in webhook:
        if webhook["action"] == 'published':
            message = f'⏩ [CQ:at,qq=all] 引擎部落服务器发布了新的大版本: {webhook["release"]["tag_name"]} !\n' \
                      f'更新日志如下:\n' \
                      f'{webhook["release"]["body"]}'
            for group in ENABLED_GROUPS:
                await send_group_msg(group_id=group, message=message)
            return 'Success'
    for group in ENABLED_GROUPS:
        await send_group_msg(
            group_id=group,
            message=f'❌ 接收到了新的 GitHub 推送消息，但并未实现对应的推送条目。\n'
                    f'{json.dumps(webhook, ensure_ascii=False)}'
        )
    return 'NotImplemented'


@webhook_app.route('/enginetribe', methods=["POST"])
async def webhook_enginetribe():
    webhook: dict = request.get_json()
    message: str = ''
    match webhook["type"]:
        case 'new_arrival':  # new arrival
            message = f'📤 {webhook["author"]} 上传了新关卡: {webhook["level_name"]}\n' \
                      f'ID: {webhook["level_id"]}'
        case 'new_featured':  # new featured
            message = f'🌟 {webhook["author"]} 的关卡 {webhook["level_name"]} 被加入了管理推荐关卡，快来玩!\n' \
                      f'ID: {webhook["level_id"]}'
        case 'permission_change':
            permission_name = {'booster': '捐赠者', 'mod': '关卡管理员'}[webhook['permission']]
            message = f"{'🤗' if webhook['value'] else '😥'} " \
                      f"{webhook['username']} {'获得' if webhook['value'] else '失去'}了" \
                      f"引擎部落的{permission_name}权限！"
        case _:
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
    if message != '':
        for group in ENABLED_GROUPS:
            await send_group_msg(group_id=group, message=message)
        return 'Success'
    else:
        for group in ENABLED_GROUPS:
            await send_group_msg(
                group_id=group,
                message=f'❌ 接收到了新的引擎部落推送消息，但并未实现对应的推送条目。\n'
                        f'{json.dumps(webhook, ensure_ascii=False)}'
            )
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
