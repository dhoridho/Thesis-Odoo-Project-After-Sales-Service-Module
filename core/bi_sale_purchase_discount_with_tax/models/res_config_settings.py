from odoo import api, fields, models, modules, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_discount_policy = fields.Selection([('tax', 'Tax Amount'), ('untax', 'Untax Amount')], string='Discount Applies On')
    sale_account_id = fields.Many2one('account.account', string='Sale Discount Account', domain=[('user_type_id.name','=','Income'), ('discount_account','=',True)])
    purchase_account_id = fields.Many2one('account.account', string='Purchase Discount Account', domain=[('user_type_id.name','=','Expenses'), ('discount_account','=',True)])

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tax_discount_policy = fields.Selection(string='Discount Applies On', related='company_id.tax_discount_policy', readonly=False)
    sale_account_id = fields.Many2one('account.account', string='Sale Discount Account', domain=[('user_type_id.name','=','Income'), ('discount_account','=',True)], related='company_id.sale_account_id', readonly=False)
    purchase_account_id = fields.Many2one('account.account', string='Purchase Discount Account', domain=[('user_type_id.name','=','Expenses'), ('discount_account','=',True)], related='company_id.purchase_account_id', readonly=False)
    