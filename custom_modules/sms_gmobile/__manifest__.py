{
    'name': 'Gmobile SMS',
    'version': '1.0',
    'sequence': 3,
    'category': 'Marketing',
    'description': """ SMS mass""",
    'summary': 'SMS broadcasting to customers',
    'depends': ['base','web','website','sms','mass_mailing_sms','sms'],
    'author': 'erdenekhuu.e',
    'data': [
        'views/view.xml',
    ],
    'installable': True,
    'application': True,
}