from odoo import api, fields, models, modules, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class ResCompany(models.Model):
    _inherit = 'res.company'

    tax_discount_policy = fields.Selection([('untax', 'After Discount'), ('tax', 'Before Discount')], string='Discount Applies On')
    sale_account_id = fields.Many2one('account.account', 'Sale Discount Account', domain="[('company_id', '=', current_company_id), ('discount_account','=',True), ('user_type_id.internal_group','in',['expense'])]",  help="Only set value with string account = Sale Discount")
    purchase_account_id = fields.Many2one('account.account', 'Purchase Discount Account', domain="[('company_id', '=', current_company_id), ('discount_account','=',True),('user_type_id.internal_group','in',['income'])]", help="Only set value with string account = Purchase Discount")
    post_discount_account = fields.Boolean(string='Post Discount Account')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tax_discount_policy = fields.Selection(string='Tax Applies on', related="company_id.tax_discount_policy", readonly=False)
    sale_account_id = fields.Many2one('account.account', 'Sale Discount Account', domain="[('company_id', '=', current_company_id), ('discount_account','=',True), ('user_type_id.internal_group','in',['expense'])]",  related="company_id.sale_account_id", readonly=False, help="Only set value with string account = Sale Discount")
    purchase_account_id = fields.Many2one('account.account', 'Purchase Discount Account', domain="[('company_id', '=', current_company_id), ('discount_account','=',True),('user_type_id.internal_group','in',['income'])]", related="company_id.purchase_account_id", readonly=False, help="Only set value with string account = Purchase Discount")
    post_discount_account = fields.Boolean(string='Post Discount Account',related="company_id.post_discount_account", readonly=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update({'tax_discount_policy': self.env['ir.config_parameter'].sudo().get_param('tax_discount_policy', 'untax'),
                    'post_discount_account': self.env['ir.config_parameter'].sudo().get_param('post_discount_account', False)
                   })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('tax_discount_policy', self.tax_discount_policy)
        self.env['ir.config_parameter'].sudo().set_param('post_discount_account', self.post_discount_account)