
from odoo import api, fields, models, _
from odoo import tools

class AccountPettyCashReport(models.Model):
    _name = 'account.petty.cash.report'
    _description = 'Account Petty Cash Report'
    _auto = False

    name = fields.Char(string='Name', readonly=True)
    custodian_id = fields.Many2one('res.users', string='Custodian', readonly=True)
    main_cash_account_id = fields.Many2one('account.account', string='Main Cash Account', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Petty Cash Journal')
    amount = fields.Float(string="Fund Amount", readonly=True)
    balance = fields.Float(string="Balance", readonly=True)
    virtual_balance = fields.Float(string="Virtual Balance", readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)
    branch_id = fields.Many2one('res.branch', string="Branch", readonly=True)
    effective_date = fields.Date(string="Effective Date", readonly=True)
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True)
    create_date = fields.Datetime(string="Created Date", readonly=True)
    expense_amount = fields.Float(string="Expenses", readonly=True)

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
            min(ap.id) as id,
            ap.name as name,
            ap.custodian as custodian_id,
            ap.main_cash_account_id as main_cash_account_id,
            ap.journal as journal_id,
            ap.amount as amount,
            ap.balance as balance,
            ap.virtual_balance as virtual_balance,
            ap.company_id as company_id,
            ap.create_date as create_date,
            ap.create_uid as create_uid,
            ap.branch_id as branch_id,
            ap.effective_date as effective_date,
            ap.expense_amount as expense_amount
        """
        return select_str

    def _from(self):
        from_str = """
            account_pettycash ap
            """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                ap.name,
                ap.custodian,
                ap.main_cash_account_id,
                ap.journal,
                ap.amount,
                ap.balance,
                ap.virtual_balance,
                ap.company_id,
                ap.create_date,
                ap.create_uid,
                ap.branch_id,
                ap.effective_date,
                ap.expense_amount
            """ 
        return group_by_str
