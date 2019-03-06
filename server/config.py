import os

dev = {
    'url': 'http://127.0.0.1:5000',
    'app_url': 'http://127.0.0.1:8080',
    'host': '0.0.0.0',
    'port': 5000
}

prod = {
    'url': 'https://j4u.unil.ch:5000',
    'app_url': 'https://j4u.unil.ch',
    'host': '127.0.0.1',
    'port': 3000
}


def get_config():
    if os.environ.get('ENV') == 'prod':
        conf =  prod
    else:
        conf = dev

    conf['email_user'] = os.environ.get('MAIL_USER')
    conf['email_pwd'] = os.environ.get('MAIL_PWD')
    conf['app_key'] = os.environ.get('APP_KEY')
    conf['salt'] = os.environ.get('SALT')
    conf['jwt_key'] = os.environ.get('JWT_KEY')

    return conf