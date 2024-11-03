# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time


class CommissionInvoice(models.TransientModel):
    _name = "commission.invoice"
    _description = "Commission Invoice"

    @api.model
    def _get_default_journal(self):
        journal_domain = [
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.user.company_id.id),
        ]
        default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
        return default_journal_id.id and default_journal_id or False

    hide_groupby_partner = fields.Boolean(string='Hide Group by Partner')
    groupby_partner = fields.Boolean(string='Group by Partner', default=False,
        help='Set true if want to create single invoice for Partner')
    print_commission = fields.Boolean(string='Add Commission no in Description', default=False,
        help='Set true if want to append SO in invoice line Description')
    journal_id = fields.Many2one('account.journal', default=_get_default_journal, required=True)

    def create_invoice(self, line):
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': False,
            'partner_id': line.partner_id.id,
            'journal_id': self.journal_id.id,
            'hospital_invoice_type': 'commission'
        })
        return invoice

    def create_invoice_line(self, line, invoice, product_id, print_commission=False):
        account_id = product_id.property_account_income_id or product_id.categ_id.property_account_income_categ_id
        if not account_id:
            raise UserError(
                _('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %
                (product_id.name,))
        name = product_id.name

        if print_commission:
            name = name + ': ' + line.name

        inv_line = self.env['account.move.line'].with_context(check_move_validity=False).create({
            'move_id': invoice.id,
            'name': name,
            'price_unit': line.commission_amount,
            'quantity': 1,
            'discount': 0.0,
            'product_uom_id': product_id.uom_id.id,
            'product_id': product_id.id,
            'account_id': account_id.id,
            'tax_ids': [(6, 0, product_id.supplier_taxes_id and product_id.supplier_taxes_id.ids or [])],
        })
        return inv_line

    def create_invoices(self):
        Commission = self.env['acs.hms.commission']
        groupby = False
        invoices = []
        product_id = self.env.user.company_id.commission_product_id
        if not product_id:
            raise UserError(_('Please set Commission Product in company first.'))
        if self.groupby_partner:
            groupby = 'partner_id'
        if groupby:
            commission_group = Commission.read_group([('id', 'in', self._context.get('active_ids', [])),
                ('invoice_line_id', '=', False)] , fields=[groupby], groupby=[groupby])
            for group in commission_group:
                domain = [('id', 'in', self._context.get('active_ids', [])),
                    ('invoice_line_id', '=', False)]
                if group[groupby]:
                    domain += [(groupby, '=', int(group[groupby][0]))]
                lines = Commission.search(domain)
                if lines:
                    invoice = self.create_invoice(lines[0])
                    invoices.append(invoice.id)
                    for line in lines:
                        line_rec = self.create_invoice_line(line, invoice, product_id, self.print_commission)
                        line.invoice_line_id = line_rec.id

        else:
            lines = Commission.browse(self._context.get('active_ids', []))
            for line in lines:
                if not line.invoice_line_id:
                    invoice = self.create_invoice(line)
                    invoices.append(invoice.id)
                    line_rec = self.create_invoice_line(line, invoice, product_id, self.print_commission)
                    line.invoice_line_id = line_rec.id

        if not invoices:
            raise UserError(_('Please check there is nothing to invoice in selected Commission may be you are missing partner or trying to invoice already invoiced Commissions.'))

        acs_invoices = self.env['account.move'].search([('id','in',invoices)])
        for invoice in acs_invoices:
            invoice.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_tax_base_amount=True)

        #last invoice from above loop will be used
        if self._context.get('commission_sheet_id', False):
            sheet = self.env['acs.commission.sheet'].search([('id','=',self._context.get('commission_sheet_id', False))])
            sheet.payment_invoice_id = invoice.id

        if self._context.get('open_invoices', False):
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
            if len(invoices) > 1:
                action['domain'] = [('id', 'in', invoices)]
            elif len(invoices) == 1:
                action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
                action['res_id'] = invoices[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action
        return {'type': 'ir.actions.act_window_close'}