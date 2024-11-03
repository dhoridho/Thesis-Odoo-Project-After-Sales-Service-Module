# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
	"name" : "All in one Loyalty - Website and POS Rewards Redeem Program",
	"version" : "1.1.1",
	"category" : "eCommerce",
	"depends" : ['base','sale_management','point_of_sale','website','website_sale','delivery','website_sale_delivery'],
	"author": "BrowseInfo",
	'summary': 'Website Loyalty rewards pos loyalty rewards pos club membership website Loyalty Program eCommerce Loyalty Program pos customer loyalty webshop Loyalty and Rewards Program pos Bonus Gift website Referral website rewards pos rewards pos redeem website redeem',
	"description": """
	
	All in one Loyalty and Rewards Program in Odoo,
	sale loyalty and rewarads program in odoo,
	website loyalty and rewarads program in odoo,
	pos loyalty and rewarads program in odoo,
	redeem and reward loyalty points in odoo,
	loyalty points in sale, website and POS,
	discounts or loyalty in sale, website and POS,
	
	""",
	"website" : "https://www.browseinfo.in",
	"price": 89,
	"currency": "EUR",
	"data": [
		'security/ir.model.access.csv',
		'wizards/reedem_loyalty.xml',
		'views/template.xml',
		'views/loyalty_view.xml',
		
	],
	'qweb': [
		'static/src/xml/pos.xml',
	],
	"auto_install": False,
	"installable": True,
	"images":['static/description/Banner.png'],
	"live_test_url":'https://youtu.be/zbGWw76IRGU',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
