import os
import json
defaultSetting = {
    'username': 'admin',
    'password': 'passwd',
    'listen': '0.0.0.0',
    'port': 5000,
}

hostSettingMap = {
    'hust.edu.cn': {
        'host': 'mail.hust.edu.cn',
        'port': 25,
        'mails_per_send': 50,
        'mails_per_login': 300,
        'interval_between_login': 2,
        'reset_per_n_login': 4,
        'reset_interval': 5,
    },
}


def getHostSetting(addr):
    host = addr.split('@')[-1]
    return hostSettingMap[host]


if not os.path.exists('setting.json'):
    with open('setting.json', 'w') as fp:
        json.dump(defaultSetting, fp)

with open('setting.json', 'r') as fp:
    setting = json.load(fp)
