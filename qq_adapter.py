from config import *
import requests


def send_group_msg(group_id: str, message: str):
    return cqhttp_api('send_msg', {'message_type': 'group', 'group_id': group_id, 'message': message})


def send_private_msg(user_id: str, message: str):
    return cqhttp_api('send_msg', {'message_type': 'private', 'user_id': user_id, 'message': message})


def delete_msg(message_id: str):
    return cqhttp_api('delete_msg', {'message_id': message_id})


def cqhttp_api(api: str, post_data: dict):
    response = requests.post(GO_CQHTTP_HOST + '/' + api, data=post_data)
    return response.json()
