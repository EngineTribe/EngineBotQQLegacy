from config import *
from urllib.parse import quote
import requests


def send_msg(group_id: str, message: str):
    return cqhttp_api('send_msg', {'message_type': 'group', 'group_id': group_id, 'message': message})


def cqhttp_api(api: str, post_data: dict):
    response = requests.post(GO_CQHTTP_HOST + '/' + api, data=post_data)
    return response.json()
