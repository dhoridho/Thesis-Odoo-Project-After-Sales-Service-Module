{
    'name': 'Equip3 Open Weather',
    'version': '1.1.3',
    'category': 'Systray',
    'author': 'Hashmicro / Rajib',
    'website': 'http://www.hashmicro.com',
    'sequence': 10,
    'depends': ['web'],
    'summary': """
        Weather Information using OpenWeather API.
    """,
    'data': [
        'security/ir.model.access.csv',
        'data/open_weather_data.xml',
        'views/assets.xml',
        'views/res_config_settings_views.xml'
    ],
    'qweb': [
        'static/src/xml/open_weather.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
