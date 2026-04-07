{
    'name': 'Gmobile Invoice',
    'version': '1.0',
    'author': 'erdenee',
    'maintainer': 'erdenee',
    'category': 'Website',
    'description': "Зөвхөн нэхэмжлэл үүсгэх зориулалттай модул",
    'depends': ['account','web','mail'],
    'data': [
        'views/templates.xml',
        'views/menu.xml',
        'views/mail_templates.xml'
    ],
    'assets':{
        'web.assets_backend':[
            'gmobile/static/src/js/dashboard.js',
            'gmobile/static/src/xml/dashboard.xml',
            'gmobile/static/src/css/dashboard.css',
        ]
    },
    'license': 'GPL-3',
    'installable': True,
    'application': True
}