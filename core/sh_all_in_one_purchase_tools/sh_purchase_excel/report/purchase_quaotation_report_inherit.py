# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models
import xlwt
import base64
from io import BytesIO


class PurchaseQuotationExcelExtended(models.Model):
    _name = "purchase.quotation.excel.extended"
    _description = 'Purchase Quotation Excel Extended'

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):

        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=purchase.quotation.excel.extended&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class PurchaseOrderReport(models.TransientModel):
    _name = "purchase.quotation.report"
    _description = 'Puechase Quotation Report'

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
                }
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

            worksheet = workbook.add_sheet(purchase_order.name)

            worksheet.col(0).width = int(25*260)
            worksheet.col(2).width = int(25*260)
            worksheet.col(3).width = int(18*290)
            worksheet.col(4).width = int(18*290)
            worksheet.col(5).width = int(18*260)

            if purchase_order.state == 'draft':
                worksheet.write_merge(
                    0, 1, 0, 5, 'Quotation : ' + final_value['name'], heading_format)

            elif purchase_order.state in ['sent', 'to approve']:

                worksheet.write_merge(
                    0, 1, 0, 5, 'Quotation # ' + final_value['name'], heading_format)

            elif purchase_order.state == 'cancel':
                worksheet.write_merge(
                    0, 1, 0, 5, 'Quotation : ' + final_value['name'], heading_format)

            elif purchase_order.state in ['purchase', 'done']:
                worksheet.write_merge(
                    0, 1, 0, 5, 'Purchase Order Confirmation : ' + final_value['name'], heading_format)

            worksheet.write(3, 0, "Customer", format1)
            worksheet.write_merge(
                3, 3, 1, 2, final_value['partner_id'], format1)

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
                worksheet.write_merge(
                    7, 7, 1, 2, purchase_order.partner_id.phone, format3)

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
                worksheet.write_merge(
                    7, 7, 4, 5, purchase_order.currency_id.name, format3)

            worksheet.write(8, 0, "Mobile", format1)
            if purchase_order.partner_id.mobile:
                worksheet.write_merge(
                    8, 8, 1, 2, purchase_order.partner_id.mobile, format3)

            worksheet.write(8, 3, "Our Order Reference", format1)
            worksheet.write_merge(8, 8, 4, 5, final_value['name'], format3)

            row = 11
            worksheet.write_merge(row, row, 0, 1, "Product", bold)
            worksheet.write_merge(row, row, 2, 3, "Description", bold)
            worksheet.write(row, 4, "Date Req.", bold)
            worksheet.write(row, 5, "Qty", bold)

            row = 12

            for rec in order_lines:
                if rec.get('product_id'):
                    worksheet.write_merge(
                        row, row, 0, 1, rec.get('product_id'), format3)
                if rec.get('description'):
                    worksheet.write_merge(
                        row, row, 2, 3, rec.get('description'), format3)
                if rec.get('date_planned'):
                    worksheet.write(row, 4, str(
                        rec.get('date_planned')), format3)
                if rec.get('product_qty'):
                    worksheet.write(row, 5, rec.get('product_qty'), format4)
                row += 1

            row += 2
            if final_value['notes']:
                worksheet.write_merge(
                    row, row+1, 0, 3, final_value['notes'], format3)

        filename = ('Purchase Quotation Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['purchase.quotation.excel.extended'].sudo().create({
            'excel_file': base64.encodebytes(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'res_id': export_id.id,
            'res_model': 'purchase.quotation.excel.extended',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
