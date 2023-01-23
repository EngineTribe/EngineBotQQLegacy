import base64
from binascii import Error as BinAsciiError

from qq_adapter import *
import aiohttp
import subprocess
import rapidjson as json

STYLES = ['超马1', '超马3', '超马世界', '新超马U']

DIFFICULTY_IDS: dict[str, int] = {
    # SMM1 风格的难度名
    '简单': 0,
    '普通': 1,
    '专家': 2,
    '超级专家': 3,
    # SMM2 风格的难度名
    '困难': 2,
    '极难': 3,
    # TGRCode API 风格的难度 ID
    'e': 0,
    'n': 1,
    'ex': 2,
    'sex': 3,
    # SMMWE API 风格的难度 ID
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3
}


def prettify_level_id(level_id: str):
    return level_id[0:4] + '-' + level_id[4:8] + '-' + level_id[8:12] + '-' + level_id[12:16]


def reply(message: str, at_sender: bool = False, delete: bool = False, ):
    return json.dumps({
        'reply': message,
        'at_sender': at_sender,
        'delete': delete,
        'auto_escape': True if ('[CQ:' in message) else False
    })


def at(data: dict) -> str:
    return f'[CQ:at,qq={data["sender"]["user_id"]}]'


COMMAND_HELPS: list[tuple] = [
    ('help', '查看此帮助'),
    ('register', '注册帐号或修改密码'),
    ('query', '查询关卡信息'),
    ('report', '向管理组举报关卡'),
    ('stats', '查看上传记录'),
    ('random', '来个随机关卡'),
    ('server', '查看服务器状态')
]

ADMIN_COMMAND_HELPS: list[tuple] = [
    ('permission', '修改用户权限'),
    ('execute', '执行命令')
]
GAME_ADMIN_COMMAND_HELPS: list[tuple] = [
    ('ban', '封禁用户'),
    ('unban', '解封用户')
]


def help_item(command: str, description: str):
    return f'e!{command}: {description}。\n'


def clear_rate(deaths, clears, plays) -> str:
    if int(deaths) == 0:
        return f'{str(clears)}次通关 / {str(plays)}次游玩'
    else:
        return f'{str(clears)}次通关 / {str(plays)}次游玩 {round((int(clears) / int(plays)) * 100, 2)} %'


def level_query_metadata(level_data: dict, metadata_type: str) -> str:
    message = f'{metadata_type}: {level_data["id"]} {level_data["name"]} \n' \
              f'作者: {level_data["author"]}\n' \
              f'上传于 {level_data["date"]}\n' \
              f'{level_data["likes"]}❤  {level_data["dislikes"]}💙'
    message += ' (管理推荐关卡)\n' if (int(level_data['featured']) == 1) else '\n'
    message += f"{clear_rate(level_data['muertes'], level_data['victorias'], level_data['intentos'])}\n"
    message += f'标签: {level_data["etiquetas"]}, 游戏风格: {STYLES[int(level_data["apariencia"])]}'
    return message


async def command_help(data) -> str:
    message = f'📑 可用的命令 (输入命令以查看用法):\n'
    for command, description in COMMAND_HELPS:
        message += help_item(command, description)
    if data['sender']['user_id'] in BOT_ADMIN:
        message += '\n📑 可用的管理命令:\n'
        for command, description in ADMIN_COMMAND_HELPS:
            message += help_item(command, description)
    if data['sender']['role'] in ['admin', 'owner']:
        message += '\n📑 可用的游戏管理命令:\n'
        for command, description in GAME_ADMIN_COMMAND_HELPS:
            message += help_item(command, description)
    return reply(message.strip('\n'))


def parse_register_code(raw_register_code: str) -> list[str]:
    try:  # auto add equal sign
        register_code = base64.b64decode(raw_register_code.encode()).decode().split("\n")
    except BinAsciiError:
        try:
            register_code = base64.b64decode((raw_register_code + '=').encode()).decode().split("\n")
        except BinAsciiError:
            register_code = base64.b64decode((raw_register_code + '==').encode()).decode().split("\n")
    return register_code


