from odoo import tools, models, fields, api, _ 
from odoo.exceptions import UserError, ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for record in self:
            record.check_data_move(record)
        return res

    def check_data_move(self, picking_id):
        move_id_picking = self.env['account.move'].search([('ref','ilike',picking_id.name)])
        date = fields.Date.today()
        purchase_order = self.env['purchase.order'].search([('name','ilike', picking_id.origin)])
        
        if self.company_id.currency_id != purchase_order.currency_id:
            bill_invoice = self.env['account.move'].search([('purchase_order_ids','in', purchase_order.ids)])
            account_id = False

            if bill_invoice:
                for line_bill_invoice in bill_invoice.invoice_line_ids:
                    account_id = line_bill_invoice.account_id

            if move_id_picking and bill_invoice:
                create_journal = True
                if not purchase_order.order_line:
                    create_journal = False
                for purchase_order_line in purchase_order.order_line:
                    if purchase_order_line.product_qty != purchase_order_line.qty_invoiced:
                        create_journal = False
                        break
                if create_journal:
                    line_ids = (move_id_picking.line_ids + bill_invoice.line_ids).filtered(lambda line: line.account_id.id == account_id.id)
                    total = sum(line_ids.mapped('debit')) - sum(line_ids.mapped('credit'))
                    if total != 0:
                        journal = self.env.company.currency_exchange_journal_id

                        if total > 0.0:
                            exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                        else:
                            exchange_line_account = journal.company_id.income_currency_exchange_account_id

                        exchange_diff_move_vals = {
                                                    'move_type': 'entry',
                                                    'date': date,
                                                    'journal_id': journal.id,
                                                    'currency_id': self.env.company.currency_id.id,
                                                    'line_ids': [],
                                                    'ref' : _('Currency exchange rate difference PO %s', purchase_order.name),
                                                    }
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                'name': _('Currency exchange rate difference PO %s', purchase_order.name),
                                'debit': -total if total < 0.0 else 0.0,
                                'credit': total if total > 0.0 else 0.0,
                                'account_id': account_id.id,
                                'currency_id': self.env.company.currency_id.id,
                            }),
                            (0, 0, {
                                'name': _('Currency exchange rate difference PO %s', purchase_order.name),
                                'debit': total if total > 0.0 else 0.0,
                                'credit': -total if total < 0.0 else 0.0,
                                'account_id': exchange_line_account.id,
                                'currency_id': self.env.company.currency_id.id,
                            }),
                        ]

                        AccountMove = self.env['account.move']
                        moves = AccountMove.create(exchange_diff_move_vals)
                        moves.post()