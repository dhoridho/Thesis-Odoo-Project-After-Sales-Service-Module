# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError



class BookingInvoice(models.TransientModel):
    _name = 'booking.invoice'
    _description = 'Booking Invoice'

    @api.model
    def _default_product_id(self):
        product_id = self.env['ir.config_parameter'].sudo().get_param('tis_venue_booking.down_payment_product_id')
        return self.env['product.product'].browse(int(product_id))

    @api.model
    def _default_deposit_account_id(self):
        return self._default_product_id().property_account_income_id

    @api.model
    def _default_deposit_taxes_id(self):
        return self._default_product_id().taxes_id

    advance_payment_method = fields.Selection([

        ('all', 'Entire Invoice'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')], default='fixed')
    amount = fields.Float('Down Payment Amount', digits=dp.get_precision('Account'),
                          help="The amount to be invoiced in advance, taxes excluded.")
    deposit_account_id = fields.Many2one("account.account", string="Income Account",
                                         domain=[('deprecated', '=', False)],
                                         help="Account used for deposits", default=_default_deposit_account_id)
    deposit_taxes_id = fields.Many2many("account.tax", string="Customer Taxes", help="Taxes used for deposits",
                                        default=_default_deposit_taxes_id)
    product_id = fields.Many2one('product.product', string='Down Payment Product', domain=[('type', '=', 'service')],
                                 default=_default_product_id)

    def action_save_down_payment(self):
        """This function receives Downpayment amount received from customers
        and update the value of Downpayment in the booking record and
        returns the current downpayment amount received to generate invoice for downpayment"""

        booking = self.env['booking.booking'].browse(self._context.get('active_ids', []))
        payment_amount = 0
        if self.amount <= 0.00 or self.amount > booking.amount_total:
            raise UserError(
                _('The value of the down payment amount must be positive and should not be greater than Venue Total'))

        if self.advance_payment_method == 'percentage':
            payment_amount = booking.amount_total * self.amount / 100
            amount = booking.advance_amount + payment_amount
            if amount >= booking.amount_total:
                raise UserError(
                    _(
                        'The value of the down payment amount should not be greater than Venue Charge per day'))
            else:
                booking.write({'advance_amount': amount})
        elif self.advance_payment_method == 'fixed':
            payment_amount = self.amount
            amount = booking.advance_amount + payment_amount
            if amount >= booking.amount_total:
                raise UserError(
                    _(
                        'The value of the down payment amount should not be greater than Venue Charge per day'))
            else:
                booking.write({'advance_amount': amount})
        return payment_amount

    def _prepare_invoice(self):
        """ Prepare the dict of values to create the new invoice for a new booking order. """
        self.ensure_one()
        booking = self.env['booking.booking'].browse(self._context.get('active_ids', []))
        journal = self.env['account.move'].with_context(with_company=booking.company_id.id,
                                                        default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting journal for the company %s (%s).') % (
            booking.company_id.name, booking.company_id.id))

        invoice_vals = {
            'ref': booking.name or '',
            'move_type': 'out_invoice',
            'currency_id': booking.currency_id.id,
            'invoice_user_id': booking.user_id.id,
            'partner_id': booking.partner_id.id,
            'fiscal_position_id': booking.partner_id.property_account_position_id.id,
            'invoice_origin': booking.name,
            'invoice_payment_term_id': booking.partner_id.property_payment_term_id.id,
            'payment_reference': booking.name,
            'invoice_line_ids': [],
        }
        return invoice_vals

    def action_create_invoice(self):
        if not self.product_id:
            vals = self._prepare_deposit_product()
            self.product_id = self.env['product.product'].create(vals)
            self.env['ir.config_parameter'].sudo().set_param('tis_venue_booking.down_payment_product_id',
                                                             self.product_id.id)
        booking = self.env['booking.booking'].browse(self._context.get('active_ids', []))
        move = self.env['account.move']
        invoice_vals_list = self._prepare_invoice()
        if self.advance_payment_method == 'all':
            if booking.booking_charge and booking.venue_qty_to_invoice > 0:
                product_id = self.env['product.product'].browse \
                    (int(self.env['ir.config_parameter'].sudo().get_param('tis_venue_booking.venue_product_id')))
                invoice_vals_list['invoice_line_ids'].append((0, 0, {
                    'name': product_id.name,
                    'price_unit': booking.booking_charge,
                    'quantity': booking.venue_qty_to_invoice,
                    'product_id': product_id,
                    'product_uom_id': product_id.uom_id.id,
                    'tax_ids': [(6, 0, [tax.id for tax in booking.venue_id.taxes])],
                    'analytic_account_id': booking.venue_id.analytic_account_id.id or False,
                }))
            if booking.additional_charge and booking.additional_charge_to_invoice > 0:
                product_id = self.env['product.product'].browse(
                    int(self.env['ir.config_parameter'].sudo().get_param(
                        'tis_venue_booking.additional_charge_product_id')))
                invoice_vals_list['invoice_line_ids'].append((0, 0, {
                    'name': product_id.name,
                    'price_unit': booking.additional_charge,
                    'quantity': booking.additional_charge_to_invoice,
                    'product_id': product_id,
                    'product_uom_id': product_id.uom_id.id,
                    'analytic_account_id': booking.venue_id.analytic_account_id.id or False,

                }))






            if booking.booking_amenities_ids:
                product_id = self.env['product.product'].browse(int(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'tis_venue_booking.amenities_product_id')))
                incl_amenities = booking.booking_amenities_ids.filtered(lambda x: x.types == 'inclusive')
                print("wwwwwww", incl_amenities)
                if incl_amenities:
                    invoice_vals_list['invoice_line_ids'].append((0, 0, {
                        'name': 'Included amenities',
                        'price_unit': 0,
                        'quantity': 0,
                        'display_type': 'line_section'

                    }))
                    for rec in incl_amenities:
                        invoice_vals_list['invoice_line_ids'].append((0, 0, {
                            'name': rec.amenities_id.amenities_id.name,
                            'price_unit': rec.price,
                            'quantity': rec.qty_to_invoice,
                            'product_id': product_id,
                            'product_uom_id': product_id.uom_id.id,
                            'booking_line_ids': [(6, 0, [rec.id])],
                            'tax_ids': [(6, 0, [x.id for x in rec.taxes])],
                            'analytic_account_id': booking.venue_id.analytic_account_id.id or False,

                        }))
                excl_amenities = booking.booking_amenities_ids.filtered(lambda x: x.types == 'additional')
                print("wwwwwww", excl_amenities)
                if excl_amenities:
                    invoice_vals_list['invoice_line_ids'].append((0, 0, {
                        'name': 'Additional Amenities',
                        'price_unit': 0,
                        'quantity': 0,
                        'display_type': 'line_section'

                    }))
                    for record in excl_amenities:
                        invoice_vals_list['invoice_line_ids'].append((0, 0, {
                            'name': record.amenities_id.amenities_id.name,
                            'price_unit': record.price,
                            'quantity': record.qty_to_invoice,
                            'product_id': product_id,
                            'product_uom_id': product_id.uom_id.id,
                            'booking_line_ids': [(6, 0, [record.id])],
                            'tax_ids': [(6, 0, [x.id for x in record.taxes])],
                            'analytic_account_id': booking.venue_id.analytic_account_id.id or False,

                        }))



            if booking.advance_amount and booking.down_payment_to_invoice > 0:
                invoice_vals_list['invoice_line_ids'].append((0, 0, {
                    'name': _('Down Payment'),
                    'price_unit': booking.down_payment_to_invoice,
                    'quantity': -1.0,
                    'product_id': self.product_id.id,
                    'product_uom_id': self.product_id.uom_id.id,
                    'analytic_account_id': booking.venue_id.analytic_account_id.id or False,

                }))

        else:
            payment_amount = self.action_save_down_payment()
            invoice_vals_list['invoice_line_ids'].append((0, 0, {
                'name': _('Down Payment'),
                'price_unit': payment_amount,
                'quantity': 1.0,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_id.uom_id.id,
                'analytic_account_id': booking.venue_id.analytic_account_id.id or False,
            }))
        account_move = move.create(invoice_vals_list)

        booking._compute_invoice_count()


    def action_create_view_invoice(self):
        """This function is to view the invoice currently generated"""
        booking = self.env['booking.booking'].browse(self._context.get('active_ids', []))
        self.action_create_invoice()
        return booking.action_view_invoice()

    def _prepare_deposit_product(self):
        return {
            'name': 'Down payment',
            'type': 'service',
            'property_account_income_id': self.deposit_account_id.id,
            'taxes_id': [(6, 0, self.deposit_taxes_id.ids)],
            'company_id': False,
        }