async def command_register(data) -> str:
    if not data['parameters']:
        return reply(
            '🔗 打开 https://web.enginetribe.gq/register.html 以注册。\n'
            '打开 https://web.enginetribe.gq/change_password.html 以修改密码。'
        )
    else:
        try:
            raw_register_code: str = data['parameters'].split(' ')[0]
            register_code = parse_register_code(raw_register_code)
            operation = register_code[0]
            username = register_code[1]
            password_hash = register_code[2]
            if operation == 'r':  # register
                async with aiohttp.request(
                        method='POST',
                        url=ENGINE_TRIBE_HOST + '/user/register',
                        json={'username': username, 'password_hash': password_hash,
                              'user_id': str(data['sender']['user_id']),
                              'api_key': ENGINE_TRIBE_API_KEY}
                ) as response:
                    response_json = await response.json()
                if 'success' in response_json:
                    return reply(
                        message=f'🎉 {at(data)} 注册成功，'
                                f'现在可以使用 {response_json["username"]} 在游戏中登录了。',
                        delete=True
                    )
                else:
                    if response_json['error_type'] == '035':
                        return reply(
                            message=f'❌ 注册失败，一个 QQ 号只能注册一个帐号。\n'
                                    f'{at(data)} ({response_json["username"]}) 不能再注册账号了。',
                            delete=True
                        )
                    elif response_json['error_type'] == '036':
                        return reply(
                            message=f'❌ {at(data)} 注册失败。\n'
                                    f'{response_json["username"]} 用户名已经存在，请回到注册网页换一个用户名。',
                            delete=True
                        )
                    else:
                        return reply(
                            message=f'❌ {at(data)} 注册失败，发生未处理的错误。\n'
                                    f'{response_json["error_type"]}\n'
                                    f'{response_json["message"]}',
                            delete=True
                        )
            elif operation == 'c':  # change password
                async with aiohttp.request(
                        method='POST',
                        url=ENGINE_TRIBE_HOST + '/user/update_password',
                        json={'username': username, 'password_hash': password_hash,
                              'user_id': str(data['sender']['user_id']),
                              'api_key': ENGINE_TRIBE_API_KEY}
                ) as response:
                    response_json = await response.json()
                if 'success' in response_json:
                    return reply(
                        message=f'🎉 {at(data)} ({response_json["username"]}) 的密码修改成功。',
                        delete=True
                    )
                else:
                    return reply(
                        message='❌ 修改密码失败，用户错误。',
                        delete=True
                    )
            else:
                return reply(
                    message=f'❌ 无效的注册码，所选的操作 {operation} 不存在。',
                    delete=True
                )
        except Exception as e:
            return reply(
                message=f'❌ 无效的注册码，请检查是否复制完全。\n'
                        f'错误信息: {str(e)}',
                delete=True
            )


async def command_ban(data) -> str:
    if data['sender']['role'] not in ['admin', 'owner']:
        return reply(
            f'❌ {at(data)} 无权使用该命令。',
        )
    if not data['parameters']:
        return reply(
            '使用方法: e!ban 用户名',
        )
    else:
        try:
            username = data['parameters'].split(' ')[0]
            async with aiohttp.request(
                    method='POST',
                    url=ENGINE_TRIBE_HOST + '/user/update_permission',
                    json={'username': username, 'permission': 'banned',
                          'value': True, 'api_key': ENGINE_TRIBE_API_KEY}
            ) as response:
                response_json = await response.json()
            if 'success' in response_json:
                return reply(
                    f'✅ 成功封禁 {username} 。'
                )
            else:
                return reply(
                    f'❌ 权限更新失败。\n'
                    f'错误信息: {str(response_json)}'
                )
        except Exception as e:
            return reply(
                f'❌ 命令出现未知错误。\n'
                f'错误信息: {str(e)}'
            )


async def command_unban(data) -> str:
    if data['sender']['role'] not in ['admin', 'owner']:
        return reply(
            f'❌ {at(data)} 无权使用该命令。',
        )
    if not data['parameters']:
        return reply(
            '使用方法: e!unban 用户名',
        )
    else:
        try:
            username = data['parameters'].split(' ')[0]
            async with aiohttp.request(
                    method='POST',
                    url=ENGINE_TRIBE_HOST + '/user/update_permission',
                    json={'username': username, 'permission': 'banned',
                          'value': False, 'api_key': ENGINE_TRIBE_API_KEY}
            ) as response:
                response_json = await response.json()
            if 'success' in response_json:
                return reply(
                    f'✅ 成功解除封禁 {username} 。'
                )
            else:
                return reply(
                    f'❌ 权限更新失败。\n'
                    f'错误信息: {str(response_json)}'
                )
        except Exception as e:
            return reply(
                f'❌ 命令出现未知错误。\n'
                f'错误信息: {str(e)}'
            )


