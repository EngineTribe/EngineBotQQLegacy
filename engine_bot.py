# This file contains almost everything of Engine-bot except the web server and QQ-specific content

from qq_adapter import *


def command_help(data):
    send_msg(data['group_id'], '''📑 可用的命令:
e!help : 查看此帮助。''')
