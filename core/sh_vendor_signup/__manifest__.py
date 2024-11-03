# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Website Vendor Signup",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "license": "OPL-1",
    "category": "Website",
    "summary": "Vendor Registration Form,Marketplace Multi Step Vendor Signup,Odoo Vendor Portal,Website Vendor Registration Form,Website Portal for Vendor,Vendor Sign up Form,Web Vendor Form,Vendor Registration Form On Website Odoo",
    "description": """In this module, we have added a vendor sign up form on the website. So vendor can do registration/sign up from the website. The responsible persons get an email notification on the vendor sign up. We provide the option for a vendor to the auto-create portal user when signup.""",
    "version": "1.1.2",
    "depends": [
        "website",
        "purchase",
    ],
    "application": True,
    "data": [
        "views/assets_frontend.xml",
        "views/vendor_sign_up_template.xml",
        "views/res_partner_view_inherit.xml",
        "views/res_config_settings.xml",
        "data/vendor_sign_up_menu.xml",
        "data/mail_template.xml",
    ],
    "images": ["static/description/background.png", ],  
    "auto_install": False,
    "installable": True,
    "price": 40,
    "currency": "EUR",
}
