# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Sales Commission Based On Target | Sales commission Based On Fix Amount | Sales Commission Based On Percentage | Sales commission Based On Sales Amount",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Sales",
    "license": "OPL-1",
    "summary": "Sales Target commission,Sales Commission With Target,SalesPerson Commision With Target,Sales Person Commision,Sales Men Commision With Target,Salesmen Commision,Sales Team Commision With Target,Salesteam Commision On Collection Amount Odoo",
    "description": """Want to provide commission to salesman/salesperson for specific product & product categories? The "Sales Commission Based On Target "module allows you to pay sales commission based on the targets you set for each salesperson. In the target-based commission method, the salesman is provided with a range of targets after achieving those ranges the salesman entitled for the commission set up by the company. You can set the commission based on the product or product category. You can apply target on the amount as well as on a quantity basis. You can calculate the commission in 2 ways,
1) Based On Amount: That means commission calculate based on fixed amount.
2) Based On Percentage: Here the commission calculated based on the 2 factors,
A) Percentage On Sales Amount: The commission will be calculated based on the percentage of sales amount.
B) Percentage On Collection Amount: The commission will be calculated based on the percentage of the collection amount.""",
    "version": "14.0.1",
    "depends": ["sale_management"],
    "application": True,
    "data": [
        
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/account_move.xml',
        'views/target_commision.xml',
    ],
    "qweb": [
        "static/src/xml/*.xml",
    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "price": 70,
    "currency": "EUR"
}
