
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import base64
from io import BytesIO
import xlwt
from io import BytesIO
from xlsxwriter.workbook import Workbook

class PrintPurchaseReport(models.TransientModel):
    _name = 'print.purchase.tender.report'
    _description = 'Purchase Tender Pdf/XLS Report'

    selection = fields.Selection([('pdf', 'PDF'), ('xls', 'XLS')], default='pdf', string="Selection")
    purchase_agreement_ids = fields.Many2many('purchase.agreement', string="Purchase Agreements")

    @api.model
    def default_get(self, fields):
        res = super(PrintPurchaseReport, self).default_get(fields)
        active_ids = self.env['purchase.agreement'].browse(self._context.get('active_ids'))
        res['purchase_agreement_ids'] = [(6, 0, active_ids.ids)]
        return res

    def action_print_pdf(self):
        return self.env.ref('equip3_purchase_other_operation.report_purchase_tender_landscap').report_action(self)

    def action_print_xls(self):
        file_name = 'Purchase Tender Report.xls'
        workbook = xlwt.Workbook()
        format0 = xlwt.easyxf('font:height 500,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format1 = xlwt.easyxf('align: horiz left')
        format2 = xlwt.easyxf('font:height 230,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format3 = xlwt.easyxf('font:bold True;align: horiz center')
        format4 = xlwt.easyxf(
            "align: horiz right;pattern: \
            fore_colour white;",
            num_format_str="#,##0.00",
        )
        format5 = xlwt.easyxf('font:bold True;align: horiz left')
        format6 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        for record in self.purchase_agreement_ids:
            vendors = record._get_vendors()
            vendors_data = []
            vendor_lines = []
            for vendor in vendors:
                vendors_data.extend([vendor_id for vendor_id in vendor])
                vendor_lines.extend([{'name': vendor_id.name, 'id': vendor_id.id} for vendor_id in vendor])
            purchase_order_line = record._get_purchase_vendor_lines(vendors_data)
            vendor_name = record._get_vendors_name()
            name = record.name
            sheet = workbook.add_sheet('Purchase Tender: %s' %(name))
            sheet.col(0).width = int(25*390)
            sheet.write_merge(0, 2, 0, 6, 'Purchase Tender: %s' %(name), format0)
            row = 4
            sheet.write(5, 0, "Purchase Representative:", format5)
            pr_name = record.sh_purchase_user_id.name
            sheet.write(5, 1, pr_name, format5)
            sheet.write(6, 0, "Vendor:", format5)
            sheet.write(6, 1, vendor_name, format5)
            sheet.write(5, 3, "Ordering Date:", format5)
            date = record.sh_order_date.strftime('%m-%d-%Y') 
            sheet.write(5, 4, date, format5)
            sheet.write(6, 3, "State:", format5)
            state = dict(record._fields['state2'].selection).get(record.state2, '')
            sheet.write(6, 4, state, format5)
            if record.state2 == 'bid_submission':
                sheet.write(7, 3, "Submission Expiry Date:", format5)
                exp_date = record.sh_bid_agreement_deadline.strftime('%m-%d-%Y')
                sheet.write(7, 4, exp_date, format5)
            elif record.state2 == 'bid_selection':
                sheet.write(7, 3, "Selection Expiry Date:", format5)
                exp_date = record.sh_bid_selection_agreement_deadline.strftime('%m-%d-%Y')
                sheet.write(7, 4, exp_date, format5)
            row = 11
            col_1 = 1
            col_2 = 2
            for vendor in vendor_lines:
                v_name = vendor.get('name')
                sheet.col(col_1).width = int(25*270)
                sheet.col(col_2).width = int(25*270)
                sheet.write_merge(12, 12, col_1, col_2, v_name, format2)
                comparison_id = record.comparison_ids.filtered(lambda r:r.partner_id.id == vendor.get('id'))
                final_star = int(comparison_id.final_star) * '*'
                final_star_int = int(comparison_id.final_star)
                on_time_rate = round(comparison_id.on_time_rate, 2)
                fulfillment = round(comparison_id.fulfillment, 2)
                message = ""
                message += ' ' + str(final_star)
                message += ' ' + str(final_star_int)
                message += ' ' + '|'
                message += ' ' + str(on_time_rate)
                message += ' ' + '%'
                message += ' ' + 'Delivery on Schedule'
                message += ' ' + '|'
                message += ' ' + str(fulfillment)
                message += ' ' + '%'
                message += ' ' + 'Fulfillment'
                sheet.write_merge(13, 13, col_1, col_2, message, format6)
                sheet.write(14, col_1, 'Quantity', format5)
                sheet.write(15, col_2, 'Unit Price', format5)
                col_1 += 2
                col_2 += 2
            row = 16
            for line in purchase_order_line:
                colm_1 = 1
                colm_2 = 2
                sheet.write(row, 0, line.get('product_name'), format1)
                for vendor in line.get('vendor_lines'):
                    sheet.write(row, colm_1, vendor.get('quantity'), format4)
                    sheet.write(row, colm_2, vendor.get('unit_price'), format4)
                    colm_1 += 2
                    colm_2 +=2
                row+= 1
        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['purchase.tender.xls.report'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': file_name})
        fp.close()
        return{
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=purchase.tender.xls.report&field=excel_file&download=true&id=%s&filename=%s' % (export_id.id, export_id.file_name),
            'target': 'self',
        }
