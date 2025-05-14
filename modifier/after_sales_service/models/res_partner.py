from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = "res.partner"

    service_request_ids = fields.One2many('service.request', 'partner_id', string='Service Requests')
    warranty_claim_ids = fields.One2many('warranty.claim', 'partner_id', string='Warranty Claims')
    sale_return_ids = fields.One2many('dev.rma.rma', 'partner_id', string='Sale Returns')
    # sale_order_ids = fields.One2many('sale.order', 'partner_id', string='Sale Orders')
    # feedback_ids = fields.One2many('customer.feedback', 'partner_id', string='Customer Feedback')
    warranty_claim_count = fields.Integer(string="Warranty Claims", compute="_compute_warranty_claim_count", store=True)
    service_request_count = fields.Integer(string="Service Requests", compute="_compute_service_request_count", store=True)
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='Sale Order Count', store=True)
    sale_return_count = fields.Integer(compute='_compute_sale_return_count', string='Sale Return Count', store=True)

    @api.depends('warranty_claim_ids')
    def _compute_warranty_claim_count(self):
        for partner in self:
            partner.warranty_claim_count = len(partner.warranty_claim_ids)

    @api.depends('service_request_ids')
    def _compute_service_request_count(self):
        for partner in self:
            partner.service_request_count = len(partner.service_request_ids)

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for partner in self:
            partner.sale_order_count = len(partner.sale_order_ids)

    @api.depends('sale_return_ids')
    def _compute_sale_return_count(self):
        for partner in self:
            partner.sale_return_count = len(partner.sale_return_ids)

class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def create(self, vals):
        res = super(ResUsers, self).create(vals)
        # print('debug')
        if res.has_group('base.group_portal'):
            res.partner_id.is_customer = True

        return res
