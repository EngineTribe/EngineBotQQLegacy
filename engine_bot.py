# This file contains almost everything of Engine-bot except the web server and QQ-specific content
import base64

from qq_adapter import *


async def command_help(data):
    retval = '''📑 可用的命令:
e!help : 查看此帮助。
e!register : 注册帐号。
'''
    if data['sender']['user_id'] in BOT_ADMIN:
        retval += '''
📑 可用的管理命令:
e!permission : 更新用户权限。        
'''
    send_group_msg(group_id=data['group_id'], message=retval)
    return


async def command_register(data):
    if data['message'].strip() == 'e!register':
        send_group_msg(data['group_id'], '''🔗 打开 https://web.enginetribe.gq/register.html 以查看注册流程。''')
        return
    else:
        try:
            raw_register_code = data['message'].split(' ')[1]
            register_code = base64.b64decode(raw_register_code.strip().encode()).decode().split("\n")
            username = register_code[0]
            password_hash = register_code[1]
            response_json = requests.post(url=ENGINE_TRIBE_HOST + '/user/register',
                                          json={'username': username, 'password_hash': password_hash,
                                                'user_id': data['sender']['user_id'],
                                                'api_key': ENGINE_TRIBE_API_KEY}).json()
            if 'success' in response_json:
                send_group_msg(data['group_id'], response_json['success'])
            else:
                send_group_msg(data['group_id'], '❌ 注册失败。\n' + response_json['message'])

        except Exception as e:
            send_group_msg(data['group_id'], '❌ 无效的注册码。\n' + str(e))
            return


async def command_permission(data):
    if not data['sender']['user_id'] in BOT_ADMIN:
        send_group_msg(data['group_id'], '❌ 无权使用该命令。')
        return
    if data['message'].strip() == 'e!permission':
        send_group_msg(data['group_id'],
                       '使用方法: e!permission 用户名 权限名 true或false\n权限: mod, admin, booster, valid, banned')
        return
    else:
        try:
            args = data['message'].replace(data['message'].split(' ')[0], '').strip().split(' ')
            username = args[0]
            permission = args[1]
            if str(args[2]).lower() == 'true':
                value = True
            else:
                value = False
            response_json = requests.post(url=ENGINE_TRIBE_HOST + '/user/update_permission',
                                          json={'username': username, 'permission': permission,
                                                'value': value, 'api_key': ENGINE_TRIBE_API_KEY}).json()
            if 'success' in response_json:
                send_group_msg(data['group_id'], '✅ 成功将 '+username+' 的 '+permission+' 权限更新为 '+str(value)+'。')
            else:
                send_group_msg(data['group_id'], '❌ 权限更新失败。\n' + str(response_json))
                return
        except Exception as e:
            send_group_msg(data['group_id'], '❌ 命令出现错误。\n' + str(e))
            return
