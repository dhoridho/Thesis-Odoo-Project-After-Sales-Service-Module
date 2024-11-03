# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name' : "Merge Delivery Orders/Incoming Shipments in odoo",
    'version' : "1.1.2",
    'author' : "BrowseInfo",
    'description' : '''
    This modules gives facility to merge the picking(delivery orders / receipts).
	odoo Merge Picking list Merge Delivery Orders Merge Incoming shipments Merge Receipts Merge orders Merge 
    odoo merge Delivery Orders/Incoming Shipments in odoo merge shipment merge pickings merge combine orders
    hashmicro.combine picking order combine delivery order combine combine incoming shipment combine
	odoo merge transfer merge shipment delivery merger shipment merger picking merger
    odoo merge operations merge internal transfer in odoo
	odoo merge DO receipt merger merge multiple picking merge multiple delivery merge multiple shipment
    odoo merge warhouse picking merge stock picking merge stock movement
    odoo merge stock picking merge stock picking merger stock picking combine stock picking combine
    odoo merge stock operation merge stock operation merger stock operation combine stock operation combine
    odoo merge operations merge operations merger operations combine operations combine merge DO merge
    odoo merge delivery order merge delivery order merger delivery order combine delivery order combine
    odoo merge receipt merge receipt merger receipt combine receipt combine
    odoo merge picking merge picking merger picking combine picking combine
Fusionner la liste de prélèvement, fusionner les commandes de livraison, fusionner les envois entrants, fusionner les reçus. Fusionner les commandesfusionner le transfert, fusionner l'expédition, fusionner les livraisons, fusionner les expéditions, choisir la fusion, fusionner les opérations, fusionner le transfert internefusionner DO, réception fusion, fusionner plusieurs picking, fusionner plusieurs livraisons, fusionner plusieurs envois, fusionner picking warhouse, fusionner picking stock, fusionner stock mouvement

Combinar lista de picking, fusionar pedidos de entrega, combinar envíos entrantes, combinar recibos. Fusionar pedidos
fusión de transferencia, combinación de envío, fusión de entrega, fusión de envío, fusión de picking, fusión de operaciones, combinación de transferencia interna
fusionar DO, fusionar recibos, fusionar selección múltiple, fusionar entregas múltiples, fusionar envíos múltiples, fusionar picking de warhouse, combinar stock picking, fusionar stock de movimientos
    ''',
    'category' : "Warehouse",
    'price': 24,
    'currency': "EUR",
    "website" : "https://www.browseinfo.in",
    'summary': 'merge picking merge delivery order merge receipts merge merge stock picking Merge Picking list merge shipments Merge orders combine picking merge transfer merge internal transfer picking merger merge operations merge multiple delivery merge DO merger',
    'depends' : ['sale_management','stock', 'product','sale_stock','purchase'],
    'data': [
			 'security/ir.model.access.csv',
             'wizard/merge_picking_view.xml',
             ],
    'website': 'http://www.browseinfo.in',
    'live_test_url':'https://youtu.be/psFkkkBi1ZU',
    'installable': True,
    'auto_install': False,
	"images":['static/description/Banner.png'],
}
