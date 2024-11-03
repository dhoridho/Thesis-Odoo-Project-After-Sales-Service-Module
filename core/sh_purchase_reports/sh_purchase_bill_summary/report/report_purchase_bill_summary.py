# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models,fields
import pytz
from datetime import datetime,timedelta

class PurchaseBillSummary(models.AbstractModel):
    _name = 'report.sh_purchase_reports.sh_po_bill_summary_doc'
    _description = 'Purchase Bill Summary report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        purchase_order_obj = self.env["purchase.order"]
        vendor_order_dic = {}
        date_start = False
        date_stop = False
        if data['sh_start_date']:
            date_start = fields.Datetime.from_string(data['sh_start_date'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['sh_end_date']:
            date_stop = fields.Datetime.from_string(data['sh_end_date'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        if data.get('sh_partner_ids', False):
            for partner_id in data.get('sh_partner_ids'):
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ('state','in',['purchase','done']),
                    ('partner_id','=',partner_id)
                ]
                if data.get('sh_status') == 'both':
                    domain.append(('invoice_ids.state','in',['posted']))
                elif data.get('sh_status') == 'open':
                    domain.append(('invoice_ids.state','in',['posted']))
                    domain.append(('invoice_ids.amount_residual','!=',0.0))
                elif data.get('sh_status') == 'paid':
                    domain.append(('invoice_ids.state','in',['posted']))
                    domain.append(('invoice_ids.amount_residual','=',0.0))
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                search_orders = purchase_order_obj.sudo().search(domain)
                invoice_ids = []
                if search_orders:
                    for order in search_orders:
                        if order.invoice_ids:
                            for invoice in order.invoice_ids: 
                                if invoice.id not in invoice_ids:
                                    invoice_ids.append(invoice.id)
                                order_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order,
                                    'invoice_number': invoice.name,
                                    'invoice_date': invoice.invoice_date,
                                    'invoice_currency_id':invoice.currency_id.id,
                                }
                                if invoice.move_type == 'in_invoice':
                                    order_dic.update({
                                        'invoice_amount':invoice.amount_total,
                                        'invoice_paid_amount':invoice.amount_total - invoice.amount_residual,
                                        'due_amount' : invoice.amount_residual,
                                    })
                                elif invoice.move_type == 'in_refund':
                                    order_dic.update({
                                        'invoice_amount':-(invoice.amount_total),
                                        'invoice_paid_amount':-(invoice.amount_total - invoice.amount_residual),
                                        'due_amount' : -(invoice.amount_residual),
                                    })
                                order_list.append(order_dic)
                search_partner = self.env['res.partner'].sudo().search([
                    ('id', '=', partner_id)
                ], limit=1)
                if search_partner:
                    vendor_order_dic.update({search_partner.name_get()[0][1]: order_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'vendor_order_dic': vendor_order_dic,
        })
        return data
