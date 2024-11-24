# -*- coding: utf-8 -*-
{
    'name': "Modifier Theme Classic",
    'summary': """
        Theme Classic""",
    'description': """

    """,
    'author': "Ridho",
    'website': "",
    'category': 'Modifier',
    'version': '0.1',

    'depends': ['website_blog', 'website_sale_wishlist', 'website_sale_comparison'],
    "data": [
        'views/classic_store_config.xml',
        'data/classic_store_config_data.xml',
        'security/ir.model.access.csv',
        'views/layout.xml',
        'views/assets.xml',
        'views/footer.xml',
        'views/header.xml',
        'views/contact_us.xml',
        'views/blog.xml',
        'views/shop.xml',
        'views/shop_sidebar.xml',
        'views/404.xml',
        'views/product_view.xml',
        'views/product_view_inherits.xml',
        'views/snippets/about.xml',
        'views/snippets/banner.xml',
        'views/snippets/categories.xml',
        'views/snippets/listing.xml',
        'views/snippets/package.xml',
        'views/snippets/team.xml',
        'views/snippets/counter.xml',
        'views/snippets/sub_header.xml',
        'views/snippets/search.xml',
        'views/snippets/trending.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/theme_screenshot.png',
    ],

}
