from odoo import api, fields, models, _

class AccountAnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['account.analytic.line','mail.thread','mail.activity.mixin']
    _description = 'Account Analytic Line'

    name = fields.Char('Description', required=True, tracking=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today, tracking=True)
    amount = fields.Monetary('Amount', required=True, default=0.0, tracking=True)
    unit_amount = fields.Float('Quantity', default=0.0, tracking=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]", tracking=True)
    account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='restrict', index=True, check_company=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner', check_company=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company, tracking=True)
    group_id = fields.Many2one('account.analytic.group', related='account_id.group_id', store=True, readonly=True, compute_sudo=True, tracking=True)
    product_id = fields.Many2one('product.product', string='Product', check_company=True, tracking=True)
    ref = fields.Char(string='Ref.', tracking=True)
    move_id = fields.Many2one('account.move.line', string='Journal Item', ondelete='cascade', index=True, check_company=True, tracking=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today, tracking=True)
    amount = fields.Monetary('Amount', required=True, default=0.0, tracking=True)
