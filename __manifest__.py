# -*- coding: utf-8 -*-
{
    'name': 'GES Website',
    'summary': 'Website corporativo da General Express Service',
    'description': """
Website institucional da General Express Service, com apresentação da empresa,
soluções, projectos, notícias e pedido de cotação.
    """,
    'author': 'General Express Service',
    'website': 'https://www.generalexpress.co.mz',
    'category': 'Website/Website',
    'version': '15.0.8.0.0',
    'license': 'LGPL-3',
    'depends': ['website', 'portal', 'sale_management', 'mail', 'auth_signup'],
    'data': [
        'security/ges_portal_security.xml',
        'security/ir.model.access.csv',
        'data/ges_portal_data.xml',
        'views/ges_portal_backend_views.xml',
        'views/ges_portal_templates.xml',
        'views/templates.xml',
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'js_website_ges/static/src/scss/ges_website.scss',
            'js_website_ges/static/src/js/ges_website.js',
        ],
    },
    'application': True,
    'installable': True,
}
