# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
	'name':"Scrap Order Backdate and Remarks in Odoo",
	'version':'14.0.0.1',
	'category':'Warehouse',
	'summary':'Scrap transfer backdate scrap backdate inventory scrap transfer backdating scrap backdate remarks scrap accounting backdate transfer backdate scrap operation backdate inventory backdate stock back-date scrap transfer stock backdate scrap order backdate',
	'description':"""

    You can set a scrap Backdate and Remarks in stock move product move and account move in one click.
    Odoo scrap order Backdate and Remarks
     odoo scrap transfer backdating stock scrap backdating scrap transfer backdating
     odoo scrap backdating scrap order transfer backdating
     odoo scrap backdate scrap order Backdate scrap order transfer Backdate
     odoo scrap backdating option scrap backdating options scrap Backdate Operations
     odoo scrap Backdate Options backdating options scrap Backdate Operations Backdate Operations
     odoo scrap backdate operations scrap stock backdate operations
     odoo scrap order backdate odoo scrap order remarks scrap transfer remarks warehouse scrap order remarks scrap remarks
     odoo scrap remarks odoo scrap backdate remarks
     odoo scrap accounting backdate transfer backdate on scrap odoo


     odoo scrap order back dating scrap order transfers back dating scrap order stock transfer back dating
     odoo scrap order transfer back dating inventory scrap order back dating odoo
     odoo scrap order back date scrap order Back-date scrap order Transfers Back date
     odoo scrap order back-dating option scrap order back dating options Inventory Back date Operations
     odoo Back-date Options back dating options Inventory Back date Operations Back date Operations
     odoo warehouse back date operations warehouse scrap order back date operations
     odoo scrap order back date odoo scrap order remarks transfer remarks warehouse scrap order remarks warehouse remarks
     odoo inventory remarks odoo scrap order back date remarks
     odoo scrap order accounting back date transfer back date on inventory odoo
    
    
    
     entries so to avoid the problem this app will help to put custom back date and remarks.
     Custom back date will be transfer to stock entries and accounting entries

      odoo stock transfer backdating stock transfers backdating inventory stock transfer backdating
     odoo inventory transfer backdating inventory transfer backdating
     odoo stock backdate Stock Transfers Backdate inventory Transfers Backdate
     odoo inventory backdating option stock backdating options Inventory Backdate Operations
     odoo Backdate Options backdating options Inventory Backdate Operations Backdate Operations
     odoo warehouse backdate operations warehouse stock backdate operations
     odoo stock backdate odoo stock remarks transfer remarks warehouse delivery remarks warehouse remarks
     odoo inventory remarks odoo stock backdate remarks
     odoo stock accounting backdate transfer backdate on stock odoo


     odoo stock transfer back dating stock transfers back dating inventory stock transfer back dating
     odoo inventory transfer back dating inventory transfer back dating odoo
     odoo stock back date Stock Transfers Back-date inventory Transfers Back date
     odoo inventory back-dating option stock back dating options Inventory Back date Operations
     odoo Back-date Options back dating options Inventory Back date Operations Back date Operations
     odoo warehouse back date operations warehouse stock back date operations
     odoo stock back date odoo stock remarks transfer remarks warehouse delivery remarks warehouse remarks
     odoo inventory remarks odoo stock back date remarks
     odoo stock accounting back date transfer back date on inventory odoo
    
    
    
     entries so to avoid the problem this app will help to put custom back date and remarks.
     Custom back date will be transfer to stock entries and accounting entries

	""",
	'author':"BrowseInfo",
    'website': 'https://www.browseinfo.in',
    'currency': 'EUR',
    'price': 25, 
    'depends':['base','stock','account'],
	'data':[ 'security/ir.model.access.csv',
			'wizard/wizard_scrap_order.xml',
			'views/inherit_scrap_order_backdate.xml'],
    'qweb': [
    ],
    "auto_install": False,
    "installable": True,
	'live_test_url': 'https://youtu.be/7HKR_o8Lq2c',
	"images": ['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
