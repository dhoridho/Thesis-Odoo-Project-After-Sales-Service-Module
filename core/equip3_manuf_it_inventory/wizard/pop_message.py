# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.translate import _


class PopMessage(models.TransientModel):
    _name = 'ceisa.pop.message'
    _description = 'Pop Message'

    name = fields.Char('Message')
    info = fields.Html('Detail')

    @api.model
    def message(self, name, html=''):
        return {
            'name': _('Message'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'ceisa.pop.message',
            'target': 'new',
            'context': dict(default_name=name, default_info=html)
        }
