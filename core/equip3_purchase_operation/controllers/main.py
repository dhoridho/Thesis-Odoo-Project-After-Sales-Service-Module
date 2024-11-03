# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io

import xlsxwriter

from odoo import http
from odoo.http import request, content_disposition


class PurchaseComparison(http.Controller):
    @http.route("/purchase_comparison/", type="http", auth="user", website=True, csrf=False)
    def purchase_comparison_routes(self, purchase_comp_rpt_type, **data):
        supplier_ids = []; values = []; product = {}; rfq_info = []; rfq_ids = []
        rfq_data = data.get('rfq_ids')[1:][:-1].split(", ")
        for record in request.env['purchase.order'].sudo().search([('id', 'in', rfq_data)], order='id'):
            # Append RFQ ids
            rfq_ids.append(record.id)

            # Append FRQ
            rfq_info.append({'rfq_name': record.name, 'amount': '{:,.0f}'.format(record.amount_untaxed)})

            # Append supplier
            supplier_ids.append({'sname': record.partner_id.name})

            # Append Products and quantity
            for line in record.order_line:
                if line.product_id.id not in product:
                    product[line.product_id.id] = {'product_name': line.product_id.name,
                                                    'records': {record.id: {'price': '{:,.0f}'.format(line.price_unit), 'uom': line.product_uom.name,'qty': '{:,.2f}'.format(line.product_qty), 'subtotal': '{:,.0f}'.format(line.product_qty*line.price_unit)}}}
                else:
                    product[line.product_id.id]['records'][record.id] = {'price': '{:,.0f}'.format(line.price_unit), 'uom': line.product_uom.name,
                                                   'qty': '{:,.2f}'.format(line.product_qty), 'subtotal': '{:,.0f}'.format(line.product_qty*line.price_unit)}
        for rec in product:
            product_data = product[rec]
            product_data['record'] = []
            for record in rfq_ids:
                if record not in product_data['records']:
                    product_data['record'].append({'price': "", 'uom': "", 'qty': "", 'subtotal': ""})
                else:
                    product_data['record'].append(product_data['records'][record])
            values.append(product_data)

        report_column = (len(rfq_ids)*3)+1

        if purchase_comp_rpt_type == "htm":
            return request.render('equip3_purchase_operation.purchase_comparison', {'data': values, 'supplier': supplier_ids, 'rfq_ids': rfq_ids, 'rfq_info': rfq_info, 'report_column': report_column})
        elif purchase_comp_rpt_type == "xls":
            response = request.make_response(
                None,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition('Purchase_Comparison' + '.xlsx')),
                ]
            )
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet()

            cell_format1 = workbook.add_format({'align': 'left', 'bold': True, 'font_size': '12', 'border': 1})
            cell_format2 = workbook.add_format({'bg_color': '#CCCCCC', 'align': 'left', 'bold': True, 'font_size': '12', 'border': 1})
            head = workbook.add_format({'align': 'center', 'bold': True, 'font_size': '20'})
            txt1 = workbook.add_format({'text_wrap': True, 'font_size': '10', 'border': 1})
            txt2 = workbook.add_format({'bg_color': '#CCCCCC', 'text_wrap': True, 'font_size': '10', 'border': 1})
            cell_align1 = workbook.add_format({'align': 'center', 'bold': True, 'font_size': '12', 'border': 1})
            cell_align2 = workbook.add_format({'bg_color': '#CCCCCC', 'align': 'center', 'bold': True, 'font_size': '12', 'border': 1})
            format_qty1 = workbook.add_format({'text_wrap': True, 'align': 'right', 'font_size': '10', 'border': 1, 'num_format': '#,##0.00'})
            format_qty2 = workbook.add_format({'bg_color': '#CCCCCC', 'text_wrap': True, 'align': 'right', 'font_size': '10', 'border': 1, 'num_format': '#,##0.00'})
            format_amount1 = workbook.add_format({'align': 'center', 'bold': True, 'border': 1, 'num_format': '#,##0'})
            format_amount2 = workbook.add_format({'bg_color': '#CCCCCC','align': 'center', 'bold': True, 'border': 1, 'num_format': '#,##0'})

            c = 1
            sheet.set_column(c, c, 35)
            c += 1
            for rfq in rfq_info:
                sheet.set_column(c, c, 14)
                c += 1
                sheet.set_column(c, c, 10)
                c += 1
                sheet.set_column(c, c, 10)
                c += 1

            r = 1
            c = 1

            sheet.merge_range(r, c, r, c+report_column-1, 'PURCHASE COMPARISON CHART', head)
            r += 1
            sheet.write(r, c, 'Reference', cell_format2)
            c += 1
            for rfq in rfq_info:
                sheet.merge_range(r, c, r, c+2, rfq['rfq_name'], cell_align2)
                c += 3

            r += 1
            c = 1
            sheet.write(r, c, 'Vendor', cell_format1)
            c += 1
            for sname in supplier_ids:
                sheet.merge_range(r, c, r, c+2, sname['sname'], cell_align1)
                c += 3

            r += 1
            c = 1
            sheet.write(r, c, 'Products', cell_format2)
            c += 1
            for rec in rfq_info:
                sheet.write(r, c, 'Quantity', cell_align2)
                c += 1
                sheet.write(r, c, 'Unit Price', cell_align2)
                c += 1
                sheet.write(r, c, 'Subtotal', cell_align2)
                c += 1

            r += 1
            c = 1
            for product in values:
                sheet.write(r, c, product['product_name'], (txt2 if r % 2 == 0 else txt1))
                c += 1
                for rec in product['record']:
                    sheet.write(r, c, rec['qty']+" "+rec['uom'], (txt2 if r % 2 == 0 else txt1))
                    c += 1
                    sheet.write(r, c, rec['price'], (format_qty2 if r % 2 == 0 else format_qty1))
                    c += 1
                    sheet.write(r, c, rec['subtotal'], (format_qty2 if r % 2 == 0 else format_qty1))
                    c += 1

                r += 1
                c = 1

            c = 1
            sheet.write(r, c, 'Total', (format_amount2 if r % 2 == 0 else format_amount1))
            c += 1
            for rfq in rfq_info:
                sheet.merge_range(r, c, r, c + 2, rfq['amount'], (format_amount2 if r % 2 == 0 else format_amount1))
                c += 3

            workbook.close()
            output.seek(0)
            response.stream.write(output.read())
            output.close()
            return response
        else:
            datas = {
                'data': values, 'supplier': supplier_ids, 'rfq_ids': rfq_ids, 'rfq_info': rfq_info,
                 'report_column': report_column
            }
            pdf, _ = request.env.ref('equip3_purchase_operation.action_report_purchase_comparison').sudo()._render_qweb_pdf([], data=datas)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
