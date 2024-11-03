
from odoo import api, fields, models, _
from odoo.exceptions import UserError , ValidationError
from datetime import timedelta, datetime, date


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    is_purchase_req_direct_purchase = fields.Boolean(string='Purchase Request to Direct Purchase', compute="_compute_is_purchase_req_direct_purchase", store=False)

    def _compute_is_purchase_req_direct_purchase(self):
        is_purchase_req_direct_purchase = self.env['ir.config_parameter'].sudo().get_param('group_create_purchase_request_direct', False)
        for record in self:
            record.is_purchase_req_direct_purchase = is_purchase_req_direct_purchase

    def create_direct_purchase(self):
        context = dict(self.env.context) or {}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'create.purchase.request.direct',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Create RFQ",
            'target': 'new',
            'context': context,
        }

    @api.onchange('requested_by')
    def get_requested_by(self):
        res = super(PurchaseRequest, self).get_requested_by()
        self._compute_is_purchase_req_direct_purchase()
        return res
