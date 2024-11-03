from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
import xlwt
import operator
import base64
from io import BytesIO
import pytz
from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import float_is_zero

class ShPurchaseDetailsReportWizard(models.TransientModel):
    _inherit = "sh.purchase.details.report.wizard"

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_report(self):
        datas = self.read()[0]
        data = {'date_start': self.start_date.strftime('%d %B %Y'), 'date_stop': self.end_date.strftime('%d %B %Y'),'res_date_start': self.start_date, 'res_date_stop': self.end_date,
                'company_ids': self.company_ids.ids, 'state': self.state, 'branch_ids': self.branch_ids.ids}

        return self.env.ref('sh_purchase_reports.sh_purchase_details_report_action').report_action([], data=data)

    def print_purchase_detail_xls_report(self,):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:height 225,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        b1 = xlwt.easyxf('font:bold True;align: horiz left')
        bold_right = xlwt.easyxf('align: horiz right')
        center = xlwt.easyxf('font:bold True;align: horiz center')
        row = 1

        state = False

        data = {}
        data = dict(data or {})

        worksheet = workbook.add_sheet(
            u'Purchase Details', cell_overwrite_ok=True)
        worksheet.write_merge(0, 1, 0, 3, 'Purchase Details', heading_format)

        date_start = False
        date_stop = False
        if self.start_date:
            date_start = fields.Datetime.from_string(self.start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.end_date:
            date_stop = fields.Datetime.from_string(self.end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.start_date),
                                                                           DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.end_date),
                                                                         DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        # avoid a date_stop smaller than date_start
        worksheet.write_merge(2, 2, 0, 3, start_date +
                              " to " + end_date, center)
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
        ]
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        if self.branch_ids:
            domain.append(('branch_id', 'in', self.branch_ids.ids))
        if state and state == 'done':
            domain.append(('state', 'in', ['purchase', 'done']))

        orders = self.env['purchase.order'].sudo().search(domain)

        user_currency = self.env.user.company_id.currency_id

        total = 0.0
        products_purchased = {}
        taxes = {}
        invoice_id_list = []
        for order in orders:
            if user_currency != order.partner_id.currency_id:
                total += order.partner_id.currency_id.compute(
                    order.amount_total, user_currency)
            else:
                total += order.amount_total
            currency = order.currency_id
            for line in order.order_line:
                if not line.display_type:
                    key = (line.product_id, line.price_unit)
                    products_purchased.setdefault(key, 0.0)
                    products_purchased[key] += line.product_qty

                    if line.taxes_id:
                        line_taxes = line.taxes_id.compute_all(
                            line.price_unit * (1 / 100.0), currency, line.product_qty, product=line.product_id, partner=line.order_id.partner_id or False)
                        for tax in line_taxes['taxes']:
                            taxes.setdefault(
                                tax['id'], {'name': tax['name'], 'total': 0.0})
                            taxes[tax['id']]['total'] += tax['amount']
            if order.invoice_ids:
                f_invoices = order.invoice_ids.filtered(
                    lambda inv: inv.state not in ['draft', 'cancel'])
                if f_invoices:
                    invoice_id_list += f_invoices.ids

        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]

        search_journals = account_journal_obj.sudo().search([
            ('type', 'in', ['bank', 'cash'])
        ])

        journal_wise_total_payment_list = []
        if invoice_id_list and search_journals:
            for journal in search_journals:
                domain = []
                invoices = self.env['account.move'].browse(invoice_id_list)
                if invoices:
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('debit_move_id', 'in', invoices.mapped('line_ids').ids), ('credit_move_id', 'in', invoices.mapped('line_ids').ids)])
                    if reconcile_lines:
                        domain.append(('|'))
                        domain.append(
                            ('invoice_line_ids.id', 'in', reconcile_lines.mapped('credit_move_id').ids))
                        domain.append(
                            ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids))
                        domain.append(
                            ("payment_type", "in", ["inbound", "outbound"]))
                        domain.append(("journal_id", "=", journal.id))
                        domain.append(("partner_type", "in", ["supplier"]))

                payments = account_payment_obj.sudo().search(domain)
                paid_total = 0.0
                if payments:
                    for payment in payments:
                        paid_total += payment.amount

                if {'name': journal.name, "total": paid_total} not in journal_wise_total_payment_list:
                    journal_wise_total_payment_list.append(
                        {"name": journal.name, "total": paid_total})
        else:
            journal_wise_total_payment_list = []

        var = {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': journal_wise_total_payment_list,
            'company_name': self.env.user.company_id.name,
            'taxes': taxes.values(),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'uom': product.uom_id.name
            } for (product, price_unit), qty in products_purchased.items()], key=lambda l: l['product_name'])
        }
        list1 = var.get("products")
        worksheet.write_merge(4, 4, 0, 3, "Products", bold_center)
        worksheet.col(0).width = int(25 * 260)
        worksheet.col(1).width = int(25 * 260)
        worksheet.col(2).width = int(12 * 260)
        worksheet.col(3).width = int(14 * 260)

        worksheet.write(5, 0, "Product", bold)
        worksheet.write(5, 1, "Quantity", bold)
        worksheet.write(5, 2, "", bold)
        worksheet.write(5, 3, "Price Unit", bold)
        row = 6
        for rec in list1:
            worksheet.write(row, 0, rec['product_name'])
            worksheet.write(row, 1, str(rec['quantity']), bold_right)
            if rec['uom'] != 'Unit(s)':
                worksheet.write(row, 2, rec['uom'])
            worksheet.write(row, 3, str(rec['price_unit']), bold_right)
            row += 1
        row += 1
        list2 = var.get("payments")
        worksheet.write_merge(row, row, 0, 3, "Payments", bold_center)
        row += 1
        worksheet.write_merge(row, row, 0, 1, "Name", bold)
        worksheet.write_merge(row, row, 2, 3, "Total", bold)
        row += 1
        for rec1 in list2:
            worksheet.write_merge(row, row, 0, 1, rec1['name'])
            worksheet.write_merge(
                row, row, 2, 3, str(rec1['total']), bold_right)
            row += 1
        row += 1
        list3 = var.get("taxes")
        worksheet.write_merge(row, row, 0, 3, "Taxes", bold_center)
        row += 1
        worksheet.write_merge(row, row, 0, 1, "Name", bold)
        worksheet.write_merge(row, row, 2, 3, "Total", bold)
        row += 1
        for rec2 in list3:
            worksheet.write_merge(row, row, 0, 1, rec2['name'])
            worksheet.write_merge(row, row, 2, 3, rec2['total'], bold_right)
            row += 1
        row += 2
        list4 = var.get("total_paid")
        worksheet.write_merge(row, row, 0, 3, "Total: " + " " + str(list4), b1)
        filename = ('Purchase Detail Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['purchase.detail.excel.extended'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'name': 'Purchase Details Report',
            'res_id': export_id.id,
            'res_model': 'purchase.detail.excel.extended',
            'view_mode': 'form',
            'target': 'new',
        }

class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_pr_details_report_doc'

    def _get_street(self, partner):
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, company_ids=False, state=False, branch_ids=False):
        """ Serialise the orders of the day information

        params: date_start, date_stop string representing the datetime of order
        """
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if date_stop:
            date_stop = fields.Datetime.from_string(date_stop)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids.ids))

        if branch_ids:
            domain.append(('branch_id', 'in', branch_ids.ids))

        if state and state == 'done':
            domain.append(('state', 'in', ['purchase', 'done']))

        orders = self.env['purchase.order'].sudo().search(domain)
        user_currency = self.env.user.company_id.currency_id
        total = 0.0
        products_purchased = {}
        taxes = {}
        invoice_id_list = []
        for order in orders:
            if user_currency != order.partner_id.currency_id:
                total += order.partner_id.currency_id.compute(
                    order.amount_total, user_currency)
            else:
                total += order.amount_total
            currency = order.currency_id
            for line in order.order_line:
                if not line.display_type:
                    key = (line.product_id, line.price_unit)
                    products_purchased.setdefault(key, 0.0)
                    products_purchased[key] += line.product_qty
                    if line.taxes_id:
                        line_taxes = line.taxes_id.compute_all(
                            line.price_unit * (1/100.0), currency, line.product_qty, product=line.product_id, partner=line.order_id.partner_id or False)
                        for tax in line_taxes['taxes']:
                            taxes.setdefault(
                                tax['id'], {'name': tax['name'], 'total': 0.0})
                            taxes[tax['id']]['total'] += tax['amount']

            if order.invoice_ids:
                f_invoices = order.invoice_ids.filtered(
                    lambda inv: inv.state not in ['draft', 'cancel'])
                if f_invoices:
                    invoice_id_list += f_invoices.ids

        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]
        search_journals = account_journal_obj.sudo().search([
            ('type', 'in', ['bank', 'cash'])
        ])

        journal_wise_total_payment_list = []
        if invoice_id_list and search_journals:
            for journal in search_journals:
                domain = []
                invoices = self.env['account.move'].browse(invoice_id_list)
                if invoices:
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('debit_move_id', 'in', invoices.mapped('line_ids').ids), ('credit_move_id', 'in', invoices.mapped('line_ids').ids)])
                    if reconcile_lines:
                        domain.append(('|'))
                        domain.append(
                            ('invoice_line_ids.id', 'in', reconcile_lines.mapped('credit_move_id').ids))
                        domain.append(
                            ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids))
                        domain.append(
                            ("payment_type", "in", ["inbound", "outbound"]))
                        domain.append(("journal_id", "=", journal.id))
                        domain.append(("partner_type", "in", ["supplier"]))
                payments = account_payment_obj.sudo().search(domain)
                paid_total = 0.0
                if payments:
                    for payment in payments:
                        paid_total += payment.amount
                if {'name': journal.name, "total": paid_total} not in journal_wise_total_payment_list:
                    journal_wise_total_payment_list.append(
                        {"name": journal.name, "total": paid_total})
        else:
            journal_wise_total_payment_list = []
        company_id = self.env.company
        street_company = self._get_street(company_id.partner_id)
        address_company = self._get_address_details(company_id.partner_id)
        return {
            'currency': user_currency,
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': journal_wise_total_payment_list,
            'company_name': self.env.user.company_id.name,
            'taxes': taxes.values(),
            'company_id': company_id,
            'street_company': street_company,
            'address_company': address_company,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'uom': product.uom_id.name
            } for (product, price_unit), qty in products_purchased.items()], key=lambda l: l['product_name'])
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        company_ids = self.env['res.company'].browse(data['company_ids'])
        branch_ids = self.env['res.branch'].browse(data['branch_ids'])
        data.update(self.get_sale_details(
            data['res_date_start'], data['res_date_stop'], company_ids, data['state'], branch_ids))
        return data
    