async def command_permission(data) -> str:
    if data['sender']['role'] not in ['admin', 'owner']:
        return reply(
            f'❌ {at(data)} 无权使用该命令。',
        )
    if not data['parameters']:
        return reply(
            '使用方法: e!permission 用户名 权限名 true或false\n'
            '权限列表: mod, admin, booster, valid, banned'
        )
    else:
        try:
            args = data['parameters'].split(' ')
            username = args[0]
            permission = args[1]
            if str(args[2]).lower() == 'true':
                value = True
            else:
                value = False
            async with aiohttp.request(
                    method='POST',
                    url=ENGINE_TRIBE_HOST + '/user/update_permission',
                    json={'username': username, 'permission': permission,
                          'value': value, 'api_key': ENGINE_TRIBE_API_KEY}
            ) as response:
                response_json = await response.json()
            if 'success' in response_json:
                return reply(
                    f'✅ 成功将 {username} 的 {permission} 权限更新为 {str(value)} 。'
                )
            else:
                return reply(
                    f'❌ 权限更新失败。\n'
                    f'错误信息: {str(response_json)}'
                )
        except Exception as e:
            return reply(
                f'❌ 命令出现错误。\n'
                f'错误信息: {str(e)}'
            )


async def command_report(data) -> str:
    if not data['parameters']:
        return reply(
            '❌ 使用方法: e!report 关卡ID'
        )
    else:
        level_id: str = data['parameters'].split(' ')[0].upper()
        if '-' not in level_id:
            level_id = prettify_level_id(level_id)
        if len(level_id) != 19:
            return reply(
                '❌ 无效的关卡 ID。'
            )
    try:
        async with aiohttp.request(
                method='POST',
                url=f'{ENGINE_TRIBE_HOST}/stage/{level_id}',
                data='auth_code=' + BOT_AUTH_CODE,
                headers={'Content-Type': 'application/x-www-form-urlencoded',
                         'User-Agent': 'EngineBot/1'}
        ) as response:
            response_json = await response.json()
        if 'error_type' in response_json:
            return reply(
                f'❌ 关卡 {level_id} 未找到。'
            )
        else:
            level_data: dict = response_json['result']
            async with aiohttp.request(
                    method='POST',
                    url=f'{ENGINE_TRIBE_HOST}/user/info',
                    json={'username': level_data['author']}
            ) as response:
                response_json_user = await response.json()
            message = f'⚠ 接到举报: {level_id} {level_data["name"]} \n' \
                      f'作者: {level_data["author"]}\n' \
                      f'作者 QQ / Discord ID: {response_json_user["result"]["user_id"]}\n' \
                      f'上传于 {level_data["date"]}\n' \
                      f'{level_data["likes"]}❤  {level_data["dislikes"]}💙\n'
            message += f"{clear_rate(level_data['muertes'], level_data['victorias'], level_data['intentos'])}\n"
            message += f'标签: {level_data["etiquetas"]}, 游戏风格: {STYLES[int(level_data["apariencia"])]}'
            await send_group_msg(group_id=ADMIN_GROUP, message=message)
            return reply(
                f'✅ 已将关卡 {level_id} 的举报信息发送至管理组。'
            )
    except Exception as e:
        return reply(
            f'❌ 获得 {level_id} 的关卡信息时出现错误，连接到引擎部落后端时出错。\n'
            f'错误信息: {str(e)}'
        )


async def command_query(data):
    if not data['parameters']:
        return reply(
            '❌ 使用方法: e!query 关卡ID'
        )
    else:
        level_id = data['parameters'].split(' ')[0].upper()
        if '-' not in level_id:
            level_id = prettify_level_id(level_id)
        if len(level_id) != 19:
            return reply(
                '❌ 无效的关卡 ID。'
            )
        try:
            async with aiohttp.request(
                    method='POST',
                    url=f'{ENGINE_TRIBE_HOST}/stage/{level_id}',
                    data='auth_code=' + BOT_AUTH_CODE,
                    headers={'Content-Type': 'application/x-www-form-urlencoded',
                             'User-Agent': 'EngineBot/1'}
            ) as response:
                response_json = await response.json()
            if 'error_type' in response_json:
                return reply(
                    f'❌ 关卡 {level_id} 未找到。'
                )
            else:
                level_data: dict = response_json['result']
                return reply(
                    level_query_metadata(level_data, '🔍 查询关卡')
                )
        except Exception as e:
            return reply(
                f'❌ 命令出现错误，连接到引擎部落后端时出错。\n'
                f'错误信息: {str(e)}'
            )


