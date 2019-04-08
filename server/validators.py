login_schema = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'email': {
            'type': 'string',
            'format': 'email'
        },
        'password': {
            'type': 'string'
        },
    },
    'required': ['email', 'password']
}

signup_schema = {
    'type':
    'object',
    'additionalProperties':
    False,
    'properties': {
        'firstName': {
            'type': 'string',
        },
        'lastName': {
            'type': 'string',
        },
        'email': {
            'type': 'string',
            'format': 'email'
        },
        'phone': {
            'type': 'string',
        },
        'plastaId': {
            'type': 'string',
        },
        'password': {
            'type': 'string'
        },
        'birthDate': {
            'type': 'string',
            'format': 'date'
        },
    },
    'required': [
        'firstName', 'lastName', 'phone', 'plastaId', 'password', 'email', 'birthDate',
    ]
}