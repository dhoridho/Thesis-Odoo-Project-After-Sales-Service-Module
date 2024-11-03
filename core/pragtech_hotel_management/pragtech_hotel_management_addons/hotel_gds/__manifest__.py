# -*- encoding: utf-8 -*-

{
    "name" : "Hotel Management GDS",
    "version" : "1.2",
    "author" : "Pragmatic TechSoft Pvt Ltd",
    'website' : 'http://pragtech.co.in/',
    "category" : "Generic Modules/Hotel Management GDS",
    "description": """
    Module for Hotel/Resort/Property management. You can manage:
    * GDS Property

    Different reports are also provided, mainly for hotel statistics.
    """,
    "depends" : ["hotel_management",'banquet_managment'],
    "init_xml" : [],
    "demo_xml" : [
    ],
    "data" : [
                    "view/hotel_gds_view.xml",
                    'security/ir.model.access.csv',
    ],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
