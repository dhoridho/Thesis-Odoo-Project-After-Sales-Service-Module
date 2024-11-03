# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    def write(self, vals):
        if vals.get('stage_id'):
            stage_id = self.env['maintenance.stage'].browse(vals.get('stage_id'))
            if not stage_id.custom_user_ids:
                return super(MaintenanceRequest, self).write(vals)
            if self.env.user.id in stage_id.custom_user_ids.ids:
                return super(MaintenanceRequest, self).write(vals)
            else:
                raise UserError(_("You can not move maintenance request to this stage. Please contact your manager."))
            return super(MaintenanceRequest, self).write(vals)

        return super(MaintenanceRequest, self).write(vals)#final call.

    
