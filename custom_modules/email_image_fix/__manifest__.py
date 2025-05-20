{
    'name': 'Email Image URL Fix',
    'version': '1.0',
    'summary': 'Automatically fixes broken images in emails',
    'description': """
        Forces HTTPS and correct domain for all email images.
        Solves Gmail's mixed-content blocking issue.
    """,
    'author': 'Your Name',
    'depends': ['mail', 'web'],
    'data': [
        'data/system_parameters.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}