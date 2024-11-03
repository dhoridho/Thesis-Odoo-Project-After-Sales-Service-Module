
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cleared_bank_account = fields.Boolean(
        'Cleared? ',
        help='Check if the transaction has cleared from the bank')
    bank_acc_rec_statement_id = fields.Many2one(
        'bank.acc.rec.statement',
        'Bank Acc Rec Statement',
        help="The Bank Acc Rec Statement linked with the journal item")
    draft_assigned_to_statement = fields.Boolean(
        'Assigned to Statement? ',
        help='Check if the move line is assigned to statement lines')
