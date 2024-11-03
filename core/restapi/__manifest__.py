# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Odoo REST API',
    'version': '1.3.5',
    'summary': 'The Odoo RESTful API that accesses Odoo using standard HTTP GET, PUT, POST, and DELETE methods and a simple JSON input and output format',
    'category': 'Tools',
    'description': """
The Odoo API is a RESTful web service and uses both the OAuth1 and OAuth2 protocols to authenticate 3rd party applications.

The Odoo REST API can be used for a variety of purposes such as:
================================================================

* Calling Methods to check access rights, list records, count records, read records, listing record fields, create, update and delete records
* Workflow Manipulations
* Report Printing and
* Inspection and Introspection

via endpoints.

Check out our http://odoo-restapi.readthedocs.io online docs for a quick reference guide to use the odoo REST API.
    """,
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'https://www.synconics.com',
    'depends': ['base', 'web', 'base_automation'],
    'external_dependencies': {
            'python': ['oauthlib']},
    'data': [
        'views/auth_view.xml',
        'views/restapi_cron.xml',
        'views/ir_models_view.xml',
        'security/ir.model.access.csv',
        'data/auth_data.xml',
        'data/mail_template.xml',
        'data/ir_cron.xml',
        'data/ir_config_parameter.xml'
    ],
    'demo': [],
    'css': [],
    'qweb': [],
    'js': [],
    'test': [],
    'images': [
        'static/description/main_screen.png',
    ],
    'price': 95,
    'currency': 'USD',
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
    'post_load': 'patch_json_response'
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
