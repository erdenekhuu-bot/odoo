{
    'name': "Жишээ",

    'summary': "Энгийн жишээ модул",

    'description': 'Туршилтаар ашиглах модул бүх үйлдэлүүдийг хийдэг',
    'license': 'GPL-3',
    'author': "Gmobile",
    'website': "https://gmobile.mn",
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base','mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/menu.xml',
        'demo/demo.xml',
        'views/templates.xml',
    ],
    'assets':{
        'web.assets_backend':[
            'jishee/static/src/css/regular.css'
        ]
    },
    'qweb': [
        'views/templates.xml',
    ],
    'installable': True
}

