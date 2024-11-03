from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class AccountAnalyticGroup(models.Model):
    _name = 'account.analytic.group'
    _inherit = ['account.analytic.group','mail.thread','mail.activity.mixin']
    _description = 'Account Analytic Group'

    name = fields.Char(required=True, tracking=True, string='Analytic Category')
    description = fields.Text(string='Description', tracking=True)
    parent_id = fields.Many2one('account.analytic.group', string="Parent", ondelete='cascade', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    analytic_account_ids = fields.One2many('account.analytic.account', 'group_id', string='Analytic Account')
    analyticnew_ids = fields.One2many('account.analytic.new', 'group_id')
