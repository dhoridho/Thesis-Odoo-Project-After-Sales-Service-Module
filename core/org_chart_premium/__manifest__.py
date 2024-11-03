# -*- coding: utf-8 -*-
{
	'name': "Organization Chart Premium",
	'summary': """Employee Hierarchy - Multi Company - Drag and Drop - Search - Add - Edit - Delete - Screenshot - Horizontal - Vertical""",
	'description': """Dynamic Display of your Employee Hierarchy""",
	'author': "SLife Organization, Amichia Fréjus Arnaud AKA",
	"website": "https://slifeorganization.com",
	'category': 'Human Resources',
	'version': '1.1.6',
	'license': 'OPL-1',
	'depends': ['base', 'hr',],
	'price': 25.00,
	'currency': 'EUR',
	'support': 'frejusarnaud@gmail.com',
	'data': [
		'data/slife_org_chart_data.xml',
		'security/ir.model.access.csv',
		'views/org_chart_views.xml',
	],
	'images': [
		'static/src/img/main_screenshot.png'
	],
	'qweb': [
        "static/src/xml/org_chart_employee.xml",
    ],
	'installable': True,
	'application': True,
	'auto_install': False,
}