class TopPurchasingReport(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_top_purchasing_product_doc'
    
    @api.model
    def _get_report_values(self, docids, data=None):

        data = dict(data or {})

        purchase_order_line_obj = self.env['purchase.order.line']
        basic_date_start = False
        basic_date_stop = False
        if data['date_from']:
            basic_date_start = fields.Datetime.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            basic_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            basic_date_stop = fields.Datetime.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if (basic_date_stop < basic_date_start):
                basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        ##################################
        # for product from to
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('order_id.company_id', 'in',
                           data.get('company_ids', False)))
        if data.get('date_from', False):
            domain.append(('order_id.date_order', '>=', fields.Datetime.to_string(basic_date_start)))
        if data.get('date_to', False):
            domain.append(('order_id.date_order', '<=', fields.Datetime.to_string(basic_date_stop)))

        # search order line product and add into product_qty_dictionary
        search_order_lines = purchase_order_line_obj.sudo().search(domain)

        product_total_qty_dic = {}
        if search_order_lines:
            for line in search_order_lines.sorted(key=lambda o: o.product_id.id):

                if product_total_qty_dic.get(line.product_id.name, False):
                    qty = product_total_qty_dic.get(line.product_id.name)
                    qty += line.product_qty
                    product_total_qty_dic.update({line.product_id.name: qty})
                else:
                    product_total_qty_dic.update(
                        {line.product_id.name: line.product_qty})

        final_product_list = []
        final_product_qty_list = []
        if product_total_qty_dic:
            # sort partner dictionary by descending order
            sorted_product_total_qty_list = sorted(
                product_total_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_product_total_qty_list:
                if data['product_qty'] != 0 and tuple_item[1] >= data['product_qty']:
                    final_product_list.append(tuple_item[0])

                elif data['product_qty'] == 0:
                    final_product_list.append(tuple_item[0])

                final_product_qty_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare product from to
        compare_date_start = False
        compare_date_stop = False
        if data['date_compare_from']:
            compare_date_start = fields.Datetime.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            compare_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            compare_date_stop = fields.Datetime.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if (compare_date_stop < compare_date_start):
                compare_date_stop = compare_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            compare_date_stop = compare_date_start + timedelta(days=1, seconds=-1)
        search_order_lines = False
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('order_id.company_id', 'in',
                           data.get('company_ids', False)))
        if data.get('date_compare_from', False):
            domain.append(('order_id.date_order', '>=',
                           fields.Datetime.to_string(compare_date_start)))
        if data.get('date_compare_to', False):
            domain.append(('order_id.date_order', '<=',
                           fields.Datetime.to_string(compare_date_stop)))

        search_order_lines = purchase_order_line_obj.sudo().search(domain)

        product_total_qty_dic = {}
        if search_order_lines:
            for line in search_order_lines.sorted(key=lambda o: o.product_id.id):

                if product_total_qty_dic.get(line.product_id.name, False):
                    qty = product_total_qty_dic.get(line.product_id.name)
                    qty += line.product_qty
                    product_total_qty_dic.update({line.product_id.name: qty})
                else:
                    product_total_qty_dic.update(
                        {line.product_id.name: line.product_qty})

        final_compare_product_list = []
        final_compare_product_qty_list = []
        if product_total_qty_dic:
            # sort partner dictionary by descending order
            sorted_product_total_qty_list = sorted(
                product_total_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_product_total_qty_list:
                if data['product_qty'] != 0 and tuple_item[1] >= data['product_qty']:
                    final_compare_product_list.append(tuple_item[0])

                elif data['product_qty'] == 0:
                    final_compare_product_list.append(tuple_item[0])

                final_compare_product_qty_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_product_list = []
        new_product_list = []
        if final_product_list and final_compare_product_list:
            for item in final_product_list:
                if item not in final_compare_product_list:
                    lost_product_list.append(item)

            for item in final_compare_product_list:
                if item not in final_product_list:
                    new_product_list.append(item)
        company_id = self.env.company
        data.update({'products': final_product_list,
                     'products_qty': final_product_qty_list,
                     'compare_products': final_compare_product_list,
                     'compare_products_qty': final_compare_product_qty_list,
                     'company_id': company_id,
                     'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                     'lost_products': lost_product_list,
                     'new_products': new_product_list,
                     })
        return data
    
class DayWisePurchaseReport(models.AbstractModel):
    _name = 'report.sh_purchase_reports.rpt_purchase_order_day_wise'
    _description = "Day Wise Purchase Report"
    
    def _get_street(self, partner):
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False
    
    @api.model
    def _get_report_values(self, docids, data=None):
        company_id = self.env.company
        street_company = self._get_street(company_id.partner_id)
        address_company = self._get_address_details(company_id.partner_id)
        data = {
            'start_date': data['date_start'],
            'end_date': data['date_stop'],
            'company_id': company_id,
            'street_company': street_company,
            'address_company': address_company,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
            'product_detail_data': data['product_detail_data']
        }
        return data
    

class PurchaseOrderReport(models.Model):
    _inherit = 'purchase.order.report'

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def generate_report_data(self):
        datas = self.read()[0]
        data = {'date_start': self.start_date.strftime('%d %B %Y'), 'date_stop': self.end_date.strftime('%d %B %Y'),
                'company_ids': self.company_ids.ids,
                'product_detail_data': self.get_product()}
        return self.env.ref('sh_purchase_reports.action_report_purchase_order_day_wise_report').report_action([], data=data)

    def get_product(self):
        for rec in self:
            product_detail = []
            date_start = False
            date_stop = False
            if self.start_date:
                date_start = fields.Datetime.from_string(self.start_date)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC'))

            if self.end_date:
                date_stop = fields.Datetime.from_string(self.end_date)
                # avoid a date_stop smaller than date_start
                if (date_stop < date_start):
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)
            if rec.start_date and rec.end_date:
                if len(rec.company_ids.ids) >= 1:
                    if len(rec.branch_ids.ids) > 0:
                        rec._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                            select * from crosstab (
                                            'select pt.name as product_name,
                                            to_char(po.date_order,''day'') as order_date,
                                            sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                            from purchase_order as po 
                                            left join purchase_order_line as pl on po.id = pl.order_id
                                            left join product_product as pr on pr.id = pl.product_id
                                            left join product_template as pt on  pr.product_tmpl_id = pt.id
                                            where date(date_order) >= date('%s') and date(date_order) <= date('%s') and po.company_id in %s and po.branch_id in %s and 
                                            po.state in (''purchase'',''done'')
                                            group by pt.name,to_char(po.date_order,''day'')
                                            order by 1,2'
                            ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                            )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(rec.company_ids.ids), tuple(rec.branch_ids.ids)))
                    else:
                        rec._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                            select * from crosstab (
                                            'select pt.name as product_name,
                                            to_char(po.date_order,''day'') as order_date,
                                            sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                            from purchase_order as po 
                                            left join purchase_order_line as pl on po.id = pl.order_id
                                            left join product_product as pr on pr.id = pl.product_id
                                            left join product_template as pt on  pr.product_tmpl_id = pt.id
                                            where date(date_order) >= date('%s') and date(date_order) <= date('%s') and po.company_id in %s and 
                                            po.state in (''purchase'',''done'')
                                            group by pt.name,to_char(po.date_order,''day'')
                                            order by 1,2'
                            ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                            )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(rec.company_ids.ids)))
                    product_detail = rec._cr.dictfetchall()
                else:
                    rec._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                        select * from crosstab (
                                        'select pt.name as product_name,
                                        to_char(po.date_order,''day'') as order_date,
                                        sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                        from purchase_order as po 
                                        left join purchase_order_line as pl on po.id = pl.order_id
                                        left join product_product as pr on pr.id = pl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date('%s') and date(date_order) <= date('%s') and 
                                        po.state in (''purchase'',''done'')
                                        group by pt.name,to_char(po.date_order,''day'')
                                        order by 1,2'
                        ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                        )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop)))

                    product_detail = rec._cr.dictfetchall()
            return product_detail

    def print_purchase_order_day_wise(self):
        for data in self:
            workbook = xlwt.Workbook()
            heading_format = xlwt.easyxf(
                'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
            bold = xlwt.easyxf(
                'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
            bold_center = xlwt.easyxf(
                'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
            center = xlwt.easyxf('font:bold True;align: horiz center')
            right = xlwt.easyxf('font:bold True;align: horiz right')
            left = xlwt.easyxf('align: horiz left')
            row = 1

            worksheet = workbook.add_sheet(
                u'Purchase Order Day Wise', cell_overwrite_ok=True)
            worksheet.write_merge(
                0, 1, 0, 8, 'Purchase Order - Product Purchased Day Wise', heading_format)
            user_tz = self.env.user.tz or pytz.utc
            local = pytz.timezone(user_tz)
            start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.start_date),
                                                                               DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
            end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.end_date),
                                                                             DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
            worksheet.write_merge(3, 3, 0, 0, "Start Date : ", bold)
            worksheet.write_merge(3, 3, 1, 1, start_date)
            worksheet.write_merge(3, 3, 6, 7, "End Date : ", bold)
            worksheet.write_merge(3, 3, 8, 8, end_date)
            product_detail = []
            date_start = False
            date_stop = False
            if self.start_date:
                date_start = fields.Datetime.from_string(self.start_date)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC'))

            if self.end_date:
                date_stop = fields.Datetime.from_string(self.end_date)
                # avoid a date_stop smaller than date_start
                if (date_stop < date_start):
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)
            if data.start_date and data.end_date:
                if len(data.company_ids.ids) >= 1:
                    if len(data.branch_ids.ids) > 0:
                        data._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                            select * from crosstab (
                                            'select pt.name as product_name,
                                            to_char(po.date_order,''day'') as order_date,
                                            sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                            from purchase_order as po 
                                            left join purchase_order_line as pl on po.id = pl.order_id
                                            left join product_product as pr on pr.id = pl.product_id
                                            left join product_template as pt on  pr.product_tmpl_id = pt.id
                                            where date(date_order) >= date('%s') and date(date_order) <= date('%s') and po.company_id in %s and po.branch_id in %s and 
                                            po.state in (''purchase'',''done'')
                                            group by pt.name,to_char(po.date_order,''day'')
                                            order by 1,2'
                            ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                            )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(data.company_ids.ids), tuple(data.branch_ids.ids)))
                    else:
                        data._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                            select * from crosstab (
                                            'select pt.name as product_name,
                                            to_char(po.date_order,''day'') as order_date,
                                            sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                            from purchase_order as po 
                                            left join purchase_order_line as pl on po.id = pl.order_id
                                            left join product_product as pr on pr.id = pl.product_id
                                            left join product_template as pt on  pr.product_tmpl_id = pt.id
                                            where date(date_order) >= date('%s') and date(date_order) <= date('%s') and po.company_id in %s and 
                                            po.state in (''purchase'',''done'')
                                            group by pt.name,to_char(po.date_order,''day'')
                                            order by 1,2'
                            ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                            )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(data.company_ids.ids)))
                    product_detail = data._cr.dictfetchall()
                else:
                    data._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                        select * from crosstab (
                                        'select pt.name as product_name,
                                        to_char(po.date_order,''day'') as order_date,
                                        sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                        from purchase_order as po 
                                        left join purchase_order_line as pl on po.id = pl.order_id
                                        left join product_product as pr on pr.id = pl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date('%s') and date(date_order) <= date('%s') and 
                                        po.state in (''purchase'',''done'')
                                        group by pt.name,to_char(po.date_order,''day'')
                                        order by 1,2'
                        ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                        )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop)))

                    product_detail = data._cr.dictfetchall()
            product = product_detail
            worksheet.col(0).width = int(25*260)
            worksheet.col(1).width = int(14*260)
            worksheet.col(2).width = int(14*260)
            worksheet.col(3).width = int(14*260)
            worksheet.col(4).width = int(14*260)
            worksheet.col(5).width = int(14*260)
            worksheet.col(6).width = int(14*260)
            worksheet.col(7).width = int(14*260)
            worksheet.col(8).width = int(14*260)

            worksheet.write(5, 0, "Product Name", bold)
            worksheet.write(5, 1, "Monday", bold)
            worksheet.write(5, 2, "Tuesday", bold)
            worksheet.write(5, 3, "Wednesday", bold)
            worksheet.write(5, 4, "Thursday", bold)
            worksheet.write(5, 5, "Friday", bold)
            worksheet.write(5, 6, "Saturday", bold)
            worksheet.write(5, 7, "Sunday", bold)
            worksheet.write(5, 8, "Total", bold)
            row = 6
            reg = 0
            for p in product:
                worksheet.write(row, 0, p['product'])
                worksheet.write(row, 1, p['monday'])
                worksheet.write(row, 2, p['tuesday'])
                worksheet.write(row, 3, p['wednesday'])
                worksheet.write(row, 4, p['thursday'])
                worksheet.write(row, 5, p['friday'])
                worksheet.write(row, 6, p['saturday'])
                worksheet.write(row, 7, p['sunday'])
                if p['monday']:
                    worksheet.write(row, 8, reg+p['monday'])
                if p['tuesday']:
                    worksheet.write(row, 8, reg+p['tuesday'])
                if p['wednesday']:
                    worksheet.write(row, 8, reg+p['wednesday'])
                if p['thursday']:
                    worksheet.write(row, 8, reg+p['thursday'])
                if p['friday']:
                    worksheet.write(row, 8, reg+p['friday'])
                if p['saturday']:
                    worksheet.write(row, 8, reg+p['saturday'])
                if p['sunday']:
                    worksheet.write(row, 8, reg+p['sunday'])
                row += 1
            row += 1
            worksheet.write(row, 0, "Total", center)
            reg1 = 0
            reg2 = 0
            for i in product:
                if i['monday']:
                    reg1 += i['monday']
                    worksheet.write(row, 1, reg1, right)
                else:
                    worksheet.write(row, 1, 0, right)
                if i['tuesday']:
                    reg1 += i['tuesday']
                    worksheet.write(row, 2, reg1, right)
                else:
                    worksheet.write(row, 2, 0, right)
                if i['wednesday']:
                    reg1 += i['wednesday']
                    worksheet.write(row, 3, reg1, right)
                else:
                    worksheet.write(row, 3, 0, right)
                if i['thursday']:
                    reg1 += i['thursday']
                    worksheet.write(row, 4, reg1, right)
                else:
                    worksheet.write(row, 4, 0, right)
                if i['friday']:
                    reg1 += i['friday']
                    worksheet.write(row, 5, reg1, right)
                else:
                    worksheet.write(row, 5, 0, right)
                if i['saturday']:
                    reg1 += i['saturday']
                    worksheet.write(row, 6, reg1, right)
                else:
                    worksheet.write(row, 6, 0, right)
                if i['sunday']:
                    reg1 += i['sunday']
                    worksheet.write(row, 7, reg1, right)
                else:
                    worksheet.write(row, 7, 0, right)

                if i['monday']:
                    reg2 += i['monday']
                if i['tuesday']:
                    reg2 += i['tuesday']
                if i['wednesday']:
                    reg2 += i['wednesday']
                if i['thursday']:
                    reg2 += i['thursday']
                if i['friday']:
                    reg2 += i['friday']
                if i['saturday']:
                    reg2 += i['saturday']
                if i['sunday']:
                    reg2 += i['sunday']
                worksheet.write(row, 8, reg2, right)

            filename = ('Purchase Order Day Wise Xls Report' + '.xls')
            fp = BytesIO()
            workbook.save(fp)

            export_id = data.env['excel.extended'].sudo().create({
                'excel_file': base64.encodestring(fp.getvalue()),
                'file_name': filename,
            })

            return{
                'type': 'ir.actions.act_window',
                'name': 'Day Wise Purchase Report',
                'res_id': export_id.id,
                'res_model': 'excel.extended',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }

