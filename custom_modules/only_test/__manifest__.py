{
    'name': 'Only Test Module',
    'version': '1.0',
    'summary': '',
    'description': "",
    'depends': ['mail', 'web'],
    'data': [
        'data/system_parameters.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}