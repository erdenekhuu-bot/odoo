{
    'name': 'Business invoice',
    'version': '1.0',
    'category': 'Marketing',
    'description': """ Generate pdf invoice automatically. """,
    'author': 'erdenekhuu.e',
    'depends': ['base', 'web', 'website','mass_mailing'],
    'data':[
        'views/template/invoice_report.xml',
        'views/menu.xml',
        'security/ir.model.access.csv',
        'cron_job/task.xml',
        'views/groupview.xml',
    ],
    'installable': True,
    'application': True,
}