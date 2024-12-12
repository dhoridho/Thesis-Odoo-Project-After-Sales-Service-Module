from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = "res.partner"

    service_request_ids = fields.One2many('service.request', 'customer_id', string='Service Requests')
    warranty_claim_ids = fields.One2many('warranty.claim', 'customer_id', string='Warranty Claims')
    # sale_order_ids = fields.One2many('sale.order', 'partner_id', string='Sale Orders')
    # feedback_ids = fields.One2many('customer.feedback', 'customer_id', string='Customer Feedback')
    is_customer = fields.Boolean(string="Is Customer", default=False)
    warranty_claim_count = fields.Integer(string="Warranty Claims", compute="_compute_warranty_claim_count")
    service_request_count = fields.Integer(string="Service Requests", compute="_compute_service_request_count")

    @api.model
    def create(self, vals):
        partner = super(ResPartner, self).create(vals)
        if 'user_ids' in vals and any(
            user.has_group('portal.group_portal') for user in partner.user_ids
        ):
            partner.is_customer = True

        return partner

    @api.depends('warranty_claim_ids')
    def _compute_warranty_claim_count(self):
        for partner in self:
            partner.warranty_claim_count = len(partner.warranty_claim_ids)

    @api.depends('service_request_ids')
    def _compute_service_request_count(self):
        for partner in self:
            partner.service_request_count = len(partner.service_request_ids)
