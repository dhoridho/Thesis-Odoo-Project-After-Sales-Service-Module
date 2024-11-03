
from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import UserError, ValidationError

# class CustDeposit(models.Model):
#     _inherit = 'customer.deposit'

#     used_amount = fields.Monetary(string='Used Amount', compute='_compute_amount')

#     @api.depends('amount', 'remaining_amount')
#     def _compute_amount(self):
#         for rec in self:
#             rec.used_amount = rec.amount - rec.remaining_amount

class CustomerDepositReport(models.Model):
    _name = 'customer.deposit.report'
    _description = 'Customer Deposit Report'
    _auto = False

    name = fields.Char(string='Name')
    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    amount = fields.Monetary(currency_field='currency_id', string="Amount", required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    remaining_amount = fields.Monetary(string="Remaining Amount")
    communication = fields.Char(string="Reference")
    move_id = fields.Many2one('account.move', string="Journal Entry", required=True)
    return_deposit = fields.Many2one('account.move', string="Return Deposit")
    payment_date = fields.Date(string="Payment Date", required=True)
    deposit_reconcile_journal_id = fields.Many2one('account.journal', string="Deposit Reconcile Journal", required=True)
    journal_id = fields.Many2one('account.journal', string="Payment Method")
    deposit_account_id = fields.Many2one('account.account', string="Deposit Account",required=True)
    used_amount = fields.Monetary(string='Used Amount')


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))

    def _select(self):
        select_str = """
            SELECT
            min(cd.id) as id,
            cd.name as name,
            cd.partner_id as partner_id,
            cd.amount as amount,
            cd.remaining_amount as remaining_amount,
            (cd.amount - cd.remaining_amount) as used_amount,
            cd.communication as communication,
            cd.create_date as create_date,
            cd.deposit_move_id as move_id,
            cd.return_deposit as return_deposit,
            cd.payment_date as payment_date,
            cd.deposit_reconcile_journal_id as deposit_reconcile_journal_id,
            cd.journal_id as journal_id,
            cd.deposit_account_id as deposit_account_id,
            cd.currency_id as currency_id
        """
        return select_str

    def _from(self):
        from_str = """
            customer_deposit cd
            """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                cd.name,
                cd.partner_id,
                cd.amount,
                cd.remaining_amount,
                cd.communication,
                cd.deposit_move_id,
                cd.create_date,
                cd.return_deposit,
                cd.payment_date,
                cd.deposit_reconcile_journal_id,
                cd.journal_id,
                cd.deposit_account_id,
                cd.currency_id,
                used_amount
            """ 
        return group_by_str