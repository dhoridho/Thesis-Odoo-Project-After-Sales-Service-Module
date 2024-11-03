from odoo import api, fields, models, _

class AccountAnalyticDefault(models.Model):
    _name = 'account.analytic.default'
    _inherit = ['account.analytic.default','mail.thread','mail.activity.mixin']
    _description = 'Account Analytic Default'

    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', help="Select an accounting account which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this account, it will automatically take this as an analytic account)", tracking=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade', help="Select a product which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)", tracking=True)
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', help="Select a user which will use analytic account specified in analytic default.", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', help="Select a company which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)", tracking=True)
    date_start = fields.Date(string='Start Date', help="Default start date for this Analytic Account.", tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade', help="Select a partner which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)", tracking=True)
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', help="Select an accounting account which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this account, it will automatically take this as an analytic account)", tracking=True)
    date_stop = fields.Date(string='End Date', help="Default end date for this Analytic Account.", tracking=True)
   
    @api.model
    def action_delete_menu_analytical(self):
        try:
            menu_analytic_default = self.env.ref('account.menu_analytic_default_list')
        except ValueError:
            menu_analytic_default = False
        if menu_analytic_default:
            menu_analytic_default.active = False
