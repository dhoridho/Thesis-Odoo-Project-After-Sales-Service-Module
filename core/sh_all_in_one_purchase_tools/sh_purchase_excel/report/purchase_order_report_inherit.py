# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models
import xlwt
import base64
from io import BytesIO


class PurchaseExcelExtended(models.Model):
    _name = "purchase.excel.extended"
    _description = 'Purchase Excel Extended'

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):

        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=purchase.excel.extended&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class PurchaseOrderReport(models.TransientModel):
    _name = "purchase.order.report"
    _description = 'Purchase Order Report'

    purchase_order_id = fields.Many2one('purchase.order', "Purchase Order")

    def action_purchase_report(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        row = 1

        final_value = {}
        active_id = self.env.context.get('active_ids')
        for purchase_order in self.purchase_order_id.browse(active_id):
            order_lines = []
            for lines in purchase_order.order_line:
                product = {
                    'product_id': lines.product_id.name,
                    'description': lines.name,
                    'product_qty': lines.product_qty,
                    'date_planned': lines.date_planned,
                    'product_uom': lines.product_uom.name,
                    'price_unit': lines.price_unit,
                    'price_subtotal': lines.price_subtotal,
                }
                if lines.taxes_id:
                    taxes = []
                    for tax_id in lines.taxes_id:
                        taxes.append(tax_id.name)
                    product['taxes_id'] = taxes
                order_lines.append(product)
            final_value['partner_id'] = purchase_order.partner_id.name
            final_value['name'] = purchase_order.name
            final_value['date_order'] = purchase_order.date_order
            final_value['currency_id'] = purchase_order.currency_id
            final_value['payment_term_id'] = purchase_order.payment_term_id.name
            final_value['partner_ref'] = purchase_order.partner_ref
            final_value['state'] = dict(self.env['purchase.order'].fields_get(
                allfields=['state'])['state']['selection'])[purchase_order.state]
            final_value['origin'] = purchase_order.origin
            final_value['amount_untaxed'] = purchase_order.amount_untaxed
            final_value['amount_tax'] = purchase_order.amount_tax
            final_value['amount_total'] = purchase_order.amount_total
            final_value['notes'] = purchase_order.notes

            format1 = xlwt.easyxf('font:bold True;;align: horiz left')
            format3 = xlwt.easyxf('align: horiz left')
            format4 = xlwt.easyxf('align: horiz right')
            format7 = xlwt.easyxf('borders:top thick;align: horiz right')
            format8 = xlwt.easyxf('font:bold True;borders:top thick;')

            worksheet = workbook.add_sheet(purchase_order.name)

            worksheet.col(0).width = int(25*260)
            worksheet.col(1).width = int(25*260)
            worksheet.col(2).width = int(16*290)
            worksheet.col(3).width = int(16*260)
            worksheet.col(4).width = int(15*260)
            worksheet.col(5).width = int(14*260)
            worksheet.col(6).width = int(14*260)
            worksheet.col(7).width = int(14*260)

            if purchase_order.state == 'draft':
                worksheet.write_merge(0, 1, 0, 7, 'Quotation : ' + final_value['name'], heading_format)

            elif purchase_order.state in ['sent', 'to approve']:

                worksheet.write_merge(0, 1, 0, 7, 'Purchase Order # ' + final_value['name'], heading_format)

            elif purchase_order.state == 'cancel':
                worksheet.write_merge(0, 1, 0, 7, 'Purchase Order : ' + final_value['name'], heading_format)

            elif purchase_order.state in ['purchase', 'done']:
                worksheet.write_merge(0, 1, 0, 7, 'Purchase Order Confirmation : ' + final_value['name'], heading_format)

            worksheet.write(3, 0, "Customer", format1)
            worksheet.write_merge(3, 3, 1, 2, final_value['partner_id'], format1)

            address = ""
            if purchase_order.partner_id.street:
                address += purchase_order.partner_id.street
            if purchase_order.partner_id.street2:
                address += " "+purchase_order.partner_id.street2
            if purchase_order.partner_id.city:
                address += "\n"+purchase_order.partner_id.city
            if purchase_order.partner_id.state_id:
                address += " "+purchase_order.partner_id.state_id.name
            if purchase_order.partner_id.zip:
                address += " "+purchase_order.partner_id.zip
            if purchase_order.partner_id.country_id:
                address += "\n"+purchase_order.partner_id.country_id.name
            if address:
                worksheet.write_merge(4, 6, 1, 2, address, format3)

            worksheet.write(7, 0, "ContactNo", format1)
            if purchase_order.partner_id.phone:
                worksheet.write_merge(7, 7, 1, 2, purchase_order.partner_id.phone, format3)

            worksheet.write(3, 3, 'Date', format1)
            worksheet.write_merge(3, 3, 4, 5, str(
                final_value['date_order']), format3)
            worksheet.write(4, 3, 'Payment Term', format1)
            if final_value['payment_term_id']:
                worksheet.write_merge(
                    4, 4, 4, 5, final_value['payment_term_id'], format3)
            else:
                worksheet.write_merge(
                    4, 4, 4, 5, "No Payment Terms Defined", format3)
            worksheet.write(5, 3, 'Vendor Reference', format1)
            if final_value['partner_ref']:
                worksheet.write_merge(5, 5, 4, 5, str(
                    final_value['partner_ref']), format3)
            else:
                worksheet.write_merge(
                    5, 5, 4, 5, "No Customer Reference Defined", format3)
            worksheet.write(6, 3, 'State', format1)
            worksheet.write_merge(6, 6, 4, 5, final_value['state'], format3)

            worksheet.write(7, 3, "Currency", format1)
            if final_value['currency_id']:
                worksheet.write_merge(7, 7, 4, 5, purchase_order.currency_id.name, format3)

            worksheet.write(8, 0, "Mobile", format1)
            if purchase_order.partner_id.mobile:
                worksheet.write_merge(8, 8, 1, 2, purchase_order.partner_id.mobile, format3)

            worksheet.write(8, 3, "Our Order Reference", format1)
            worksheet.write_merge(8, 8, 4, 5, final_value['name'], format3)

            worksheet.write(11, 0, "Product", bold)
            worksheet.write(11, 1, "Description", bold)
            worksheet.write(11, 2, "Date Req.", bold)
            worksheet.write(11, 3, "Qty", bold)
            worksheet.write(11, 4, "Product Uom", bold)
            worksheet.write(11, 5, "Unit Price", bold)
            worksheet.write(11, 6, "Taxes", bold)
            worksheet.write(11, 7, "Subtotal", bold)

            row = 12

            for rec in order_lines:
                if rec.get('product_id'):
                    worksheet.write(row, 0, rec.get('product_id'), format3)
                if rec.get('description'):
                    worksheet.write(row, 1, rec.get('description'), format3)
                if rec.get('date_planned'):
                    worksheet.write(row, 2, str(
                        rec.get('date_planned')), format3)
                if rec.get('product_qty'):
                    worksheet.write(row, 3, rec.get('product_qty'), format4)
                if rec.get('product_uom'):
                    worksheet.write(row, 4, rec.get('product_uom'), format4)
                if rec.get('price_unit'):
                    worksheet.write(row, 5, rec.get('price_unit'), format4)
                if rec.get('taxes_id'):
                    worksheet.write(row, 6, ",".join(
                        rec.get('taxes_id')), format4)
                else:
                    worksheet.write(row, 6, '', format4)

                if final_value['currency_id'].position == "before":
                    worksheet.write(row, 7, rec.get('price_subtotal'), format4)
                else:
                    worksheet.write(row, 7, rec.get('price_subtotal'), format4)
                row += 1

            row += 2
            worksheet.write_merge(row, row, 5, 6, 'Total Without Taxes', format8)
            worksheet.write_merge(row+1, row+1, 5, 6, 'Taxes', format8)
            worksheet.write_merge(row+2, row+2, 5, 6, 'Total', format8)
            if final_value['currency_id'].position == "before":
                worksheet.write(
                    row, 7,  final_value['amount_untaxed'], format7)
                worksheet.write(row+1, 7, final_value['amount_tax'], format7)
                worksheet.write(row+2, 7, final_value['amount_total'], format7)
            else:
                worksheet.write(row, 7, final_value['amount_untaxed'], format7)
                worksheet.write(row+1, 7, final_value['amount_tax'], format7)
                worksheet.write(row+2, 7, final_value['amount_total'], format7)
            row += 4
            if final_value['notes']:
                worksheet.write_merge(row, row+1, 0, 3, final_value['notes'], format3)

        filename = ('Purchase Order Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['purchase.excel.extended'].sudo().create({
            'excel_file': base64.encodebytes(fp.getvalue()),
                                        'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'res_id': export_id.id,
                'res_model': 'purchase.excel.extended',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
        }
