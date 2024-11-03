
from odoo import api, fields, models, _
from odoo import tools


class VendorDepositReport(models.Model):
    _name = 'vendor.deposit.report'
    _description = 'Vendor Deposit Report'
    _auto = False
    
    name = fields.Char(string="Name")
    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    amount = fields.Monetary(currency_field='currency_id', string="Amount", required=True)
    remaining_amount = fields.Monetary(string="Remaining Amount")
    communication = fields.Char(string="Reference")
    deposit_move_id = fields.Many2one('account.move', string="Journal Entry", required=True)
    return_deposit = fields.Many2one('account.move', string="Return Deposit")
    payment_date = fields.Date(string="Payment Date", required=True)
    deposit_reconcile_journal_id = fields.Many2one('account.journal', string="Deposit Reconcile Journal", required=True)
    journal_id = fields.Many2one('account.journal', string="Payment Method", domain=[('type','in',('bank','cash'))])
    deposit_account_id = fields.Many2one('account.account', string="Deposit Account")
    used_amount = fields.Monetary(string='Used Amount')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM %s
            %s
            %s
            )""" % (self._table, self._select(), self._from(), self._where(), self._group_by()))

    def _select(self):
        select_str = """
            SELECT
            min(vd.id) as id,
            vd.name as name,
            vd.partner_id as partner_id,
            vd.amount as amount,
            vd.remaining_amount as remaining_amount,
            (vd.amount - vd.remaining_amount) as used_amount,
            vd.communication as communication,
            vd.create_date as create_date,
            vd.move_id as deposit_move_id,
            vd.return_deposit as return_deposit,
            vd.payment_date as payment_date,
            vd.deposit_reconcile_journal_id as deposit_reconcile_journal_id,
            vd.journal_id as journal_id,
            vd.deposit_account_id as deposit_account_id,
            vd.currency_id as currency_id
        """
        if 'is_cash_advance' in self.env['vendor.deposit']:
            select_str += ",vd.is_cash_advance as is_cash_advance "
        return select_str

    def _from(self):
        from_str = """
            vendor_deposit vd
            """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                vd.name,
                vd.partner_id,
                vd.amount,
                vd.remaining_amount,
                vd.communication,
                vd.move_id,
                vd.create_date,
                vd.return_deposit,
                vd.payment_date,
                vd.deposit_reconcile_journal_id,
                vd.journal_id,
                vd.deposit_account_id,
                vd.currency_id,
                used_amount
            """ 

        if 'is_cash_advance' in self.env['vendor.deposit']:
            group_by_str += ",vd.is_cash_advance "
        return group_by_str

    def _where(self):
        if 'is_cash_advance' in self.env['vendor.deposit']:
            where_str = """
            WHERE
                vd.is_cash_advance isnull or vd.is_cash_advance != true
            """ 
        else:
            where_str = """ """ 
        return where_str