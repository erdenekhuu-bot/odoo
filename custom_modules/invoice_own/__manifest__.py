{
    'name': 'Invoice Own',
    'version': '1.0',
    'category': 'Invoice',
    'description': """ Generate pdf invoice automatically. """,
    'author': 'erdenekhuu.e',
    'depends': ['base', 'web', 'website','mass_mailing'],
    'assets':{
        'web.assets_frontend':[
            'invoice_own/static/src/css/style.css',
        ]
    },
    'data':[
        'views/pdf_template.xml',
        'views/pdf_attachment.xml',
        'views/menu.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': True,
}