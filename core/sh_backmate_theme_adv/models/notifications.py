# Copyright (C) Softhealer Technologies.
from odoo import fields, models, _, api
# import html2text

class Annoucement(models.Model):
    _name = 'sh.announcement'

    name = fields.Char("Name")
    description = fields.Html("Description",translate=True)
    active = fields.Boolean("Active",default=True)
    user_ids = fields.Many2many('res.users',string="Users")
    font_color = fields.Char("Font Color")
    background_color = fields.Char("Background Color")
    date = fields.Date("Creation Date",default=fields.Date.today())
    is_animation = fields.Boolean("Enable Animation ?")
    direction = fields.Selection([('right','Left to Right'),('left','Right To Left')],string="Direction",default='right')
    simple_text = fields.Boolean("Want Simple Text ?")
    description_text = fields.Text("Description")
    font_size = fields.Integer("Font Size", default=12)
    padding = fields.Float("Padding", default=5)
    font_family = fields.Selection([
        ('Roboto','Roboto'),
        ('monospace','Monospace'),
        ('serif','Serif'),
        ('sans-serif','Sans-serif'),
        ('fantasy','Fantasy'),
        ('emoji','Emoji'),
        ('math','Math')
        ],string = 'Body Font Family',default='Roboto')
    google_font_family = fields.Char(string = "Google Font Family")
    is_popup_notification = fields.Boolean("Popup Notification ?")
    notification_type = fields.Selection([('warning','Info'),('danger','Alert')], string="Notification Type",default='warning')
    
    @api.onchange('is_popup_notification')
    def _onchange_popup_notification(self):
        if self.is_popup_notification:
            self.simple_text = True
        else:
            self.simple_text = False
    
    def notify_user(self):
        notifications = []
        if self.user_ids:
            if self.simple_text:
                if self.notification_type == 'warning':
                    CODE_SOUND_SUCCESS = "SH_NOTIFICATION_SUCCESS_" 
                    for user in self.user_ids:
                        notifications.append([
                            (self._cr.dbname, 'res.partner', user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Notitification'), 'message': CODE_SOUND_SUCCESS + self.description_text, 'sticky': True, 'warning': True}  # sorted to make deterministic for tests
                        ])
                if self.notification_type == 'danger':
                    CODE_SOUND_FAIL = "SH_NOTIFICATION_FAIL_" 
                    for user in self.user_ids:
                        notifications.append([
                            (self._cr.dbname, 'res.partner', user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Notitification'), 'message': CODE_SOUND_FAIL + self.description_text, 'sticky': True, 'warning': False}  # sorted to make deterministic for tests
                        ])
#             else:
#                 for user in self.user_ids:
#                     notifications.append([
#                         (self._cr.dbname, 'res.partner', user.partner_id.id),
#                         {'type': 'simple_notification', 'title': _('Notitification'), 'message': html2text.html2text(self.description), 'sticky': True, 'warning': True}  # sorted to make deterministic for tests
#                     ])
                
        self.env['bus.bus'].sendmany(notifications)
