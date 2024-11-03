
from odoo import api, fields, models, _


class PurchaseAgreement(models.Model):
    _inherit = 'purchase.agreement'
    
    is_rental_orders = fields.Boolean(string="Rental Orders", default=False)
    rent_duration = fields.Integer(string='Rent Duration')
    rent_duration_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ],string="Single Rent Duration")
    
    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order'):
            if context.get('rentals_orders'):
                if vals.get('tender_scope') and vals.get('tender_scope') == 'open_tender':
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.r.open')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.r')
        return super(PurchaseAgreement, self).create(vals)
    
    @api.depends('branch_id', 'sh_agreement_type', 'amount')
    def _get_approval_matrix(self):
        res = super(PurchaseAgreement, self)._get_approval_matrix()
        set_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_tender_approval_matrix')
        for record in self:
            if set_approval_matrix and record.is_rental_orders:
                approval_id = self.env['purchase.agreement.approval.matrix'].search(
                    [
                    ('branch_id', '=', record.branch_id.id), 
                    ('order_type', '=', 'rental_order')
                    ], 
                    limit=1, order='id desc')
                record.approval_matrix = approval_id
        return res
    
class PurchaseAgreementLine(models.Model):
    _inherit ='purchase.agreement.line'
    
    # Jalan
    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        res = super(PurchaseAgreementLine, self)._default_domain()
        domain = [('company_id','=',self.env.company.id)]
        if context.get('rentals_orders'):
            return domain+[('is_rented', '=', True)]
        return res

    is_rental_orders = fields.Boolean(string="Rental Orders", related='agreement_id.is_rental_orders', store=True)
    sh_product_id = fields.Many2one(domain=_default_domain)
