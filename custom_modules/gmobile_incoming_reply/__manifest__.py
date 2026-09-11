{
    'name': 'Gmobile Incoming Reply Log',
    'version': '18.0.1.0.0',
    'category': 'Mail',
    'summary': 'Logs inbound replies to alert@gmobile.mn as records',
    'depends': ['mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/incoming_reply_views.xml',
    ],
    'installable': True,
    'application': False,
}