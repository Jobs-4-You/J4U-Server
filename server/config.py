import os

dev = {
    'url': 'http://127.0.0.1:5000',
    'app_url': 'http://127.0.0.1:8080',
    'host': '0.0.0.0',
    'port': 5000
}

prod = {
    'url': 'https://j4u.uni.ch:5000',
    'app_url': 'https://j4u.uni.ch',
    'host': '127.0.0.1',
    'port': 3000
}


def get_config():
    if os.environ.get('ENV') == 'prod':
        return prod
    else:
        return dev