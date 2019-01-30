import os

dev = {
    'url': 'http://127.0.0.1:5000',
    'host': '0.0.0.0',
    'port': 5000
}

prod = {
    'host': 'https://j4u.uni.ch:3000',
    'host': '127.0.0.1',
    'port': 3000
}


def get_config():
    if os.environ.get('ENV') == 'prod':
        return prod
    else:
        return dev