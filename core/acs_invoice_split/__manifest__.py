# -*- coding: utf-8 -*-
#╔══════════════════════════════════════════════════════════════════════╗
#║                                                                      ║
#║                  ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                   ║
#║                  ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                   ║
#║                  ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                   ║
#║                  ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                   ║
#║                  ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                   ║
#║                  ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                   ║
#║                            ╔═╝║     ╔═╝║                             ║
#║                            ╚══╝     ╚══╝                             ║
#║                  SOFTWARE DEVELOPED AND SUPPORTED BY                 ║
#║                ALMIGHTY CONSULTING SOLUTIONS PVT. LTD.               ║
#║                      COPYRIGHT (C) 2016 - TODAY                      ║
#║                      https://www.almightycs.com                      ║
#║                                                                      ║
#╚══════════════════════════════════════════════════════════════════════╝
{
    'name': 'Invoice Splitting',
    'summary': """This Module will Add functionality of Invoice Splitting.""",
    'description': """
        This Module will Add functionality of Invoice Spliting of selected invoices of a customer. split invoice invoice spliting invoice split

        Ce module ajoutera la fonctionnalité de fractionnement des factures de factures sélectionnées d'un client. scission de facture scission de facture scission de facture

        Este módulo agregará la funcionalidad de la división de facturas de las facturas seleccionadas de un cliente. Factura dividida Factura dividida Factura dividida

        Deze module zal functionaliteit toevoegen voor het splitsen van facturen van geselecteerde facturen van een klant. splits factuurfacturering splitsfactuur splitsen
    """,
    'version': '1.0.4',
    'category': 'Accounting',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    'depends': ["account"],
    'data' : [
        'security/ir.model.access.csv',
        'wizard/split_wizard_view.xml',
        'views/account_view.xml',
    ],
    'images': [
        'static/description/acs_split_invoice_almightycs_cover.jpg',
    ],
    'installable': True,
    'sequence': 1,
    'price': 36,
    'currency': 'EUR',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: