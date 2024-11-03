from odoo import _, api, fields, models
from odoo.addons.base.models.ir_model import quote


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    is_from_query = fields.Boolean(string='Is From Query')
    stock_move_ids = fields.Many2many('stock.move', 'account_move_stock_move_rel', 'account_move_id', 'stock_move_id', string='Stock Moves', copy=False)

    @api.model
    def _query_complete_account_move_fields(self, res, branch):
        today = fields.Date.today()
        period = self.env['sh.account.period'].sudo().search([
            ('date_start', '<=', today), 
            ('date_end', '>=', today)
        ], limit=1)

        res.update({
            'name': res.get('name') or '/',
            'branch_id': branch.id,
            'auto_reverse_date_mode': 'custom',
            'period_id': period.id,
            'fiscal_year': period.fiscal_year_id.id,
            'is_from_query': True
        })

        for line in res.get('line_ids', []):
            line[-1].update({
                'is_from_query': True
            })
        return res

    def _stock_account_anglo_saxon_reconcile_valuation(self, product=False):
        """ Reconciles the entries made in the interim accounts in anglosaxon accounting,
        reconciling stock valuation move lines with the invoice's.
        """
        # override
        # only change account_move_ids with its new relation m2m_account_move_ids
        for move in self:
            if not move.is_invoice():
                continue
            if not move.company_id.anglo_saxon_accounting:
                continue

            stock_moves = move._stock_account_get_last_step_stock_moves()

            if not stock_moves:
                continue

            products = product or move.mapped('invoice_line_ids.product_id')
            for prod in products:
                if prod.valuation != 'real_time':
                    continue

                # We first get the invoices move lines (taking the invoice and the previous ones into account)...
                product_accounts = prod.product_tmpl_id._get_product_accounts()
                if move.is_sale_document():
                    product_interim_account = product_accounts['stock_output']
                else:
                    product_interim_account = product_accounts['stock_input']

                if product_interim_account.reconcile:
                    # Search for anglo-saxon lines linked to the product in the journal entry.
                    product_account_moves = move.line_ids.filtered(
                        lambda line: line.product_id == prod and line.account_id == product_interim_account and not line.reconciled)

                    # Search for anglo-saxon lines linked to the product in the stock moves.
                    product_stock_moves = stock_moves.filtered(lambda stock_move: stock_move.product_id == prod)
                    product_account_moves += product_stock_moves.mapped('m2m_account_move_ids.line_ids')\
                        .filtered(lambda line: line.account_id == product_interim_account and not line.reconciled)

                    # Reconcile.
                    product_account_moves.reconcile()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_from_query = fields.Boolean(string='Is From Query')
