# -*- coding: utf-8 -*-
from odoo import models, fields


class WarningWizard(models.TransientModel):
    _name = 'warning.wizard'
    _description = 'Warning Wizard'

    message = fields.Char("Warning!")

    def show_message(self, message):
        self.message = message
        return {
            'name': 'Warning Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'warning.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'res_id': self.id,
        }