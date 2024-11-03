# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo Rental Management for Machine,Product and Equipements',
    'summary': 'Rental product rental service rent product rent car rent machine rental machine rent Hire machinery Equipment Rental management machine rental real estate rental sales service Equipment rental property rent service rental Equipment Machinery rental service',
    'category': 'Sales',
    "version": "1.1.7",
    'description': """
This module use for Rental management system
Equipment Rental management
Rental agency
property rental
property lease
lease items
Odoo Rental Sale
Rental Sale
rental management system
rental orders
rental contract
rental contracts
lease contracts
car lease 
vehicle lease
product lease
leasing 
lease management
Rental Management for Product/Item/Equipment/Vehicle
Product Rental Management
Vehicle rental management
product lease management
vehicle rental management
Rental management
car rental management
lease sale
Odoo Rental Sale
Rental Sale
rental management system
Equipment hire agency
hire agency
fleet rental management
Tenant Management
Property Lease/Tenant Management
Property Lease Management
hire equipements

hire agency
rental hire management  . It helps user to manage orders for rent car, rent house, rent product.Anything you can rent based on this module. Car Rent, House Rent, Product Rent can be done by this rental management system.
product rent, machine rent, car rent,house rent, fleet rent. Service Rent,Product Rent,Vehical Rent, Car Rent, Machine rental system
hire for rent Hire Equipment and Machinery rental  Equipment hire industry  , 
Este módulo usa o sistema de gerenciamento de locação. Ajuda o usuário a gerenciar pedidos de aluguel de carros, aluguel de casa, aluguel de produtos. Tudo o que você pode alugar com base neste módulo. Aluguel de carro, aluguel de casa, aluguel de produto pode ser feito por este sistema de gerenciamento de aluguel.
aluguel de produtos, aluguel de máquinas, aluguel de carros, aluguel de casas, aluguel de frotas. Aluguel de Serviços, Aluguel de Produtos, Aluguel Vehical, Aluguel de Carros, Sistema de aluguel de máquinas
alugar para alugarتستخدم هذه الوحدة لنظام إدارة التأجير. يساعد المستخدم على إدارة طلبات تأجير السيارات ، استئجار منزل ، تأجير المنتج. أي شيء يمكنك استئجاره بناء على هذه الوحدة. تأجير السيارات ، استئجار منزل ، يمكن أن يتم استئجار المنتج عن طريق نظام إدارة الإيجارات هذا.
تأجير المنتجات ، تأجير الآلات ، تأجير السيارات ، استئجار منزل ، تأجير أسطول. خدمة تأجير ، إيجار المنتجات ، تأجير vehical ، تأجير السيارات ، نظام تأجير الجهاز
استئجار للإيجار
tustakhdam hadhih alwahdat linizam 'iidarat altaajiri. yusaeid almustakhdam ealaa 'iidarat talabat tajir alsayarat , aistijar manzil , tajir almntj. 'ay shay' yumkinuk aistijaruh bina'an ealaa hadhih alwahdati. tajir alsayarat , aistijar manzil , ymkn 'an yatima aistijar almuntaj ean tariq nizam 'iidarat al'iijarat hadha.
tajir almuntajat , tajir alalat , tajir alsayarat , aistijar manzil , tajir 'ustul. khidmat tajir , 'iijar almuntajat , tajir vehical , tajir alsayarat , nizam tajir aljihaz
aistijar lil'iijarEste uso del módulo para el sistema de gestión de alquiler. Ayuda al usuario a gestionar pedidos de alquiler de automóvil, alquiler de casa, alquiler de producto. Todo lo que puede alquilar se basa en este módulo. Alquiler de autos, alquiler de casas, alquiler de productos se puede hacer con este sistema de administración de alquileres.
alquiler de productos, alquiler de máquinas, alquiler de automóviles, alquiler de viviendas, alquiler de flota. Alquiler de servicios, alquiler de productos, alquiler de vehículos, alquiler de automóviles, sistema de alquiler de maquinaria
alquilar en alquilerCe module est utilisé pour le système de gestion de location. Il aide l'utilisateur à gérer les commandes de location de voiture, louer une maison, louer un produit. Tout ce que vous pouvez louer en fonction de ce module. Car Rent, House Rent, Product Rent peut être fait par ce système de gestion locative.
location de produits, location de machines, location de voitures, location de maisons, location de véhicules. Service Rent, Location de produits, Location Vehical, Location de voitures, Location de machines
location à louer
Dieses Modul wird für das Rental-Management-System verwendet. Es hilft Benutzern, Aufträge für Mietwagen zu verwalten, Haus zu mieten, Produkt zu mieten. Alles, was Sie mieten können, basiert auf diesem Modul. Autovermietung, Hausmiete, Produktmiete kann mit diesem Mietverwaltungssystem durchgeführt werden.
Produktmiete, Maschinenmiete, Autovermietung, Hausmiete, Flottenmiete. Service-Miete, Produkt-Miete, Vehicle Rent, Autovermietung, Maschinen-Verleih-System
Miete für Miete
Deze module gebruikt voor verhuurbeheersysteem. Het helpt de gebruiker om bestellingen voor huurauto's, huurwoningen, huurproducten te beheren. Alles wat u op basis van deze module kunt huren. Car Rent, House Rent, Product Rent kan worden gedaan door dit verhuurbeheersysteem.
producthuur, machineverhuur, autohuur, huishuur, vloothuur. Servicehuur, producthuur, voertuigenverhuur, autoverhuur, machineverhuursysteem
huur te huur

==========================================
    """,
    'website': 'https://www.browseinfo.in',
    'live_test_url':'https://youtu.be/3Feb4HZ_dkU',
    'author': 'BrowseInfo',
    'price': 69.00,
    'currency': "EUR",
    'application': True,
    'installable': True,
    'depends': ['base','product', 'sale','stock','sales_team','account','sale_management','purchase'],#subscription,account_accountant
    'data': [
             'security/ir.model.access.csv',
            'data/mail_template.xml',
             'data/rental_sequence.xml',
             'data/cron.xml',
             'wizard/replace_product_wizard_view.xml',
			 'views/rental_view.xml',
			 'views/rental_product_view.xml',
			 'views/rental_menu_view.xml',
            'views/rental_setting_view.xml',
        'views/rental_report.xml',
        'views/rental_report_templates.xml',
        'views/account_invoice_report_view.xml'
    ],
    "images":['static/description/Banner.png'],
}
