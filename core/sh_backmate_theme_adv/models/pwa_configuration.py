# Part of Softhealer Technologies.
from odoo import api, fields, models, _

mime_selection = [('image/png', 'image/png'), ('image/x-icon',
                                               'image/x-icon'), ('image/gif', 'image/gif')]
display_selection = [('fullscreen', 'Fullscreen'),
                     ('standalone', 'Standalone'), ('minimal-ui', 'Minimal')]
orientation_selection = [('landscape', 'Always Landscape')]


class PWAConfig(models.Model):
    _name = 'sh.pwa.config'
    _description = 'PWA Configuration'

    name = fields.Char(required=True, default='HashMicro')
    short_name = fields.Char(required=True, default='HashMicro')
    theme_color = fields.Char(default='#DBDCDE')
    background_color = fields.Char(default='#3367D6')
    display = fields.Selection(
        selection=display_selection, default='fullscreen', required=True)
    orientation = fields.Selection(selection=orientation_selection)
    icon_small = fields.Binary(
        help='Set a small app icon. Must be at least 32x32 pixels')
    icon_small_mimetype = fields.Selection(
        selection=mime_selection, help='Set the mimetype of your small icon.')
    icon_small_size = fields.Char(default='32x32')
    icon = fields.Binary(
        help='Set a big app icon. Must be at least 512x512 pixels')
    icon_mimetype = fields.Selection(
        selection=mime_selection, help='Set the mimetype of your icon.')
    icon_size = fields.Char(default='512x512')
    company_id = fields.Many2one(
        'res.company', string="Company", default=lambda self: self.env.user.company_id.id)
    icon_iphone = fields.Binary(help='Icon for Iphone',string="Icon for Iphone")