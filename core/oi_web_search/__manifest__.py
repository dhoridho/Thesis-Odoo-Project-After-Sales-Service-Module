{
    "name": "Advance Search",
    "summary": "Advanced Search, List View Search, List View Manager, Global Search, Quick Search, Listview Search, Search Engine, Advance Search, Advance Filter, Field Search, Advance Search Tree",
    "version": "1.1.1",
    "category": "Extra Tools",
    "website": "https://www.open-inside.com",
    "description": """
        
    """,
    "website": "https://www.open-inside.com",
    "author": "Openinside",
    "license": "OPL-1",
    "price" : 85,
    "currency": 'EUR',    
   
    "installable": True,
    "auto_install": True,
    # any module necessary for this one to work correctly
    "depends": [
       'web'
    ],

    # always loaded
    'data': [
       'views/assets_backend.xml'       
    ],
    'qweb' : [
        'static/src/xml/templates.xml'
        ],    
    'images' : [
        'static/description/cover.png'
        ],      
    'odoo-apps' : True 
}