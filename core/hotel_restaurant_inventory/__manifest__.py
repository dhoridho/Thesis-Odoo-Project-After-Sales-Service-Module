# -*- encoding: utf-8 -*-

{
    "name" : "Hotel Restaurant Inventory ",
    "version" : "1.2",
    "author" : "Pragmatic TechSoft Pvt Ltd",
    "category" : "Generic Modules/Hotel Restaurant Inventory",
    "description": """
    Module for Add Concept of BOM to restaurant Module:
    * Configure Property
    * Hotel Configuration
    * Product Quantity maintainance
   
    """,
    "depends" : ["hotel_management","mrp"],
    "init_xml" : [
                  ],
    "demo_xml" : [
    ],
    "data" : [
            "views/hotel_restaurant_inventory_view.xml",
            "security/ir.model.access.csv",
    ],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
