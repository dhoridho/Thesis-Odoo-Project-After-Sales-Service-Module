# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class IrModelData(models.Model):
    _inherit = 'ir.model.data'
    _description = 'Model Data'

    @api.model
    def action_update_rescountry_city(self):
        return self._cr.execute("UPDATE ir_model_data SET noupdate = false WHERE module = 'equip3_crm_operation' AND name LIKE 'city_%'")

    @api.model
    def action_noupdate_rescountry_city(self):
        return self._cr.execute("UPDATE ir_model_data SET noupdate = true WHERE module = 'equip3_crm_operation' AND name LIKE 'city_%'")
