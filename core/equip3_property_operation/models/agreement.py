from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
from odoo.exceptions import UserError


class Agreement(models.Model):
    _inherit = 'agreement'

    is_active_stage = fields.Boolean(string='Active Stage', compute='_compute_is_active_stage')

    @api.depends('stage_id')
    def _compute_is_active_stage(self):
        for rec in self:
            rec.is_active_stage = False
            if rec.stage_id.name == 'Active':
                rec.is_active_stage = True


    def create_invoice_property_agreement(self):
        """ This method is used to create invoice from agreement repeated based on start date and end date"""
        today = fields.Date.context_today(self)
        active_stage = self.env['agreement.stage'].search([('name', 'in', ('Active', 'Expired'))]).ids

        agreements = self.env['agreement'].search([
            ('start_date', '!=', False),
            ('end_date', '!=', False),
            ('stage_id', '=', active_stage),
            ('is_recurring_invoice', '=', True),
            ('invoice_type', '=', 'recurring'),
            ('line_ids', '!=', False),
            ('is_template', '=', False),
            ('active', '=', True),
        ])

        if agreements:
            for agreement in agreements:
                recurring_type = agreement.recurring_invoice_id.recurring_type
                recurring_duration = agreement.recurring_invoice_id.recurring_duration

                if recurring_type == 'daily':
                    total_invoice_need = agreement.duration_daily / recurring_duration
                elif recurring_type == 'monthly':
                    total_invoice_need = agreement.duration_monthly / recurring_duration
                elif recurring_type == 'yearly':
                    total_invoice_need = agreement.duration_yearly / recurring_duration

                if agreement.invoice_count >= total_invoice_need:
                    continue

                recurring_count = 0
                for _ in range(int(total_invoice_need)):
                    invoice_line = []
                    in_due_date = False

                    for line in agreement.line_ids:
                        income_account = line.product_id.property_account_income_id or \
                                        line.product_id.categ_id.property_account_income_categ_id
                        if not income_account:
                            raise UserError(_('Please define income account for this product: "%s" (id:%d).') % (
                            line.product_id.name, line.product_id.id))

                        if recurring_type == 'daily':
                            freq = agreement.duration_daily
                            in_due_date = today + relativedelta(days=freq)
                        elif recurring_type == 'monthly':
                            freq = agreement.duration_monthly
                            in_due_date = today + relativedelta(months=freq)
                        elif recurring_type == 'yearly':
                            freq = agreement.duration_yearly
                            in_due_date = today + relativedelta(years=freq)

                        invoice_line.append((0, 0, {
                            'product_id': line.product_id.id,
                            'product_uom_id': line.uom_id.id,
                            'quantity': line.qty,
                            'price_unit': line.unit_price,
                            'name': agreement.name,
                            'account_id': income_account.id,
                            'tax_ids': [(6, 0, line.taxes_id.ids)],
                        }))

                    invoice = {
                        'agreement_id': agreement.id,
                        'move_type': 'out_invoice',
                        'invoice_origin': agreement.name,
                        'partner_id': agreement.partner_id.id,
                        'invoice_date_due': in_due_date,
                        'invoice_user_id': agreement.create_uid.id,
                        'invoice_line_ids': invoice_line,
                    }

                    recurring_count += recurring_duration

                    if recurring_type == 'daily':
                        invoice_date = {'invoice_date': agreement.start_date + relativedelta(days=recurring_count)}
                        next_invoice_date = invoice_date['invoice_date'] + relativedelta(days=recurring_duration)
                    elif recurring_type == 'monthly':
                        invoice_date = {'invoice_date': agreement.start_date + relativedelta(months=recurring_count)}
                        next_invoice_date = invoice_date['invoice_date'] + relativedelta(months=recurring_duration)
                    elif recurring_type == 'yearly':
                        invoice_date = {'invoice_date': agreement.start_date + relativedelta(years=recurring_count)}
                        next_invoice_date = invoice_date['invoice_date'] + relativedelta(years=recurring_duration)

                    invoice.update(invoice_date)

                    # ongoing agreement
                    if agreement.start_date <= today and agreement.end_date >= today and invoice_date['invoice_date'] <= today:
                        account_move = self.env['account.move'].search([
                            ('invoice_date', '=', invoice_date['invoice_date']),
                            ('agreement_id', '=', agreement.id)
                        ])
                        if not account_move:
                            account_move_obj = self.env['account.move'].create(invoice)
                            agreement.next_invoice = next_invoice_date
                            # print("➡ ongoing contract :", agreement.name, '➡ invoice_date :',
                            #       invoice_date['invoice_date'], '➡ next_invoice :', next_invoice_date)

                    # backdate agreement
                    if agreement.end_date < today:
                        account_move_obj = self.env['account.move'].create(invoice)
                        agreement.stage_id = self.env['agreement.stage'].search([('name', '=', 'Expired')], limit=1).id
                        # print("➡ backdate contract :", agreement.name, '➡ invoice_date :',
                        #       invoice_date['invoice_date'])

            return True
