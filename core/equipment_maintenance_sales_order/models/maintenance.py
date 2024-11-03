# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    maintenance_requestcustom_line_ids = fields.One2many(
       'maintenance.request.custom.lines',
       'maint_request_custom_id',
       string="Maintenance Request Lines",
       copy=True,
    )
    partner_custom_id = fields.Many2one(
        'res.partner',
        string='Customer',
        copy=True,
    )

    def show_quotation(self):
        self.ensure_one()
        res = self.env.ref('sale.action_quotations')
        res = res.read()[0]
        res['domain'] = str([('maint_request_custom_id','=', self.id)])
        return res
   