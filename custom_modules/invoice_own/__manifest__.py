{
    'name': 'Invoice Own',
    'version': '1.0',
    'category': 'Invoice',
    'description': """ Generate pdf invoice automatically. """,
    'author': 'erdenekhuu.e',
    'images': [
        'static/src/img/appstoreqr.png',
        'static/src/img/logo.png',
        'static/src/img/playstoreqr.png',
        'static/src/img/whitescreen.png',
        'static/src/img/whitescreen2.png',
        'static/src/img/whitescreen3.png',
    ],
    'depends': ['base', 'web', 'website'],
    'assets':{
        'web.assets_frontend':[
            'invoice_own/static/src/css/style.css',
        ]
    },
    'data':[
        'views/pdf_template.xml',
    ],
    'installable': True,
    'application': True,
}