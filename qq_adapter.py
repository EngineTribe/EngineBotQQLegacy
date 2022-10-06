from config import *
import requests
import rapidjson


def cqhttp_api(api: str, post_data: dict):
    response = requests.post(GO_CQHTTP_HOST + '/' + api, data=post_data)
    return response.json()


def send_group_msg(group_id, message: str):
    return cqhttp_api('send_msg', {'message_type': 'group', 'group_id': group_id, 'message': message})


def send_private_msg(user_id, message: str):
    return cqhttp_api('send_msg', {'message_type': 'private', 'user_id': user_id, 'message': message})


def send_group_forward_msg(group_id, messages: list[str], sender_name: str):
    nodes = []
    for message in messages:
        nodes.append({'type': 'node', 'data': {'name': sender_name, 'uin': BOT_USER_ID,
                                               'content': [{'type': 'text', 'data': {'text': message}}]}})
    return cqhttp_api('send_group_forward_msg',
                      {'message_type': 'group', 'group_id': group_id, 'messages': rapidjson.dumps(nodes)})


def delete_msg(message_id):
    return cqhttp_api('delete_msg', {'message_id': message_id})
