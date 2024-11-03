from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError
from lxml import etree

class picking_order(models.Model):
    _inherit = "picking.order"

    delivery_boy_move_id = fields.Many2one('account.move',string="Delivery Boy Journal Ref")
    order_amount = fields.Float(string="Total")
    payment_term_id = fields.Many2one('account.payment.term',string="Payment Term")
    date_order = fields.Datetime(string="Order Date")

    def create(self,vals):
        res = super(picking_order, self).create(vals)
        res.order_amount = res.sale_order.amount_total
        res.payment_term_id = res.sale_order.payment_term_id
        res.date_order = res.sale_order.date_order
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        res = super(picking_order, self).fields_view_get(view_id=view_id, view_type=view_type, 
                                                        toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        remove_button = self.env.ref('delivery_cash_wallet.action_picking_order_from_list').id
        for button in res.get('toolbar', {}).get('action', []):
            if remove_button and button['id'] == remove_button:
                res['toolbar']['action'].remove(button)
        res['arch'] = etree.tostring(doc)
        return res

    def view_invoice_register_payment(self):
        # self.write({'state': 'payment_collected'})
        return {
           'type': 'ir.actions.act_window',
           'name': ('Journal Items'),
           'res_model': 'account.payment.register',
           'view_mode': 'form',
           'context': {
                'active_model': 'account.move',
                'active_ids': self.invoice.id,
            },
           'target' : 'new'
        }

    def invoice_register_payment(self):
        account_journal = self.env['account.journal'].sudo().search([('name', '=', 'Bank')],limit=1)
        payment_method = self.env['account.payment.method'].sudo().search([])
        for rec in self:
            if rec.invoice and rec.state == "delivered":
                invoice_id = rec.invoice
                vals={
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': invoice_id.partner_id.id,
                    'ref': invoice_id.name,
                    'amount': invoice_id.amount_total,
                    'payment_method_id': payment_method[0].id,
                    'journal_id': account_journal.id,
                }
                payment = self.env['account.payment'].sudo().create(vals)
                if payment:
                    payment.action_post()
                    rec.state = "payment_collected"

                to_reconcile = []

                available_lines = self.env['account.move.line']
                for line in invoice_id.line_ids:
                    if line.move_id.state != 'posted':
                        raise UserError(_("You can only register payment for posted journal entries."))

                    if line.account_internal_type not in ('receivable', 'payable'):
                        continue
                    if line.currency_id:
                        if line.currency_id.is_zero(line.amount_residual_currency):
                            continue
                    else:
                        if line.company_currency_id.is_zero(line.amount_residual):
                            continue
                    available_lines |= line

                to_reconcile.append(available_lines)
                domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]

                for payment, lines in zip(payment, to_reconcile):
                    if payment.state != 'posted':
                        continue
                    payment_lines = payment.line_ids.filtered_domain(domain)
                    for account in payment_lines.account_id:
                        (payment_lines + lines) \
                            .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                            .reconcile()
            else:
                raise UserError(_("You can only register payment for 'Delivered' Order"))