class ShPurchaseReportRepresentativeWizard(models.TransientModel):
    _inherit = "sh.purchase.report.representative.wizard"

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Purchase Report by Purchase Representative', bold_center)
        worksheet.write_merge(
            0, 1, 0, 5, 'Purchase Report by Purchase Representative', heading_format)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.date_start:
            date_start = fields.Datetime.from_string(self.date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.date_end:
            date_stop = fields.Datetime.from_string(self.date_end)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_start),
                                                                           DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_end),
                                                                         DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        worksheet.write_merge(2, 2, 0, 5, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        row = 4
        for user_id in self.user_ids:
            row = row + 2
            worksheet.write_merge(
                row, row, 0, 5, "Purchase Representative: " + user_id.name, bold_center)
            row = row + 2
            worksheet.write(row, 0, "Order Number", bold)
            worksheet.write(row, 1, "Order Date", bold)
            worksheet.write(row, 2, "Vendor", bold)
            worksheet.write(row, 3, "Total", bold)
            worksheet.write(row, 4, "Amount Invoiced", bold)
            worksheet.write(row, 5, "Amount Due", bold)
            if self.state == 'all':
                sum_of_amount_total = 0.0
                total_invoice_amount = 0.0
                total_due_amount = 0.0
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ("user_id", "=", user_id.id)
                ]
                if self.company_ids:
                    domain.append(('company_id', 'in', self.company_ids.ids))
                if self.branch_ids:
                    domain.append(('branch_id', 'in', self.branch_ids.ids))
                for purchase_order in self.env['purchase.order'].sudo().search(domain):
                    row = row + 1
                    sum_of_amount_total = sum_of_amount_total + purchase_order.amount_total
                    sum_of_invoice_amount = 0.0
                    sum_of_due_amount = 0.0
                    if purchase_order.invoice_ids:
                        for invoice_id in purchase_order.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                            sum_of_invoice_amount += invoice_id.amount_total
                            sum_of_due_amount += invoice_id.amount_residual_signed
                            total_invoice_amount += invoice_id.amount_total
                            total_due_amount += invoice_id.amount_residual_signed
                    order_date = fields.Datetime.to_string(purchase_order.date_order)
                    date_order = datetime.strftime(pytz.utc.localize(datetime.strptime(order_date,
                                                                                       DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
                    worksheet.write(row, 0, purchase_order.name)
                    worksheet.write(row, 1, date_order)
                    worksheet.write(row, 2, purchase_order.partner_id.name)
                    worksheet.write(row, 3, purchase_order.amount_total)
                    worksheet.write(row, 4, sum_of_invoice_amount)
                    worksheet.write(row, 5, sum_of_due_amount)
                row = row + 1
                worksheet.write(row, 2, "Total", left)
                worksheet.write(row, 3, sum_of_amount_total)
                worksheet.write(row, 4, total_invoice_amount)
                worksheet.write(row, 5, total_due_amount)
            elif self.state == 'done':
                sum_of_amount_total = 0.0
                total_invoice_amount = 0.0
                total_due_amount = 0.0
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ("user_id", "=", user_id.id)
                ]
                domain.append(('state', 'in', ['purchase', 'done']))
                if self.company_ids:
                    domain.append(('company_id', 'in', self.company_ids.ids))
                if self.branch_ids:
                    domain.append(('company_id', 'in', self.branch_ids.ids))
                for purchase_order in self.env['purchase.order'].sudo().search(domain):
                    row = row + 1
                    sum_of_amount_total = sum_of_amount_total + purchase_order.amount_total
                    sum_of_invoice_amount = 0.0
                    sum_of_due_amount = 0.0
                    if purchase_order.invoice_ids:
                        for invoice_id in purchase_order.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                            sum_of_invoice_amount += invoice_id.amount_total
                            sum_of_due_amount += invoice_id.residual_signed
                            total_invoice_amount += invoice_id.amount_total
                            total_due_amount += invoice_id.residual_signed
                    order_date = fields.Datetime.to_string(purchase_order.date_order)
                    date_order = datetime.strftime(pytz.utc.localize(datetime.strptime(order_date,
                                                                                       DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
                    worksheet.write(row, 0, purchase_order.name)
                    worksheet.write(row, 1, order_date)
                    worksheet.write(row, 2, purchase_order.partner_id.name)
                    worksheet.write(row, 3, purchase_order.amount_total)
                    worksheet.write(row, 4, sum_of_invoice_amount)
                    worksheet.write(row, 5, sum_of_due_amount)
                row = row + 1
                worksheet.write(row, 2, "Total", left)
                worksheet.write(row, 3, sum_of_amount_total)
                worksheet.write(row, 4, total_invoice_amount)
                worksheet.write(row, 5, total_due_amount)
        filename = ('Purchase By Purchase Representative Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['purchase.report.representative.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Purchase Report by Purchase Representative',
            'res_id': export_id.id,
            'res_model': 'purchase.report.representative.xls',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

class RepresentativeReport(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_representative_report_doc'

    def _get_street(self, partner):
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def _get_report_values(self, docids, data=None):

        purchase_order_obj = self.env["purchase.order"]

        user_order_dic = {}
        user_list = []
        currency = False
        date_start = False
        date_stop = False
        if data['date_start']:
            date_start = fields.Datetime.from_string(data['date_start'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_end']:
            date_stop = fields.Datetime.from_string(data['date_end'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        if data.get('user_ids', False):
            for user_id in data.get('user_ids'):
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ("user_id", "=", user_id)
                ]
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                if data.get('branch_ids', False):
                    domain.append(
                        ('branch_id', 'in', data.get('branch_ids', False)))
                if data.get('state', False) and data.get('state') == 'done':
                    domain.append(('state', 'in', ['purchase', 'done']))

                search_orders = purchase_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if not currency:
                            currency = order.currency_id

                        order_dic = {
                            'order_number': order.name,
                            'order_date': order.date_order,
                            'vendor': order.partner_id.name if order.partner_id else "",
                            'total': order.amount_total,
                            'paid_amount': 0.0,
                            'due_amount': 0.0,
                        }
                        if order.invoice_ids:
                            sum_of_invoice_amount = 0.0
                            sum_of_due_amount = 0.0
                            for invoice_id in order.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                                sum_of_invoice_amount += invoice_id.amount_total
                                sum_of_due_amount += invoice_id.amount_residual_signed

                            order_dic.update({
                                "paid_amount": sum_of_invoice_amount,
                                "due_amount": sum_of_due_amount,
                            })

                        order_list.append(order_dic)

                search_user = self.env['res.users'].sudo().search([
                    ('id', '=', user_id)
                ], limit=1)
                if search_user:
                    user_order_dic.update({search_user.name: order_list})
                    user_list.append(search_user.name)

        if not currency:
            currency = self.env.user.company_id.sudo().currency_id
        company_id = self.env.company
        street_company = self._get_street(company_id.partner_id)
        address_company = self._get_address_details(company_id.partner_id)
        currency = self.env.user.company_id.sudo().currency_id
        data = {
            'date_start': datetime.strptime(data['date_start'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y'),
            'date_end': datetime.strptime(data['date_end'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y'),
            'user_order_dic': user_order_dic,
            'user_list': user_list,
            'currency': currency,
            'company_id': company_id,
            'street_company': street_company,
            'address_company': address_company,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
        }
        return data

class PurchaseBillSummaryWizard(models.TransientModel):
    _inherit = 'sh.purchase.bill.summary.wizard'

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Purchase Bill Summary', bold_center)
        worksheet.write_merge(
            0, 1, 0, 6, 'Purchase Bill Summary', heading_format)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.sh_start_date:
            date_start = fields.Datetime.from_string(self.sh_start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.sh_end_date:
            date_stop = fields.Datetime.from_string(self.sh_end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_start_date),
                                                                           DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_end_date),
                                                                         DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        worksheet.write_merge(2, 2, 0, 6, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        vendor_order_dic = {}
        for partner_id in self.sh_partner_ids:
            order_list = []
            domain = [
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                ("partner_id", "=", partner_id.id),
                ('state', 'in', ['purchase', 'done']),
            ]
            if self.sh_status == 'both':
                domain.append(('invoice_ids.state', 'in', ['posted']))
            elif self.sh_status == 'open':
                domain.append(('invoice_ids.state', 'in', ['posted']))
                domain.append(('invoice_ids.amount_residual', '!=', 0.0))
            elif self.sh_status == 'paid':
                domain.append(('invoice_ids.state', 'in', ['posted']))
                domain.append(('invoice_ids.amount_residual', '=', 0.0))
            if self.company_ids:
                domain.append(
                    ('company_id', 'in', self.company_ids.ids))
            if self.branch_ids:
                domain.append(
                    ('branch_id', 'in', self.branch_ids.ids))
            search_orders = self.env['purchase.order'].sudo().search(domain)
            invoice_ids = []
            if search_orders:
                for order in search_orders:
                    if order.invoice_ids:
                        for invoice in order.invoice_ids:
                            if invoice.id not in invoice_ids:
                                invoice_ids.append(invoice.id)
                            order_dic = {
                                'order_number': order.name,
                                'order_date': order.date_order.date(),
                                'invoice_number': invoice.name,
                                'invoice_date': invoice.invoice_date,
                                'invoice_currency_id': invoice.currency_id.symbol,
                            }
                            if invoice.move_type == 'in_invoice':
                                order_dic.update({
                                    'invoice_amount': invoice.amount_total,
                                    'invoice_paid_amount': invoice.amount_total - invoice.amount_residual,
                                    'due_amount': invoice.amount_residual,
                                })
                            elif invoice.move_type == 'in_refund':
                                order_dic.update({
                                    'invoice_amount': -(invoice.amount_total),
                                    'invoice_paid_amount': -(invoice.amount_total - invoice.amount_residual),
                                    'due_amount': -(invoice.amount_residual),
                                })
                            order_list.append(order_dic)
            vendor_order_dic.update({partner_id.name_get()[0][1]: order_list})
        row = 4
        if vendor_order_dic:
            for key in vendor_order_dic.keys():
                worksheet.write_merge(
                    row, row, 0, 6, key, bold_center)
                row = row + 2
                total_amount_invoiced = 0.0
                total_amount_paid = 0.0
                total_amount_due = 0.0
                worksheet.write(row, 0, "Order Number", bold)
                worksheet.write(row, 1, "Order Date", bold)
                worksheet.write(row, 2, "Bill Number", bold)
                worksheet.write(row, 3, "Bill Date", bold)
                worksheet.write(row, 4, "Amount Billed", bold)
                worksheet.write(row, 5, "Amount Paid", bold)
                worksheet.write(row, 6, "Amount Due", bold)
                row = row + 1
                for rec in vendor_order_dic[key]:
                    worksheet.write(row, 0, rec.get('order_number'), center)
                    worksheet.write(row, 1, str(rec.get('order_date')), center)
                    worksheet.write(row, 2, rec.get('invoice_number'), center)
                    worksheet.write(row, 3, str(
                        rec.get('invoice_date')), center)
                    worksheet.write(row, 4, str(rec.get(
                        'invoice_currency_id')) + str("{:.2f}".format(rec.get('invoice_amount'))), center)
                    worksheet.write(row, 5, str(rec.get(
                        'invoice_currency_id')) + str("{:.2f}".format(rec.get('invoice_paid_amount'))), center)
                    worksheet.write(row, 6, str(rec.get(
                        'invoice_currency_id')) + str("{:.2f}".format(rec.get('due_amount'))), center)
                    total_amount_invoiced = total_amount_invoiced + \
                                            rec.get('invoice_amount')
                    total_amount_paid = total_amount_paid + \
                                        rec.get('invoice_paid_amount')
                    total_amount_due = total_amount_due + rec.get('due_amount')
                    row = row + 1
                worksheet.write(row, 3, "Total", left)
                worksheet.write(row, 4, "{:.2f}".format(
                    total_amount_invoiced), bold_center_total)
                worksheet.write(row, 5, "{:.2f}".format(
                    total_amount_paid), bold_center_total)
                worksheet.write(row, 6, "{:.2f}".format(
                    total_amount_due), bold_center_total)
                row = row + 2
        filename = ('Purchase Bill Summary' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.purchase.bill.summary.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Purchase Bill Summary',
            'res_id': export_id.id,
            'res_model': 'sh.purchase.bill.summary.xls',
            'view_mode': 'form',
            'target': 'new',
        }

class PurchaseBillSummary(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_po_bill_summary_doc'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        purchase_order_obj = self.env["purchase.order"]
        vendor_order_dic = {}
        date_start = False
        date_stop = False
        invoice_amount = 0
        invoice_paid_amount = 0
        due_amount = 0
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
                if data.get('branch_ids', False):
                    domain.append(
                        ('branch_id', 'in', data.get('branch_ids', False)))
                search_orders = purchase_order_obj.sudo().search(domain)
                invoice_ids = []
                if search_orders:
                    for order in search_orders:
                        if order.invoice_ids:
                            for invoice in order.invoice_ids:
                                AccountPayment = self.env['account.payment'].sudo()
                                payment = AccountPayment.search([]).filtered(lambda p,invoice=invoice:invoice.id in p.reconciled_bill_ids.ids)
                                payment_date = payment and payment[0].date or False
                                if invoice.id not in invoice_ids:
                                    invoice_ids.append(invoice.id)
                                order_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order,
                                    'invoice_number': invoice.name,
                                    'invoice_date': invoice.invoice_date,
                                    'invoice_currency_id':invoice.currency_id.id,
                                    'payment_date':payment_date,
                                }
                                if invoice.move_type == 'in_invoice':
                                    invoice_amount += invoice.amount_total
                                    invoice_paid_amount += invoice.amount_total - invoice.amount_residual
                                    due_amount += invoice.amount_residual
                                    order_dic.update({
                                        'invoice_amount':invoice.amount_total,
                                        'invoice_paid_amount':invoice.amount_total - invoice.amount_residual,
                                        'due_amount' : invoice.amount_residual,
                                    })
                                elif invoice.move_type == 'in_refund':
                                    invoice_amount -= invoice.amount_total
                                    invoice_paid_amount -= invoice.amount_total - invoice.amount_residual
                                    due_amount -= invoice.amount_residual
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
        company_id = self.env.company
        street_company = self._get_street(company_id.partner_id)
        address_company = self._get_address_details(company_id.partner_id)
        start_date = datetime.strptime(data['sh_start_date'],'%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(data['sh_end_date'],'%Y-%m-%d %H:%M:%S')
        data.update({
            'date_start': date_start.strftime('%d %B %Y'),
            'date_end': date_stop.strftime('%d %B %Y'),
            'vendor_order_dic': vendor_order_dic,
            'invoice_amount': invoice_amount,
            'invoice_paid_amount': invoice_paid_amount,
            'due_amount': due_amount,
            'currency': self.env.user.company_id.sudo().currency_id,
            'company_id': company_id,
            'street_company': street_company,
            'address_company': address_company,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
        })
        return data
    
    def _get_street(self, partner):
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

class PurchaseAnalysisWizard(models.TransientModel):
    _inherit = 'sh.purchase.analysis.wizard'

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Vendor Purchase Analysis', bold_center)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.sh_start_date:
            date_start = fields.Datetime.from_string(self.sh_start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.sh_end_date:
            date_stop = fields.Datetime.from_string(self.sh_end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_start_date),
                                                                           DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_end_date),
                                                                         DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        if self.report_by == 'order':
            worksheet.write_merge(
                0, 1, 0, 5, 'Vendor Purchase Analysis', heading_format)
            worksheet.write_merge(2, 2, 0, 5, start_date + " to " + end_date, bold)
        elif self.report_by == 'product':
            worksheet.write_merge(
                0, 1, 0, 6, 'Vendor Purchase Analysis', heading_format)
            worksheet.write_merge(2, 2, 0, 6, str(
                self.sh_start_date) + " to " + str(self.sh_end_date), bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        order_dic_by_orders = {}
        order_dic_by_products = {}
        for partner_id in self.sh_partner_ids:
            order_list = []
            domain = [
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                ("partner_id", "=", partner_id.id),
            ]
            if self.sh_status == 'all':
                domain.append(('state', 'not in', ['cancel']))
            elif self.sh_status == 'draft':
                domain.append(('state', 'in', ['draft']))
            elif self.sh_status == 'sent':
                domain.append(('state', 'in', ['sent']))
            elif self.sh_status == 'purchase':
                domain.append(('state', 'in', ['purchase']))
            elif self.sh_status == 'done':
                domain.append(('state', 'in', ['done']))
            if self.company_ids:
                domain.append(
                    ('company_id', 'in', self.company_ids.ids))
            if self.branch_ids:
                domain.append(
                    ('branch_id', 'in', self.branch_ids.ids))
            search_orders = self.env['purchase.order'].sudo().search(domain)
            if search_orders:
                for order in search_orders:
                    if self.report_by == 'order':
                        order_dic = {
                            'order_number': order.name,
                            'order_date': order.date_order.date(),
                            'user': order.user_id.name,
                            'purchase_amount': order.amount_total,
                            'purchase_currency_id': order.currency_id.symbol,
                        }
                        paid_amount = 0.0
                        if order.invoice_ids:
                            for invoice in order.invoice_ids:
                                if invoice.move_type == 'in_invoice':
                                    paid_amount += invoice.amount_total - invoice.amount_residual
                                elif invoice.move_type == 'in_refund':
                                    paid_amount += - \
                                        (invoice.amount_total -
                                         invoice.amount_residual)
                        order_dic.update({
                            'paid_amount': paid_amount,
                            'balance_amount': order.amount_total - paid_amount
                        })
                        order_list.append(order_dic)
                    elif self.report_by == 'product' and order.order_line:
                        lines = False
                        if self.sh_product_ids:
                            lines = order.order_line.sudo().filtered(
                                lambda x: x.product_id.id in self.sh_product_ids.ids)
                        else:
                            products = self.env['product.product'].sudo().search(
                                [])
                            lines = order.order_line.sudo().filtered(
                                lambda x: x.product_id.id in products.ids)
                        if lines:
                            for line in lines:
                                order_dic = {
                                    'order_number': line.order_id.name,
                                    'order_date': line.order_id.date_order.date(),
                                    'product_name': line.product_id.name_get()[0][1],
                                    'price': line.price_unit,
                                    'qty': line.product_uom_qty,
                                    'tax': line.price_tax,
                                    'subtotal': line.price_subtotal,
                                    'purchase_currency_id': order.currency_id.symbol,
                                }
                                order_list.append(order_dic)
            if self.report_by == 'order':
                order_dic_by_orders.update(
                    {partner_id.name_get()[0][1]: order_list})
            elif self.report_by == 'product':
                order_dic_by_products.update(
                    {partner_id.name_get()[0][1]: order_list})
        row = 4
        if self.report_by == 'order':
            if order_dic_by_orders:
                for key in order_dic_by_orders.keys():
                    worksheet.write_merge(
                        row, row, 0, 5, key, bold_center)
                    row = row + 2
                    total_purchase_amount = 0.0
                    total_amount_paid = 0.0
                    total_balance = 0.0
                    worksheet.write(row, 0, "Order Number", bold)
                    worksheet.write(row, 1, "Order Date", bold)
                    worksheet.write(row, 2, "Purchase Representative", bold)
                    worksheet.write(row, 3, "Purchase Amount", bold)
                    worksheet.write(row, 4, "Amount Paid", bold)
                    worksheet.write(row, 5, "Balance", bold)
                    row = row + 1
                    for rec in order_dic_by_orders[key]:
                        worksheet.write(row, 0, rec.get(
                            'order_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('order_date')), center)
                        worksheet.write(row, 2, rec.get('user'), center)
                        worksheet.write(row, 3, str(rec.get(
                            'purchase_currency_id'))+str("{:.2f}".format(rec.get('purchase_amount'))), center)
                        worksheet.write(row, 4, str(rec.get(
                            'purchase_currency_id')) + str("{:.2f}".format(rec.get('paid_amount'))), center)
                        worksheet.write(row, 5, str(rec.get(
                            'purchase_currency_id')) + str("{:.2f}".format(rec.get('balance_amount'))), center)
                        total_purchase_amount = total_purchase_amount + \
                                                rec.get('purchase_amount')
                        total_amount_paid = total_amount_paid + \
                                            rec.get('paid_amount')
                        total_balance = total_balance + \
                                        rec.get('balance_amount')
                        row = row + 1
                    worksheet.write(row, 2, "Total", left)
                    worksheet.write(row, 3, "{:.2f}".format(
                        total_purchase_amount), bold_center_total)
                    worksheet.write(row, 4, "{:.2f}".format(
                        total_amount_paid), bold_center_total)
                    worksheet.write(row, 5, "{:.2f}".format(
                        total_balance), bold_center_total)
                    row = row + 2
        elif self.report_by == 'product':
            if order_dic_by_products:
                for key in order_dic_by_products.keys():
                    worksheet.write_merge(
                        row, row, 0, 6, key, bold_center)
                    row = row + 2
                    total_tax = 0.0
                    total_subtotal = 0.0
                    total_balance = 0.0
                    worksheet.write(row, 0, "Number", bold)
                    worksheet.write(row, 1, "Date", bold)
                    worksheet.write(row, 2, "Product", bold)
                    worksheet.write(row, 3, "Price", bold)
                    worksheet.write(row, 4, "Quantity", bold)
                    worksheet.write(row, 5, "Tax", bold)
                    worksheet.write(row, 6, "Subtotal", bold)
                    row = row + 1
                    for rec in order_dic_by_products[key]:
                        worksheet.write(row, 0, rec.get(
                            'order_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('order_date')), center)
                        worksheet.write(row, 2, rec.get(
                            'product_name'), center)
                        worksheet.write(row, 3, str(
                            rec.get('purchase_currency_id'))+str("{:.2f}".format(rec.get('price'))), center)
                        worksheet.write(row, 4, rec.get('qty'), center)
                        worksheet.write(row, 5, str(
                            rec.get('purchase_currency_id'))+str("{:.2f}".format(rec.get('tax'))), center)
                        worksheet.write(row, 6, str(rec.get(
                            'purchase_currency_id'))+str("{:.2f}".format(rec.get('subtotal'))), center)
                        total_tax = total_tax + rec.get('tax')
                        total_subtotal = total_subtotal + rec.get('subtotal')
                        row = row + 1
                    worksheet.write(row, 4, "Total", left)
                    worksheet.write(row, 5, "{:.2f}".format(
                        total_tax), bold_center_total)
                    worksheet.write(row, 6, "{:.2f}".format(
                        total_subtotal), bold_center_total)
                    row = row + 2
        filename = ('Vendor Purchase Analysis' + '.xls')
        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['sh.purchase.analysis.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Vendor Purchase Analysis',
            'res_id': export_id.id,
            'res_model': 'sh.purchase.analysis.xls',
            'view_mode': 'form',
            'target': 'new',
        }

class VendorPurchaseAnalysis(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_vend_po_analysis_doc'

    def _get_street(self, partner):
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        purchase_order_obj = self.env["purchase.order"]
        order_dic_by_orders = {}
        order_dic_by_products = {}
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
                    ("partner_id", "=", partner_id),
                ]
                if data.get('sh_status') == 'all':
                    domain.append(('state','not in',['cancel']))
                elif data.get('sh_status') == 'draft':
                    domain.append(('state','in',['draft']))
                elif data.get('sh_status') == 'sent':
                    domain.append(('state','in',['sent']))
                elif data.get('sh_status') == 'purchase':
                    domain.append(('state','in',['purchase']))
                elif data.get('sh_status') == 'done':
                    domain.append(('state','in',['done']))
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                if data.get('branch_ids', False):
                    domain.append(
                        ('branch_id', 'in', data.get('branch_ids', False)))
                search_orders = purchase_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if data.get('report_by') == 'order':
                            order_dic = {
                                'order_number': order.name,
                                'order_date': order.date_order,
                                'user': order.user_id.name,
                                'purchase_amount': order.amount_total,
                                'purchase_currency_id':order.currency_id.id,
                            }
                            paid_amount = 0.0
                            if order.invoice_ids:
                                for invoice in order.invoice_ids:
                                    if invoice.move_type == 'in_invoice':
                                        paid_amount+=invoice.amount_total - invoice.amount_residual
                                    elif invoice.move_type == 'in_refund':
                                        paid_amount+=-(invoice.amount_total - invoice.amount_residual)
                            order_dic.update({
                                'paid_amount':paid_amount,
                                'balance_amount':order.amount_total - paid_amount
                            })
                            order_list.append(order_dic)
                        elif data.get('report_by') == 'product' and order.order_line:
                            lines = False
                            if data.get('sh_product_ids'):
                                lines = order.order_line.sudo().filtered(lambda x: x.product_id.id in data.get('sh_product_ids'))
                            else:
                                products = self.env['product.product'].sudo().search([])
                                lines = order.order_line.sudo().filtered(lambda x: x.product_id.id in products.ids)
                            if lines:
                                for line in lines:
                                    order_dic = {
                                        'order_number':line.order_id.name,
                                        'order_date':line.order_id.date_order,
                                        'product_name': line.product_id.name_get()[0][1],
                                        'price': line.price_unit,
                                        'qty':line.product_qty,
                                        'tax':line.price_tax,
                                        'subtotal':line.price_subtotal,
                                        'purchase_currency_id':order.currency_id.id,
                                    }
                                    order_list.append(order_dic)
                search_partner = self.env['res.partner'].sudo().search([
                    ('id', '=', partner_id)
                ], limit=1)
                if search_partner:
                    if data.get('report_by') == 'order':
                        order_dic_by_orders.update({search_partner.name_get()[0][1]: order_list})
                    elif data.get('report_by') == 'product':
                        order_dic_by_products.update({search_partner.name_get()[0][1]: order_list})
        company_id = self.env.company
        street_company = self._get_street(company_id.partner_id)
        address_company = self._get_address_details(company_id.partner_id)
        currency = self.env.user.company_id.sudo().currency_id
        data.update({
            'date_start': datetime.strptime(data['sh_start_date'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y'),
            'date_end': datetime.strptime(data['sh_end_date'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y'),
            'order_dic_by_orders': order_dic_by_orders,
            'report_by':data.get('report_by'),
            'company_id': company_id,
            'currency': currency,
            'street_company': street_company,
            'address_company': address_company,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
            'order_dic_by_products':order_dic_by_products,
        })
        return data

class ShTcTopVendorWizard(models.TransientModel):
    _inherit = "sh.tv.top.vendor.wizard"

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_top_vendor_xls_report(self,):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        left = xlwt.easyxf('align: horiz left')
        row = 1

        data = {}
        data = self.read()[0]
        data = dict(data or {})
        currency_id = False
        purchase_order_obj = self.env['purchase.order']
        basic_date_start = False
        basic_date_stop = False
        if data['date_from']:
            basic_date_start = fields.Datetime.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            basic_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            basic_date_stop = fields.Datetime.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if (basic_date_stop < basic_date_start):
                basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        basic_start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_from),
                                                                                 DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        basic_end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_to),
                                                                               DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(basic_date_start)),
            ('date_order', '<=', fields.Datetime.to_string(basic_date_stop)),
            ('state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('branch_ids', False):
            domain.append(('branch_id', 'in', data.get('branch_ids', False)))

        purchase_orders = purchase_order_obj.sudo().search(domain)
        partner_total_amount_dic = {}
        if purchase_orders:
            for order in purchase_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_partner_list = []
        final_partner_amount_list = []
        if partner_total_amount_dic:
            # sort partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_partner_list.append(tuple_item[0])
                elif data['amount_total'] == 0:
                    final_partner_list.append(tuple_item[0])

                final_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare partner from to
        purchase_orders = False
        compare_date_start = False
        compare_date_stop = False
        if data['date_compare_from']:
            compare_date_start = fields.Datetime.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            compare_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            compare_date_stop = fields.Datetime.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if (compare_date_stop < compare_date_start):
                compare_date_stop = compare_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            compare_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        compare_start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_compare_from),
                                                                                   DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        compare_end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_compare_to),
                                                                                 DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(compare_date_start)),
            ('date_order', '<=', fields.Datetime.to_string(compare_date_stop)),
            ('state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))

        if data.get('branch_ids', False):
            domain.append(('branch_id', 'in', data.get('branch_ids', False)))

        purchase_orders = purchase_order_obj.sudo().search(domain)

        partner_total_amount_dic = {}
        if purchase_orders:
            for order in purchase_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_compare_partner_list = []
        final_compare_partner_amount_list = []
        if partner_total_amount_dic:
            # sort compare partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)

            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_compare_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_compare_partner_list.append(tuple_item[0])

                final_compare_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_partner_list = []
        new_partner_list = []
        if final_partner_list and final_compare_partner_list:
            for item in final_partner_list:
                if item not in final_compare_partner_list:
                    lost_partner_list.append(item)

            for item in final_compare_partner_list:
                if item not in final_partner_list:
                    new_partner_list.append(item)

        #       finally update data dictionary
        if not currency_id:
            self.env.user.company_id.sudo().currency_id

        if self.type == 'basic':
            row = 1
            worksheet = workbook.add_sheet(
                u'Top Vendors', cell_overwrite_ok=True)
            worksheet.write_merge(0, 1, 0, 2, 'Top Vendors', heading_format)
            worksheet.write(3, 0, 'Date From: ', bold)
            worksheet.write(3, 1, basic_start_date)

            worksheet.write(4, 0, 'Date To: ', bold)
            worksheet.write(4, 1, basic_end_date)
            worksheet.col(0).width = int(25*260)
            worksheet.col(1).width = int(25*260)
            worksheet.col(2).width = int(14*260)
            row = 6
            worksheet.write(row, 0, "#", bold)
            worksheet.write(row, 1, "Vendor", bold)
            worksheet.write(row, 2, "Purchase Amount", bold)
            no = 0
            row = 7
            for i in range(len(final_partner_list)):
                no = no+1
                worksheet.write(row, 0, no, left)
                worksheet.write(row, 1, final_partner_list[i], left)
                worksheet.write(row, 2, final_partner_amount_list[i], left)
                row = row+1
        elif self.type == 'compare':
            row = 1
            worksheet = workbook.add_sheet(
                u'Top Vendors', cell_overwrite_ok=True)
            worksheet.write_merge(0, 1, 0, 6, 'Top Vendors', heading_format)
            worksheet.write(3, 0, 'Date From: ', bold)
            worksheet.write(3, 1, basic_start_date)
            worksheet.write(4, 0, 'Date To: ', bold)
            worksheet.write(4, 1, basic_end_date)
            worksheet.write(3, 5, 'Compare From Date: ', bold)
            worksheet.write(3, 6, compare_start_date)

            worksheet.write(4, 5, 'Compare To Date: ', bold)
            worksheet.write(4, 6, compare_end_date)
            row = 7
            worksheet.col(0).width = int(25*260)
            worksheet.col(1).width = int(25*260)
            worksheet.col(2).width = int(14*260)
            worksheet.col(3).width = int(25*260)
            worksheet.col(4).width = int(25*260)
            worksheet.col(5).width = int(14*260)
            worksheet.col(6).width = int(14*260)
            worksheet.write(row, 0, "#", bold)
            worksheet.write(row, 1, "Vendor", bold)
            worksheet.write(row, 2, "Purchase Amount", bold)
            worksheet.write(row, 4, "#", bold)
            worksheet.write(row, 5, "Compare Vendor", bold)
            worksheet.write(row, 6, "Purchase Amount", bold)
            row = 8
            for i in range(len(final_partner_list)):
                worksheet.write(row, 0, i+1, left)
                worksheet.write(row, 1, final_partner_list[i], left)
                worksheet.write(row, 2, final_partner_amount_list[i], left)
                row = row+1
            row = 8
            for j in range(len(final_compare_partner_list)):
                worksheet.write(row, 4, j+1, left)
                worksheet.write(row, 5, final_compare_partner_list[j], left)
                worksheet.write(
                    row, 6, final_compare_partner_amount_list[j], left)
                row = row+1
            row = row+2
            worksheet.write_merge(row, row, 0, 2, 'New Vendors', bold_center)
            worksheet.write_merge(row, row, 4, 6, 'Lost Vendors', bold_center)
            row = row+1
            for new in new_partner_list:
                worksheet.write_merge(row, row, 0, 2, new, left)
                row = row+1
            for lost in lost_partner_list:
                worksheet.write_merge(row, row, 4, 6, lost, left)
                row = row+1

        filename = ('Top Vendor Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.top.vendor.excel.extended'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'name': 'Top Vendors',
            'res_id': export_id.id,
            'res_model': 'sh.top.vendor.excel.extended',
            'view_mode': 'form',
            'target': 'new',
        }

class TopVendorsReport(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_tv_top_vendors_doc'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        purchase_order_obj = self.env['purchase.order']
        currency_id = False
        basic_date_start = False
        basic_date_stop = False
        if data['date_from']:
            basic_date_start = fields.Datetime.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            basic_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            basic_date_stop = fields.Datetime.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if (basic_date_stop < basic_date_start):
                basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        ##################################
        # for partner from to
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(basic_date_start)),
            ('date_order', '<=', fields.Datetime.to_string(basic_date_stop)),
            ('state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('branch_ids', False):
            domain.append(('branch_id', 'in', data.get('branch_ids', False)))
        purchase_orders = purchase_order_obj.sudo().search(domain)
        partner_total_amount_dic = {}
        if purchase_orders:
            for order in purchase_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_partner_list = []
        final_partner_amount_list = []
        if partner_total_amount_dic:
            # sort partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_partner_list.append(tuple_item[0])
                elif data['amount_total'] == 0:
                    final_partner_list.append(tuple_item[0])

                final_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare partner from to
        compare_date_start = False
        compare_date_stop = False
        if data['date_compare_from']:
            compare_date_start = fields.Datetime.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            compare_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            compare_date_stop = fields.Datetime.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if (compare_date_stop < compare_date_start):
                compare_date_stop = compare_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            compare_date_stop = compare_date_start + timedelta(days=1, seconds=-1)
        purchase_orders = False
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(compare_date_start)),
            ('date_order', '<=', fields.Datetime.to_string(compare_date_stop)),
            ('state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))

        if data.get('branch_ids', False):
            domain.append(('branch_id', 'in', data.get('branch_ids', False)))

        purchase_orders = purchase_order_obj.sudo().search(domain)

        partner_total_amount_dic = {}
        if purchase_orders:
            for order in purchase_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_compare_partner_list = []
        final_compare_partner_amount_list = []
        if partner_total_amount_dic:
            # sort compare partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)

            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_compare_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_compare_partner_list.append(tuple_item[0])

                final_compare_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_partner_list = []
        new_partner_list = []
        if final_partner_list and final_compare_partner_list:
            for item in final_partner_list:
                if item not in final_compare_partner_list:
                    lost_partner_list.append(item)

            for item in final_compare_partner_list:
                if item not in final_partner_list:
                    new_partner_list.append(item)

        #       finally update data dictionary
        if not currency_id:
            self.env.user.company_id.sudo().currency_id
        company_id = self.env.company
        data.update({'partners': final_partner_list,
                     'partners_amount': final_partner_amount_list,
                     'compare_partners': final_compare_partner_list,
                     'compare_partners_amount': final_compare_partner_amount_list,
                     'lost_partners': lost_partner_list,
                     'new_partners': new_partner_list,
                     'currency': currency_id,
                     'company_id': company_id,
                     'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                     })
        return data

class PurchaseByCategoryWizard(models.TransientModel):
    _inherit = 'sh.purchase.category.wizard'

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Purchase By Product Category', bold_center)
        worksheet.write_merge(
            0, 1, 0, 8, 'Purchase By Product Category', heading_format)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.sh_start_date:
            date_start = fields.Datetime.from_string(self.sh_start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.sh_end_date:
            date_stop = fields.Datetime.from_string(self.sh_end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_start_date),
                                                                           DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_end_date),
                                                                         DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
        worksheet.write_merge(2, 2, 0, 8, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        worksheet.col(7).width = int(15 * 260)
        purchase_order_obj = self.env["purchase.order"]
        category_order_dic = {}
        categories = False
        if self.sh_category_ids:
            categories = self.sh_category_ids
        else:
            categories = self.env['product.category'].sudo().search([])
        if categories:
            for category in categories:
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ('state', 'in', ['purchase', 'done'])
                ]
                if self.company_ids:
                    domain.append(
                        ('company_id', 'in', self.company_ids.ids))
                if self.branch_ids:
                    domain.append(
                        ('branch_id', 'in', self.branch_ids.ids))
                search_orders = purchase_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if order.order_line:
                            order_dic = {}
                            for line in order.order_line.sudo().filtered(lambda x: x.product_id.categ_id.id == category.id):
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order.date(),
                                    'product': line.product_id.name_get()[0][1],
                                    'qty': line.product_qty,
                                    'uom': line.product_uom.name,
                                    'purchase_price': line.price_unit,
                                    'tax': line.price_tax,
                                    'purchase_currency_id': line.currency_id.symbol
                                }
                                if order_dic.get(line.product_id.id, False):
                                    qty = order_dic.get(
                                        line.product_id.id)['qty']
                                    qty = qty + line.product_uom_qty
                                    tax = order_dic.get(
                                        line.product_id.id)['tax']
                                    tax = tax + line.price_tax
                                    line_dic.update({
                                        'qty': qty,
                                        'tax': tax
                                    })
                                order_dic.update(
                                    {line.product_id.id: line_dic})
                            for key, value in order_dic.items():
                                order_list.append(value)
                category_order_dic.update({category.display_name: order_list})
        row = 4
        if category_order_dic:
            for key in category_order_dic.keys():
                total_qty = 0.0
                total_price = 0.0
                total_tax = 0.0
                total_subtotal = 0.0
                total = 0.0
                worksheet.write_merge(
                    row, row, 0, 8, key, bold_center)
                row = row + 2
                worksheet.write(row, 0, "Order Number", bold)
                worksheet.write(row, 1, "Order Date", bold)
                worksheet.write(row, 2, "Product", bold)
                worksheet.write(row, 3, "Quantity", bold)
                worksheet.write(row, 4, "UOM", bold)
                worksheet.write(row, 5, "Price", bold)
                worksheet.write(row, 6, "Tax", bold)
                worksheet.write(row, 7, "Subtotal", bold)
                worksheet.write(row, 8, "Total", bold)
                row = row + 1
                for rec in category_order_dic[key]:
                    total_qty += rec.get('qty')
                    total_price += rec.get('purchase_price')
                    total_tax += rec.get('tax')
                    total_subtotal += rec.get('qty', 0.0) * \
                                      rec.get('purchase_price', 0.0)
                    total += (rec.get('purchase_price') *
                              rec.get('qty', '')) + rec.get('tax')
                    worksheet.write(row, 0, rec.get('order_number'), center)
                    worksheet.write(row, 1, str(rec.get('order_date')), center)
                    worksheet.write(row, 2, rec.get('product'), center)
                    worksheet.write(row, 3, str(
                        "{:.2f}".format(rec.get('qty'))), center)
                    worksheet.write(row, 4, rec.get('uom'), center)
                    worksheet.write(row, 5, str(rec.get(
                        'purchase_currency_id')) + str("{:.2f}".format(rec.get('purchase_price'))), center)
                    worksheet.write(row, 6, rec.get('tax'), center)
                    worksheet.write(row, 7, str(rec.get('purchase_currency_id')) + str(
                        "{:.2f}".format(rec.get('purchase_price') * rec.get('qty', ''))), center)
                    worksheet.write(row, 8, str(rec.get('purchase_currency_id')) + str("{:.2f}".format(
                        (rec.get('purchase_price') * rec.get('qty', '')) + rec.get('tax'))), center)
                    row = row + 1
                worksheet.write(row, 2, "Total", bold_center_total)
                worksheet.write(row, 3, "{:.2f}".format(
                    total_qty), bold_center_total)
                worksheet.write(row, 5, "{:.2f}".format(
                    total_price), bold_center_total)
                worksheet.write(row, 6, "{:.2f}".format(
                    total_tax), bold_center_total)
                worksheet.write(row, 7, "{:.2f}".format(
                    total_subtotal), bold_center_total)
                worksheet.write(row, 8, "{:.2f}".format(
                    total), bold_center_total)
                row = row + 2
        filename = ('Purchase By Product Category' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.purchase.category.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Purchase by Product Category',
            'res_id': export_id.id,
            'res_model': 'sh.purchase.category.xls',
            'view_mode': 'form',
            'target': 'new',
        }

class PurchaseByCategory(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_po_by_category_doc'

    def _get_street(self, partner):
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        purchase_order_obj = self.env["purchase.order"]
        category_order_dic = {}
        categories = False
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
        if data.get('sh_category_ids', False):
            categories = self.env['product.category'].sudo().browse(
                data.get('sh_category_ids', False))
        else:
            categories = self.env['product.category'].sudo().search([])
        if categories:
            for category in categories:
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ('state', 'in', ['purchase', 'done'])
                ]
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                if data.get('branch_ids', False):
                    domain.append(
                        ('branch_id', 'in', data.get('branch_ids', False)))
                search_orders = purchase_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if order.order_line:
                            order_dic = {}
                            for line in order.order_line.sudo().filtered(lambda x: x.product_id.categ_id.id == category.id):
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order,
                                    'product': line.product_id.name_get()[0][1],
                                    'qty': line.product_qty,
                                    'uom': line.product_uom.name,
                                    'purchase_price': line.price_unit,
                                    'tax': line.price_tax,
                                    'purchase_currency_id': line.currency_id.id
                                }
                                if order_dic.get(line.product_id.id, False):
                                    qty = order_dic.get(
                                        line.product_id.id)['qty']
                                    qty = qty + line.product_uom_qty
                                    tax = order_dic.get(
                                        line.product_id.id)['tax']
                                    tax = tax + line.price_tax
                                    line_dic.update({
                                        'qty': qty,
                                        'tax': tax
                                    })
                                order_dic.update(
                                    {line.product_id.id: line_dic})
                            for key, value in order_dic.items():
                                order_list.append(value)
                category_order_dic.update({category.display_name: order_list})
        company_id = self.env.company
        street_company = self._get_street(company_id.partner_id)
        address_company = self._get_address_details(company_id.partner_id)
        currency = self.env.user.company_id.sudo().currency_id
        data.update({
            'date_start': datetime.strptime(data['sh_start_date'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y'),
            'date_end': datetime.strptime(data['sh_end_date'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y'),
            'category_order_dic': category_order_dic,
            'company_id': company_id,
            'currency': currency,
            'street_company': street_company,
            'address_company': address_company,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
        })
        return data

class PurchaseProductIndentWizard(models.TransientModel):
    _inherit = 'sh.purchase.product.indent.wizard'

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Purchase Product Indent', bold_center)
        worksheet.write_merge(
            0, 1, 0, 1, 'Purchase Product Indent', heading_format)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.sh_start_date:
            date_start = fields.Datetime.from_string(self.sh_start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.sh_end_date:
            date_stop = fields.Datetime.from_string(self.sh_end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_start_date),
                                                                           DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_end_date),
                                                                         DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        worksheet.write_merge(2, 2, 0, 1, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        order_dic = {}
        for partner in self.sh_partner_ids:
            customer_list = []
            for category in self.sh_category_ids:
                category_dic = {}
                category_list = []
                products = self.env['product.product'].sudo().search(
                    [('categ_id', '=', category.id)])
                for product in products:
                    domain = [
                        ("order_id.date_order", ">=",fields.Datetime.to_string(date_start)),
                        ("order_id.date_order", "<=", fields.Datetime.to_string(date_stop)),
                        ('order_id.partner_id', '=', partner.id),
                        ('product_id', '=', product.id)
                    ]
                    if self.sh_status == 'all':
                        domain.append(('order_id.state', 'not in', ['cancel']))
                    elif self.sh_status == 'draft':
                        domain.append(('order_id.state', 'in', ['draft']))
                    elif self.sh_status == 'sent':
                        domain.append(('order_id.state', 'in', ['sent']))
                    elif self.sh_status == 'purchase':
                        domain.append(('order_id.state', 'in', ['purchase']))
                    elif self.sh_status == 'done':
                        domain.append(('order_id.state', 'in', ['done']))
                    if self.company_ids:
                        domain.append(
                            ('company_id', 'in', self.company_ids.ids))
                    if self.branch_ids:
                        domain.append(
                            ('branch_id', 'in', self.branch_ids.ids))
                    order_lines = self.env['purchase.order.line'].sudo().search(
                        domain).mapped('product_qty')
                    product_qty = 0.0
                    if order_lines:
                        for qty in order_lines:
                            product_qty += qty
                    product_dic = {
                        'name': product.name_get()[0][1],
                        'qty': product_qty,
                    }
                    category_list.append(product_dic)
                category_dic.update({
                    category.display_name: category_list
                })
                customer_list.append(category_dic)
            order_dic.update({partner.name_get()[0][1]: customer_list})
        row = 4
        if order_dic:
            for key in order_dic.keys():
                worksheet.write(row, 0, key, bold)
                worksheet.write_merge(row, row, 0, 1, key, bold)
                row = row + 2
                for category_data in order_dic[key]:
                    for key_2 in category_data.keys():
                        total = 0.0
                        worksheet.write_merge(row, row, 0, 1, key_2, bold)
                        row = row + 1
                        worksheet.write(row, 0, "Product", bold_center_total)
                        worksheet.write(row, 1, "Quantity", bold_center_total)
                        row = row + 1
                        for record in category_data[key_2]:
                            total = total + record.get('qty')
                            worksheet.write(row, 0, record.get('name'), center)
                            worksheet.write(row, 1, "{:.2f}".format(
                                record.get('qty')), center)
                            row = row + 1
                        worksheet.write(row, 0, "Total", bold_center_total)
                        worksheet.write(row, 1, "{:.2f}".format(
                            total), bold_center_total)
                        row = row + 2
        filename = ('Purchase Product Indent' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.purchase.product.indent.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Purchase Product Indent',
            'res_id': export_id.id,
            'res_model': 'sh.purchase.product.indent.xls',
            'view_mode': 'form',
            'target': 'new',
        }

class PurchaseProductIndent(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_po_product_indent_doc'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        order_dic = {}
        categories = self.env['product.category'].sudo().browse(
            data.get('sh_category_ids', False))
        partners = self.env['res.partner'].sudo().browse(
            data.get('sh_partner_ids', False))
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
        if partners:
            for partner in partners:
                customer_list = []
                for category in categories:
                    category_dic = {}
                    category_list = []
                    products = self.env['product.product'].sudo().search(
                        [('categ_id', '=', category.id)])
                    for product in products:
                        domain = [
                            ("order_id.date_order", ">=",
                             fields.Datetime.to_string(date_start)),
                            ("order_id.date_order", "<=", fields.Datetime.to_string(date_stop)),
                            ('order_id.partner_id', '=', partner.id),
                            ('product_id', '=', product.id)
                        ]
                        if data.get('sh_status', False) == 'all':
                            domain.append(
                                ('order_id.state', 'not in', ['cancel']))
                        elif data.get('sh_status', False) == 'draft':
                            domain.append(('order_id.state', 'in', ['draft']))
                        elif data.get('sh_status', False) == 'sent':
                            domain.append(('order_id.state', 'in', ['sent']))
                        elif data.get('sh_status', False) == 'purchase':
                            domain.append(
                                ('order_id.state', 'in', ['purchase']))
                        elif data.get('sh_status', False) == 'done':
                            domain.append(('order_id.state', 'in', ['done']))
                        if data.get('company_ids', False):
                            domain.append(
                                ('company_id', 'in', data.get('company_ids', False)))
                        if data.get('branch_ids', False):
                            domain.append(
                                ('branch_id', 'in', data.get('branch_ids', False)))
                        order_lines = self.env['purchase.order.line'].sudo().search(
                            domain).mapped('product_qty')
                        product_qty = 0.0
                        if order_lines:
                            for qty in order_lines:
                                product_qty += qty
                        product_dic = {
                            'name': product.name_get()[0][1],
                            'qty': product_qty,
                        }
                        category_list.append(product_dic)
                    category_dic.update({
                        category.display_name: category_list
                    })
                    customer_list.append(category_dic)
                order_dic.update({partner.name_get()[0][1]: customer_list})
        company_id = self.env.company
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'order_dic': order_dic,
            'company_id': company_id,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
        })
        return data

class ShPaymentPurchaseReportWizard(models.TransientModel):
    _inherit = "sh.purchase.payment.report.wizard"

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        total_bold = xlwt.easyxf('font:bold True')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet('Bill Payment Report', bold_center)
        worksheet.write_merge(
            0, 1, 0, 7, 'Bill Payment Report', heading_format)
        worksheet.write_merge(2, 2, 0, 7, str(
            self.date_start) + " to " + str(self.date_end), bold)
        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]
        currency = False
        j_refund = 0.0
        data = {}
        grand_journal_dic = {}
        user_data_dic = {}
        search_user = self.env['res.users'].sudo().search(
            [('id', 'in', self.user_ids.ids)])
        journal_domain = [('type','in',['bank','cash'])]
        if self.company_ids:
            journal_domain.append(('company_id','in',self.company_ids.ids))
        if self.branch_ids:
            journal_domain.append(('branch_id','in',self.branch_ids.ids))
        search_journals = account_journal_obj.sudo().search(journal_domain)
        final_col_list = ["Bill", "Bill Date",
                          "Purchase Representative", "Vendor"]
        final_total_col_list = []
        for journal in search_journals:
            if journal.name not in final_col_list:
                final_col_list.append(journal.name)
            if journal.name not in final_total_col_list:
                final_total_col_list.append(journal.name)
        final_col_list.append("Total")
        final_total_col_list.append("Total")
        if search_user:
            for user_id in search_user:
                domain = [
                    ("date", ">=", self.date_start),
                    ("date", "<=", self.date_end),
                    ("payment_type", "in", ["inbound", "outbound"]),
                    ("partner_type", "in", ["supplier"])
                ]
                state = self.state
                if data.get('company_ids', False):
                    domain.append(
                        ("company_id", "in", self.company_ids.ids))
                if data.get('branch_ids', False):
                    domain.append(
                        ("branch_id", "in", self.branch_ids.ids))
                # journal wise payment first we total all bank, cash etc etc.
                payments = account_payment_obj.sudo().search(domain)
                invoice_pay_dic = {}
                invoice_ids = []
                if payments and search_journals:
                    for journal_wise_payment in payments.filtered(lambda x: x.journal_id.id in search_journals.ids):
                        if journal_wise_payment.reconciled_bill_ids:
                            invoices = False
                            if state:
                                if state == 'all':
                                    invoices = journal_wise_payment.reconciled_bill_ids.sudo().filtered(
                                        lambda x: x.state not in ['draft', 'cancel'] and x.invoice_user_id.id == user_id.id)
                                elif state == 'open' or state == 'paid':
                                    invoices = journal_wise_payment.reconciled_bill_ids.sudo().filtered(
                                        lambda x: x.state in ['posted'] and x.invoice_user_id.id == user_id.id)
                            for invoice in invoices:
                                if invoice.id not in invoice_ids:
                                    invoice_ids.append(invoice.id)
                                else:
                                    continue
                                pay_term_line_ids = invoice.line_ids.filtered(
                                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                partials = pay_term_line_ids.mapped(
                                    'matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')
                                if partials:
                                    for partial in partials.sudo().filtered(lambda x: x.max_date >= self.date_start and x.max_date <= self.date_end):
                                        counterpart_lines = partial.debit_move_id + partial.credit_move_id
                                        counterpart_line = counterpart_lines.filtered(
                                            lambda line: line.id not in invoice.line_ids.ids)
                                        foreign_currency = invoice.currency_id if invoice.currency_id != self.env.company.currency_id else False
                                        if foreign_currency and partial.currency_id == foreign_currency:
                                            payment_amount = partial.amount_currency
                                        else:
                                            payment_amount = partial.company_currency_id._convert(
                                                partial.amount, invoice.currency_id, self.env.company, invoice.invoice_date)
                                        if float_is_zero(payment_amount, precision_rounding=invoice.currency_id.rounding):
                                            continue
                                        if not currency:
                                            currency = invoice.currency_id
                                        if invoice.move_type == "in_invoice":
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                                    amount = pay_dic.get(
                                                        counterpart_line.payment_id.journal_id.name)
                                                    total += payment_amount
                                                    amount += payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                                else:
                                                    total += payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": total})

                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})
                                            else:
                                                invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": payment_amount, "Bill": invoice.name, "Vendor": invoice.partner_id.name, "Bill Date": str(
                                                    invoice.invoice_date), "Purchase Representative": invoice.user_id.name if invoice.user_id else "", "style": ''}})

                                        if invoice.move_type == "in_refund":
                                            j_refund += payment_amount
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                                    amount = pay_dic.get(
                                                        counterpart_line.payment_id.journal_id.name)
                                                    total -= payment_amount
                                                    amount -= payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                                else:
                                                    total -= payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": total})

                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})

                                            else:
                                                invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": -1 * (payment_amount), "Bill": invoice.name, "Vendor": invoice.partner_id.name, "Bill Date": str(
                                                    invoice.invoice_date), "Purchase Representative": invoice.user_id.name if invoice.user_id else "", "style": 'font:color red'}})

                # all final list and [{},{},{}] format
                # here we get the below total.
                # total journal amount is a grand total and format is : {} just a dictionary
                final_list = []
                total_journal_amount = {}
                for key, value in invoice_pay_dic.items():
                    final_list.append(value)
                    for col_name in final_total_col_list:
                        if total_journal_amount.get(col_name, False):
                            total = total_journal_amount.get(col_name)
                            total += value.get(col_name, 0.0)

                            total_journal_amount.update({col_name: total})

                        else:
                            total_journal_amount.update(
                                {col_name: value.get(col_name, 0.0)})

                # finally make user wise dic here.
                search_user = self.env['res.users'].search([
                    ('id', '=', user_id.id)
                ], limit=1)
                if search_user:
                    user_data_dic.update({
                        search_user.name: {'pay': final_list,
                                           'grand_total': total_journal_amount}
                    })

                for col_name in final_total_col_list:
                    j_total = 0.0
                    j_total = total_journal_amount.get(col_name, 0.0)
                    j_total += grand_journal_dic.get(col_name, 0.0)
                    grand_journal_dic.update({col_name: j_total})

            j_refund = j_refund * -1
            grand_journal_dic.update({'Refund': j_refund})

        data.update({
            'columns': final_col_list,
            'user_data_dic': user_data_dic,
            'currency': currency,
            'grand_journal_dic': grand_journal_dic,
        })
        row = 3
        col = 0

        for user in user_data_dic.keys():
            pay_list = []
            pay_list.append(user_data_dic.get(user).get('pay', []))
            row = row + 2
            worksheet.write_merge(
                row, row, 0, 7, "Purchase Representative: " + user, bold_center)
            row = row + 2
            col = 0
            for column in data.get('columns'):
                worksheet.col(col).width = int(15 * 260)
                worksheet.write(row, col, column, bold)
                col = col + 1
            for p in pay_list:
                row = row + 1
                col = 0
                for dic in p:
                    row = row + 1
                    col = 0
                    for column in data.get('columns'):
                        style = xlwt.easyxf(dic.get('style', ''))
                        worksheet.write(row, col, dic.get(column, 0), style)
                        col = col + 1
            row = row + 1
            col = 3
            worksheet.col(col).width = int(15 * 260)
            worksheet.write(row, col, "Total", total_bold)
            col = col + 1
            if user_data_dic.get(user, False):
                grand_total = user_data_dic.get(user).get('grand_total', {})
                if grand_total:
                    for column in data.get('columns'):
                        if column not in ['Bill', 'Bill Date', 'Purchase Representative', 'Vendor']:
                            worksheet.write(row, col, grand_total.get(
                                column, 0), total_bold)
                            col = col + 1
        row = row + 2
        worksheet.write_merge(row, row, 0, 1, "Payment Method", bold)
        row = row + 1
        worksheet.write(row, 0, "Name", bold)
        worksheet.write(row, 1, "Total", bold)
        for column in data.get('columns'):
            col = 0
            if column not in ["Bill", "Bill Date", "Purchase Representative", "Vendor"]:
                row = row + 1
                worksheet.col(col).width = int(15 * 260)
                worksheet.write(row, col, column)
                col = col + 1
                worksheet.write(row, col, grand_journal_dic.get(column, 0))
        if grand_journal_dic.get('Refund', False):
            row = row + 1
            col = 0
            worksheet.col(col).width = int(15 * 260)
            worksheet.write(row, col, "Refund")
            worksheet.write(row, col + 1, grand_journal_dic.get('Refund', 0.0))

        filename = ('Bill Payment Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['bill.payment.report.xls'].sudo().create({
            'excel_file': base64.encodebytes(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Bill Payment Report',
            'res_id': export_id.id,
            'res_model': 'bill.payment.report.xls',
            'view_mode': 'form',
            'target': 'new',
        }

class PaymentRpoert(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_payment_pr_report_doc'

    def _get_street(self, partner):
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def _get_report_values(self, docids, data=None):

        data = dict(data or {})
        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]

        journal_domain = [('type','in',['bank','cash'])]
        if data.get('company_ids', False):
            journal_domain.append(('company_id','in',data.get('company_ids', False)))
        if data.get('branch_ids', False):
            journal_domain.append(('branch_id','in',data.get('branch_ids', False)))
        search_journals = account_journal_obj.sudo().search(journal_domain)

        final_col_list = ["Bill", "Bill Date",
                          "Purchase Representative", "Vendor"]
        final_total_col_list = []
        for journal in search_journals:
            if journal.name not in final_col_list:
                final_col_list.append(journal.name)
            if journal.name not in final_total_col_list:
                final_total_col_list.append(journal.name)

        final_col_list.append("Total")
        final_total_col_list.append("Total")

        currency = False
        grand_journal_dic = {}
        j_refund = 0.0

        user_data_dic = {}
        if data.get("user_ids", False):

            for user_id in data.get("user_ids"):

                domain = [
                    ("date", ">=", data["date_start"]),
                    ("date", "<=", data["date_end"]),
                    ("payment_type", "in", ["inbound", "outbound"]),
                    ("partner_type", "in", ["supplier"])
                ]
                state = data.get("state")
                if data.get('company_ids', False):
                    domain.append(
                        ("company_id", "in", data.get('company_ids', False)))
                if data.get('branch_ids', False):
                    domain.append(
                        ("branch_id", "in", data.get('branch_ids', False)))
                # journal wise payment first we total all bank, cash etc etc.
                payments = account_payment_obj.sudo().search(domain)
                invoice_pay_dic = {}
                invoice_ids = []
                if payments and search_journals:
                    for journal_wise_payment in payments.filtered(lambda x: x.journal_id.id in search_journals.ids):
                        if journal_wise_payment.reconciled_bill_ids:
                            invoices = False
                            if data.get("state", False):
                                if state == 'all':
                                    invoices = journal_wise_payment.reconciled_bill_ids.sudo().filtered(
                                        lambda x: x.state not in ['draft', 'cancel'] and x.invoice_user_id.id == user_id)
                                elif state == 'open' or state == 'paid':
                                    invoices = journal_wise_payment.reconciled_bill_ids.sudo().filtered(
                                        lambda x: x.state in ['posted'] and x.invoice_user_id.id == user_id)
                            for invoice in invoices:
                                if invoice.id not in invoice_ids:
                                    invoice_ids.append(invoice.id)
                                else:
                                    continue
                                pay_term_line_ids = invoice.line_ids.filtered(
                                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                partials = pay_term_line_ids.mapped(
                                    'matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')
                                if partials:
                                    start_date = datetime.strptime(
                                        data['date_start'], "%Y-%m-%d").date()
                                    end_date = datetime.strptime(
                                        data['date_end'], "%Y-%m-%d").date()
                                    for partial in partials.sudo().filtered(lambda x: x.max_date >= start_date and x.max_date <= end_date):
                                        counterpart_lines = partial.debit_move_id + partial.credit_move_id
                                        counterpart_line = counterpart_lines.filtered(
                                            lambda line: line.id not in invoice.line_ids.ids)
                                        foreign_currency = invoice.currency_id if invoice.currency_id != self.env.company.currency_id else False
                                        if foreign_currency and partial.company_currency_id == foreign_currency:
                                            payment_amount = partial.amount_currency
                                        else:
                                            payment_amount = partial.company_currency_id._convert(
                                                partial.amount, invoice.currency_id, self.env.company, invoice.invoice_date)
                                        if float_is_zero(payment_amount, precision_rounding=invoice.currency_id.rounding):
                                            continue
                                        if not currency:
                                            currency = invoice.currency_id
                                        if invoice.move_type == "in_invoice":
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                                    amount = pay_dic.get(
                                                        counterpart_line.payment_id.journal_id.name)
                                                    total += payment_amount
                                                    amount += payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                                else:
                                                    total += payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": total})

                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})
                                            else:
                                                invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": payment_amount, "Bill": invoice.name, "Vendor": invoice.partner_id.name,
                                                                                       "Bill Date": invoice.invoice_date, "Purchase Representative": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;'}})

                                        if invoice.move_type == "in_refund":
                                            j_refund += payment_amount
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                                    amount = pay_dic.get(
                                                        counterpart_line.payment_id.journal_id.name)
                                                    total -= payment_amount
                                                    amount -= payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                                else:
                                                    total -= payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": total})

                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})

                                            else:
                                                invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": -1 * (payment_amount), "Bill": invoice.name, "Vendor": invoice.partner_id.name,
                                                                                       "Bill Date": invoice.invoice_date, "Purchase Representative": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;color:red'}})
                # all final list and [{},{},{}] format
                # here we get the below total.
                # total journal amount is a grand total and format is : {} just a dictionary
                final_list = []
                total_journal_amount = {}
                for value in invoice_pay_dic.items():
                    final_list.append(value)
                    for col_name in final_total_col_list:
                        if total_journal_amount.get(col_name, False):
                            total = total_journal_amount.get(col_name)
                            total += value[1].get(col_name, 0.0)

                            total_journal_amount.update({col_name: total})

                        else:
                            total_journal_amount.update(
                                {col_name: value[1].get(col_name, 0.0)})

                # finally make user wise dic here.
                search_user = self.env['res.users'].sudo().search([
                    ('id', '=', user_id)
                ], limit=1)
                if search_user:
                    user_data_dic.update({
                        search_user.name: {'pay': final_list,
                                           'grand_total': total_journal_amount}
                    })

                for col_name in final_total_col_list:
                    j_total = 0.0
                    j_total = total_journal_amount.get(col_name, 0.0)
                    j_total += grand_journal_dic.get(col_name, 0.0)
                    grand_journal_dic.update({col_name: j_total})

            j_refund = j_refund * -1
            grand_journal_dic.update({'Refund': j_refund})
        company_id = self.env.company
        street_company = self._get_street(company_id.partner_id)
        address_company = self._get_address_details(company_id.partner_id)
        currency = self.env.user.company_id.sudo().currency_id
        data.update({
            'date_start': datetime.strptime(data['date_start'], '%Y-%m-%d').strftime('%d %B %Y'),
            'date_end': datetime.strptime(data['date_end'], '%Y-%m-%d').strftime('%d %B %Y'),
            'columns': final_col_list,
            'user_data_dic': user_data_dic,
            'currency': currency,
            'company_id': company_id,
            'street_company': street_company,
            'address_company': address_company,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
            'grand_journal_dic': grand_journal_dic,
        })
        return data