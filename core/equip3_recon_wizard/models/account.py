import logging

from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move.line'

    manual_reconciled = fields.Selection(
        [('not_match', 'Not Matched'), ('match', 'Matched')],
        default='not_match',
        string="Manual Reconciled",
    )
    manual_reconcile_id = fields.Many2one('manual.reconcile.report', string='Manual  Recocile Id')


class AccountAccount(models.Model):
    _inherit = 'account.account'

    beginning_balance = fields.Float(default=0, string="Beginning Balance")
    last_statement_ending_date = fields.Char(string="Last Statement Date")


class CustomFinancialReport(models.Model):
    _name = 'manual.reconcile.report'
    _description = 'Manual  Reconcile Report'
    _order = 'write_date desc'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    ending_date = fields.Char(string='Ending Date', required=True)
    ending_balance = fields.Float(string='Ending Balance')
    starting_balance = fields.Float(string='Starting Balance')
    difference = fields.Float(string='Difference Balance')
    account_move_line_ids = fields.One2many('account.move.line', 'manual_reconcile_id', string='Journal Items')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ], string='Status', readonly=True, copy=False,
         store=True)
