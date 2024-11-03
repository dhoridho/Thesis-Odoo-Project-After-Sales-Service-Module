{
    'name': 'Date Year Widget',
    'version': '1.1.3',
    'category': 'Widget',
    'author': 'Hashmicro',
    'website': 'http://www.hashmicro.com',
    'sequence': 10,
    'depends': ['web'],
    'summary': """
        Feature:
        - Year widget for list view and form view,

        How to use:
        - Adding widget="year" attribute for your Date/Datetime field on view
        Ex:
        <field name="your_date_field" widget="date_year"/> for Date field or
        <field name="your_datetime_field" widget="datetime_year"/> for Datetime field
    """,
    'data': [
        'views/date_year_views.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
