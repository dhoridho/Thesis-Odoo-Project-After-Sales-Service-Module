
import time

from odoo import api, models


class BankStatmentBalance(models.AbstractModel):
    _name = 'report.sg_bank_reconcilation_report.sg_bank_statment_report'
    _description = "Bank Statement Balance"

    def get_blc(self, acc_id, st_date):
        """Get Balance."""
        self._cr.execute("""
            SELECT
                sum(debit) - sum(credit)
            FROM
                account_move_line l , account_move m
            WHERE
                l.move_id = m.id
            AND l.account_id = %s
            AND m.date >= %s
            AND m.state='posted'""", (acc_id.id, st_date))
        acc_blc = self._cr.fetchall()
        if acc_blc and acc_blc[0] and acc_blc[0][0]:
            return acc_blc[0][0]
        return 0.00

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values."""
        model = self.env.context.get('active_model')
        docs = self.env['bank.acc.rec.statement'].browse(docids)
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'docs': docs,
            'time': time,
            'get_blc': self.get_blc,
        }
