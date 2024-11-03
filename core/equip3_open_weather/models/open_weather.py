from odoo import models, fields


class OpenWeatherTheme(models.Model):
    _name = 'open.weather.theme'
    _description = 'Open Weather Theme'

    name = fields.Char(required=True)
    widget_ids = fields.One2many('open.weather.widget', 'theme_id', string='Widgets')


class OpenWeatherWidget(models.Model):
    _name = 'open.weather.widget'
    _description = 'Open Weather Widget'

    theme_id = fields.Many2one('open.weather.theme', string='Theme', required=True)
    name = fields.Char(required=True)
    oid = fields.Integer()