async def command_random(data) -> str:
    difficulty_query: str = ''
    if data['parameters']:
        try:
            difficulty_query: str = '&dificultad=' + str(DIFFICULTY_IDS[data['parameters'].split(' ')[0]])
        except KeyError:
            return reply(
                '❌ 无效的难度。\n'
                '可用的难度名或 ID: 简单、普通、专家、超级专家、困难、极难、e、n、ex、sex。'
            )
    try:
        async with aiohttp.request(
                method='POST',
                url=f'{ENGINE_TRIBE_HOST}/stage/random',
                data=f'auth_code={BOT_AUTH_CODE}{difficulty_query}',
                headers={'Content-Type': 'application/x-www-form-urlencoded',
                         'User-Agent': 'EngineBot/1'}
        ) as response:
            response_json = await response.json()
        level_data: dict = response_json['result']
        return reply(
            level_query_metadata(level_data, '💫 随机关卡')
        )
    except Exception as e:
        return reply(
            f'❌ 命令出现错误，连接到引擎部落后端时出错。\n'
            f'错误信息: {str(e)}'
        )


async def command_stats(data) -> str:
    if not data['parameters']:
        request_body = {'user_id': data['sender']['user_id']}
    elif data['parameters'] == str(int(data['parameters'])):
        request_body = {'user_id': str(data['parameters'])}
    else:
        request_body = {'username': data['parameters'].split(' ')[0]}
    try:
        async with aiohttp.request(
                method='POST',
                url=f'{ENGINE_TRIBE_HOST}/user/info',
                json=request_body
        ) as response:
            response_json = await response.json()
        if 'error_type' in response_json:
            return reply(
                '❌ 数据不存在。\n'
                f'{json.dumps(request_body)}'
            )
        else:
            user_data = response_json['result']
            messages: list[str] = [
                f'📜 玩家 {user_data["username"]} 的上传记录\n'
                f'共上传了 {user_data["uploads"]} 个关卡。'
            ]
            if str(user_data['uploads']) == '0':
                # 没有关卡
                return reply(
                    messages[0]
                )
            else:
                all_likes = 0
                all_dislikes = 0
                all_plays = 0
                async with aiohttp.request(
                        method='POST',
                        url=f'{ENGINE_TRIBE_HOST}/stages/detailed_search',
                        data={'auth_code': BOT_AUTH_CODE, 'author': user_data['username']},
                        headers={'Content-Type': 'application/x-www-form-urlencoded',
                                 'User-Agent': 'EngineBot/1'}
                ) as response:
                    level_datas: dict = await response.json()
                for level_data in level_datas['result']:
                    messages.append(
                        f'- {level_data["name"]}\n'
                        f'  {level_data["likes"]}❤  {level_data["dislikes"]}💙\n'
                        f'  ID: {level_data["id"]}'
                        f"{' (推荐)' if (int(level_data['featured']) == 1) else ''}\n"
                        f'  标签: {level_data["etiquetas"]}'
                    )
                    all_likes += int(level_data['likes'])
                    all_dislikes += int(level_data['dislikes'])
                    all_plays += int(level_data['intentos'])
                messages.append(
                    f'总获赞: {all_likes}'
                    f'总获孬: {all_dislikes}'
                    f'总游玩: {all_plays}'
                )
                await send_group_forward_msg(
                    group_id=data['group_id'],
                    messages=messages,
                    sender_name=f'{user_data["username"]} 的上传记录'
                )
                return '✅ 查询完毕。'
    except Exception as e:
        return reply(
            f'❌ 命令出现错误，连接到引擎部落后端时出错。\n'
            f'错误信息: {str(e)}'
        )


async def command_server(data) -> str:
    try:
        async with aiohttp.request(
                method='GET',
                url=f'{ENGINE_TRIBE_HOST}/server_stats'
        ) as response:
            response_json = await response.json()
        return reply(
            f'🗄️ 服务器状态\n'
            f'🐧 操作系统: {response_json["os"]}\n'
            f'🐍 Python 版本: {response_json["python"]}\n'
            f'👥 玩家数量: {response_json["player_count"]}\n'
            f'🌏 关卡数量: {response_json["level_count"]}\n'
            f'🕰️ 运行时间: {int(response_json["uptime"] / 60)} 分钟\n'
            f'📊 每分钟连接数: {response_json["connection_per_minute"]}'
        )
    except Exception as e:
        return reply(
            '❌ 未知错误\n' + str(e)
        )


async def command_execute(data):
    if not data['sender']['user_id'] in BOT_ADMIN:
        return reply(
            '❌ 无权使用该命令。'
        )
    try:
        process = subprocess.Popen(data['parameters'], shell=True, stdout=subprocess.PIPE)
        process.wait()
        return reply(
            process.stdout.read().decode('utf-8')
        )
    except Exception as e:
        return reply(
            '❌ 未知错误\n' + str(e)
        )
