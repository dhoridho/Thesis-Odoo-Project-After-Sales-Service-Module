# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HRDashboard(models.Model):
    _inherit = 'sh.hr.dashboard'

    # def open_hr_announcement(self):
    #     message_id = self.env['hr.message.wizard'].create({'message': _("Invitation is successfully sent")})
    #     return {
    #         'name': _('Successfull'),
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'res_model': 'hr.message.wizard',
    #         'res_id': message_id.id,
    #         'target': 'new'
    #     }
