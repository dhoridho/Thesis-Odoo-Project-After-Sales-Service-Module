# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import date
import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    average_payment_days = fields.Float(string="Average Payment Days",compute="_compute_payment_days")

    @api.depends('invoice_ids')
    def _compute_payment_days(self):
        today = date.today()
        for rec in self:
            # total_index = 0
            # total_amount = 0
            # for invoice in rec.invoice_ids.filtered(lambda r: r.state == 'posted' and r.move_type == 'out_invoice' and r.amount_residual != 0):
            #     days_till_today = (today - invoice.invoice_date).days
            #     index = invoice.amount_residual * days_till_today
            #     total_index += index
            #     total_amount += invoice.amount_residual
            # _logger.info("\n\n\nTotal Index %s------", total_index)
            # _logger.info("\n\n\nTotal Amount %s------", total_amount)
            # if total_amount != 0:
            #     rec.average_payment_days = total_index / total_amount
            # else:
            #     rec.average_payment_days = 0
            total_index = 0
            total_days = 0
            for invoice in rec.invoice_ids.filtered(lambda r: r.state == 'posted' and r.move_type == 'out_invoice' and r.payment_state == 'paid'):
                account_payment = self.env['account.payment'].search([('ref','=',invoice.name)], limit=1, order='id desc')
                if account_payment:
                    payment_date = account_payment.date
                    total_days += (payment_date - invoice.invoice_date).days
                    total_index += 1

            if total_index != 0:
                rec.average_payment_days = total_days / total_index
            else:
                rec.average_payment_days = 0