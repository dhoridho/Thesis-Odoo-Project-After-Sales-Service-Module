
from odoo import api, fields, models, _


class PurchaseAgreement(models.Model):
    _inherit = 'purchase.agreement'
    
    is_assets_orders = fields.Boolean(string="Assets Orders", default=False)
    
    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order'):
            if context.get('assets_orders'):
                if vals.get('tender_scope') and vals['tender_scope'] == 'open_tender':
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.a.open')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.a')
        return super(PurchaseAgreement, self).create(vals)
    
    @api.depends('branch_id', 'sh_agreement_type', 'amount')
    def _get_approval_matrix(self):
        res = super(PurchaseAgreement, self)._get_approval_matrix()
        set_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_tender_approval_matrix')
        # set_approval_matrix = self.env.company.is_purchase_tender_approval_matrix
        for record in self:
            if set_approval_matrix and record.is_assets_orders:
                approval_id = self.env['purchase.agreement.approval.matrix'].search([('branch_id', '=', record.branch_id.id), ('order_type', '=', 'assets_order')], limit=1, order='id desc')
                record.approval_matrix = approval_id
        return res
    
class PurchaseAgreementLine(models.Model):
    _inherit ='purchase.agreement.line'
    
    # Jalan
    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        domain = [('company_id','=',self.env.company.id)]
        res = super(PurchaseAgreementLine, self)._default_domain()
        if context.get('assets_orders'):
            return domain+[('type', '=', 'asset')]
        return res

    sh_product_id = fields.Many2one(domain=_default_domain)
