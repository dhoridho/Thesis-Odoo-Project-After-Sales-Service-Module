
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class UsageType(models.Model):
    _name = 'usage.type'
    _description = 'Usage Type'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    company_id = fields.Many2one('res.company', string='Company',tracking=True, readonly=True, default=lambda self: self.env.user.company_id)
    branch_id = fields.Many2one('res.branch', string='Branch',tracking=True, domain="[('company_id', '=', company_id)]")
    name = fields.Char(string="Usage Name", required=True, tracking=True)
    account_id = fields.Many2one('account.account', string='Expense Account', required=True, tracking=True)
    filter_account_ids = fields.Many2many('account.account', compute='_compute_account_ids', store=False)
    usage_type = fields.Selection([('usage', 'Usage'),
                                    ('scrap', 'Scrap'),
                                    ], string='Usage Type', required=True,
                                    default='usage',tracking=True)
    income_account_id = fields.Many2one('account.account', string="Income Account", tracking=True)
    product_category_id = fields.Many2one('product.category', string='Product Category', tracking=True)
    inv_val_account_id = fields.Many2one('account.account', string="Inventory Valuation Account", related='product_category_id.property_stock_valuation_account_id', tracking=True)
    filter_income_account_ids = fields.Many2many('account.account', compute='_compute_income_account_ids', store=False)

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            usage_id = self.search([('name', '=', record.name), ('id', '!=', record.id)], limit=1)
            if usage_id:
                raise ValidationError(_(" %s Is Already There. Please Create A Usage Type With Another Name" % record.name))

    @api.depends('company_id')
    def _compute_account_ids(self):
        expense_account_id = self.env.ref('account.data_account_type_expenses')
        for rec in self:
            account_ids = self.env['account.account'].search([('user_type_id', '=', expense_account_id.id), ('company_id','=', rec.company_id.id)])
            rec.filter_account_ids = [(6, 0, account_ids.ids)]
    
    @api.depends('company_id')
    def _compute_income_account_ids(self):
        revenue_account_id = self.env.ref('account.data_account_type_revenue')
        other_income_account_id = self.env.ref('account.data_account_type_other_income')
        for rec in self:
            account_ids = self.env['account.account'].search([('user_type_id', 'in', [revenue_account_id.id , other_income_account_id.id]), ('company_id','=', rec.company_id.id)])
            rec.filter_income_account_ids = [(6, 0, account_ids.ids)]
    
    @api.model
    def action_create_usage_type(self):
        """
        before upgrade this current module, we need to set default value for expense account and income account from settings
        by upgrade inventory_tracking first and then set default value for expense account and income account from settings
        then you can upgrade this module to create or update auto scrap usage type
        """
        expense_account_id = self.env['ir.config_parameter'].sudo().get_param('scrap_expense_id')
        income_account_id = self.env['ir.config_parameter'].sudo().get_param('scrap_income_id')
        is_exist = self.env['usage.type'].search([('name', '=', 'Auto Scrap')])
        if not is_exist:
            if expense_account_id and income_account_id:
                self.env['usage.type'].create({
                    'name': 'Auto Scrap',
                    'usage_type': 'scrap',
                    'account_id': expense_account_id,
                    'income_account_id': income_account_id,
                })
            else:
                pass
        else:
            pass
