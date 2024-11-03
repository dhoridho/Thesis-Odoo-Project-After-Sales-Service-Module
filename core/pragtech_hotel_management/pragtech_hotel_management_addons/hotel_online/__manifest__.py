# -*- coding: utf-8 -*-

{
    'name': 'Website Product',
    'category': 'Website',
    'summary': 'Book Hotel Rooms Online',
    'website': 'https://www.hashmicro.com/page/website-builder',
    'version': '1.23',
    'author': 'Pragmatic TechSoft Pvt Ltd',
    'depends': ['web', 'website', 'website_sale_coupon', 'hotel_management', 'payment', 'website_sale', 'portal'],
    'description': """
        Book Rooms Online
         
        hotel_online Module used for select and book the hotel rooms online.\n
        It also allow user to pay the bill online

    """,
    'data': [

            'views/website_event_search.xml',
            'views/website_book_room.xml',
            'views/hotel_reservation.xml',
            'views/website_home.xml',
            'views/coupon_program.xml',
            'static/src/data/website_menu.xml',
    ],
    'demo': [

    ],
    'installable': True,
}
