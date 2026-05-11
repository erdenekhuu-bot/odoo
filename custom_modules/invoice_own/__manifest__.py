{
    'name': 'Invoice Own',
    'version': '1.0',
    'category': 'Invoice',
    'description': """ Generate pdf invoice automatically. """,
    'depends': ['mailing.mailing','link.tracker','res.partner'],
    'data': [
        'views/list.xml',
        'views/menu.xml'
    ],
    'author': 'erdenekhuu.e',
    'installable': True,
    'application': True,
}