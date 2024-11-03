# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Backmate Backend Theme Advance",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "description": """
                Are you bored with your standard odoo backend theme? Are You are looking for modern, creative, clean, clear, materialize Odoo theme for your backend? So you are at right place, We have made sure that this theme is highly customizable and it comes with a premium look and feel. Our theme is not only beautifully designed but also fully functional, flexible, fast, lightweight, animated and modern multipurpose theme. Our backend theme is suitable for almost every purpose.
                """,
    "summary": "Advance Material Backend Theme, Responsive Theme, Fully functional Theme, flexible Backend Theme, fast Backend Theme, lightweight Backend Theme, Animated Backend Theme, Modern multipurpose theme, Customizable Backend Theme, Multi Tab Backend Theme Odoo",
    "category": "Theme/Backend",
    "version": "1.1.9",
    "depends":
    [
        "web", "mail", "app_odoo_customize"
    ],

    "data":
    [
        "security/base_security.xml",
        "security/ir.model.access.csv",
        "data/theme_config_data.xml",
        "data/pwa_configuraion_data.xml",
        "views/assets.xml",
        "views/login_layout.xml",
        "views/back_theme_config_view.xml",
        "views/assets_backend.xml",
        #          "wizard/theme_preview_wizard.xml",
        "views/res_config_settings.xml",
        "views/base_view.xml",
        "views/global_search_view.xml",
        "views/pwa_configuration_view.xml",
        "views/views.xml",
        "views/notifications_view.xml",
        "views/send_notifications.xml",
        "views/web_push_notification.xml",
    ],

    "qweb":
    [
        "static/src/xml/web_quick_menu.xml",
        "static/src/xml/global_search.xml",
        "static/src/xml/sh_thread.xml",
        "static/src/xml/menu.xml",
        "static/src/xml/navbar.xml",
        "static/src/xml/form_view.xml",
        "static/src/xml/theme_config.xml",
        "static/src/xml/base.xml",
    ],
    'images': [
        'static/description/splash-screen.png',
        'static/description/splash-screen_screenshot.gif'
    ],
    "live_test_url": "https://softhealer.com/contact_us",
    "installable": True,
    "auto_install" : True,
    "application": True,
    "price": 125,
    "currency": "EUR",
    "bootstrap": True,
}
