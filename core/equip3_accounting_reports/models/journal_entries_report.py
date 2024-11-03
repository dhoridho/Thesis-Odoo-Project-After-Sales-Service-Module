
from odoo import api, fields, models, _
from odoo import tools

class JournalEntriesReport(models.Model):
    _name = 'journal.entries.report'
    _description = 'Journal Entries Report'
    _auto = False

    # move_id = fields.Many2one('account.move', readonly=True)
    num = fields.Char(string='Number', readonly=True)
    label = fields.Char(string='Label', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", readonly=True)
    amount_currency = fields.Monetary(string="Amount in Currency", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
    debit = fields.Monetary(string="Debit", readonly=True)
    credit = fields.Monetary(string="Credit", readonly=True)

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
            ap.name as label,
            ap.move_name as num,
            ap.account_id as account_id,
            ap.partner_id as partner_id,
            ap.analytic_account_id as analytic_account_id,
            ap.amount_currency as amount_currency,
            ap.currency_id as currency_id,
            ap.debit as debit,
            ap.credit as credit
        """
        return select_str

    def _from(self):
        from_str = """
            account_move_line as ap
            """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                ap.name,
                ap.move_name,
                ap.account_id,
                ap.partner_id,
                ap.analytic_account_id,
                ap.amount_currency,
                ap.currency_id,
                ap.debit,
                ap.credit
            """ 
        return group_by_str