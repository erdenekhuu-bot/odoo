{
    'name': 'Gmobile Incoming Reply Log',
    'version': '18.0.1.0.0',
    'category': 'Mail',
    'summary': 'Logs inbound replies to alert@gmobile.mn as records',
    'depends': ['mail','web','mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
        'views/incoming_reply_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gmobile_incoming_reply/static/src/js/login_alert.js'
        ]
    },
    'installable': True,
    'application': False,
}