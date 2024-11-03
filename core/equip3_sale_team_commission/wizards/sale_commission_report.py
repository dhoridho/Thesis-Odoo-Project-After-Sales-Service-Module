
from odoo import tools
from odoo import api , models, fields , _
from datetime import datetime, date
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import xlwt
import base64
from io import BytesIO
from xlsxwriter.workbook import Workbook

class SalesCommissionReport(models.TransientModel):
    _name = 'sale.commission.report'
    _description = "Sale Commission Report"
    
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    sales_persons = fields.Many2many('res.users', string="Sales Person")
    commision_type = fields.Selection([
        ('all', 'ALL'),
        ('sales', 'Sales'),
        ('collection', 'Collection'),
    ], string="Commision Type", default='all')
    company_ids = fields.Many2many('res.company', string="Company")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self:self.env.user.company_id.id)
    
    @api.model
    def default_get(self, fields):
        res = super(SalesCommissionReport, self).default_get(fields)
        res['company_ids'] = [(6, 0, self.env.user.company_id.ids)]
        return res
    
    def action_print(self):
        sales_persons = self.sales_persons
        if not self.sales_persons:
            sales_persons = self.set_sales_persons()

        count_data = 0
        for user_id in sales_persons:
            final_data = self._get_sale_commission_data(user_id)
            if len(final_data) > 0:
                count_data += 1

        if count_data == 0:
            raise Warning(_('This user didn’t have any data.'))
        return self.env.ref('equip3_sale_team_commission.report_sale_commission_report').report_action(self)

    def action_print_xls(self):
        file_name = 'Sale Commission Report.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        format0 = xlwt.easyxf('font:height 500,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format1 = xlwt.easyxf('font:height 200,bold True; align: horiz left')
        format2 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format3 = xlwt.easyxf('font:height 350,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format4 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format5 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format6 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format7 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format8 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format9 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format10 = xlwt.easyxf('font:height 200,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format12 = xlwt.easyxf('align: horiz center;')
        format13 = xlwt.easyxf('align: horiz center; font:height 200,bold True')
        sales_persons = self.sales_persons
        if not self.sales_persons:
            sales_persons = self.set_sales_persons()
        for user_id in sales_persons:
            sheet = workbook.add_sheet('Sale Commission Report %s' % (user_id.name))
            sheet.col(0).width = int(25*370)
            sheet.col(1).width = int(25*270)
            sheet.col(2).width = int(25*270)
            sheet.col(3).width = int(25*270)
            sheet.col(4).width = int(25*270)
            sheet.col(5).width = int(25*270)
            sheet.col(6).width = int(25*270)
            sheet.col(7).width = int(25*270)
            sheet.write_merge(0, 2, 0, 6, 'Sale Commission Report', format0)
            periods = "Period " + self.start_date.strftime("%d %B %Y") + " - " + self.end_date.strftime("%d %B %Y")
            sheet.write_merge(3, 4, 0, 6, periods, format0)
            sheet.write(7, 0, "Printed On:", format1)
            today_date = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            final_data = self._get_sale_commission_data(user_id)
            if final_data:
                sheet.write(7, 1, today_date, format1)
                sheet.write(8, 0, "Sales Person:", format1)
                sheet.write(8, 1, user_id.name, format1)
                row = 9
                for line_data in final_data:
                    if line_data.get('type') == 'sales':
                        sheet.write(row, 0, "Grand Total Achievement:", format1)
                        sheet.write(row, 1, "{:0,.2f}".format(line_data.get('grand_total_achievement')), format1)
                    row += 1
                    sheet.write(row, 0, "Grand Total Commission Amount:", format1)
                    sheet.write(row, 1, "{:0,.2f}".format(line_data.get('grand_commission_total')), format1)
                    row += 2
                    sheet.write(row, 0, "No:", format1)
                    sheet.write(row, 1, "Periode:", format1)
                    if line_data.get('type') == 'sales':
                        sheet.write(row, 2, "Achievement:", format1)
                    sheet.write(row, 3, "Commission Amount:", format1)
                    counter = 1
                    row += 1
                    for product_lines in line_data.get('data'):
                        for line in product_lines.get('product_data'):
                            sheet.write(row, 0, counter, format1)
                            sheet.write(row, 1, line.get('date'), format1)
                            if line_data.get('type') == 'sales':
                                sheet.write(row, 2, "{:0,.2f}".format(line.get('achievement')), format1)
                            sheet.write(row, 3, "{:0,.2f}".format(line.get('commission')), format1)
                            row += 1
                            counter += 1
                    row += 2
        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['sale.commission.excel.report'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': file_name})
        fp.close()
        return{
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'sale.commission.excel.report',
            'name': 'Sale Commission Report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
            }

    def set_sales_persons(self):
        data = []
        users = self.env['res.users'].search([])
        for user_id in users:
            target_commision_ids = self.env['sh.target.commision'].search([('from_date', '>=', self.start_date), ('to_date', '<=', self.end_date),
                                                                           ('user_id', '=', user_id.id), ('company_id', 'in', self.company_ids.ids)])
            if target_commision_ids:
                data.append(user_id)
        return data

    def _get_sale_commission_data(self, user_id):
        for record in self:
            data = []
            vals = []
            sales_data = []
            collection_data = []
            grand_sale_total = 0
            grand_commission_total = 0
            grand_collection_total = 0
            grand_total_achievement = 0
            target_commision_ids = self.env['sh.target.commision'].search([('from_date', '>=', record.start_date), ('to_date', '<=', record.end_date),
                                                                           ('user_id', '=', user_id.id), ('company_id', 'in', record.company_ids.ids)])
            if target_commision_ids:
                for rec in target_commision_ids:
                    grand_total_achievement += rec.current_achievement
                    grand_commission_total += (rec.current_achievement - rec.deduction) * rec.current_commission / 100
                    vals.append({
                        'product_data': record._prepare_line(rec)
                    })
                data.append({
                    'type': 'sales',
                    'data': vals,
                    'grand_total_achievement': grand_total_achievement,
                    'grand_commission_total': grand_commission_total
                })
            return data

    def _prepare_line(self, target):
        product_data = []
        for res in target:
            vals = []
            product_data = []
            product_data.append({
                'date': res.from_date.strftime('%d/%m/%Y') + " - " + res.to_date.strftime('%d/%m/%Y'),
                'achievement': res.current_achievement,
                'commission': (res.current_achievement - res.deduction) * res.current_commission / 100,
            })
        return product_data

    def _prepare_invoice_data(self, product_ids, start_date, end_date, user_id, target_line):
        vals = {}
        product_data = []
        temp_product_data = []
        for product_id in product_ids:
            line_ids = self.env['account.move.line'].search([
                ('product_id', '=', product_id.id),
                ('move_id.payment_state', '=', 'paid'),
                ('move_id.invoice_user_id', '=', user_id.id),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.invoice_date', '>=', start_date),
                ('move_id.invoice_date', '<=', end_date),
            ])
            if line_ids:
                collection_amount = sum(line_ids.mapped('price_subtotal'))
                collection_cal_amount = round((collection_amount / target_line.collection_amount) * 100, 2)
                commission = (collection_cal_amount / 100) * target_line.commision
                if {'date_start': start_date, 'date_end': end_date, 'product_id': product_id.id} in temp_product_data:
                    filter_line = list(filter(
                                lambda r: r.get('date_start') == start_date and 
                                r.get('date_end') == end_date and
                                r.get('product') == product_id.id, product_data))
                    if filter_line:
                        filter_line[0]['commission'].append(round(commission, 2))
                        filter_line[0]['collection_amount'].append(collection_amount)
                else:
                    temp_product_data.append({
                        'date_start': start_date,
                        'date_end': end_date,
                        'product_id': product_id.id
                    })
                    product_data.append({
                        'date': start_date.strftime('%d/%m/%Y') + ' - ' + end_date.strftime('%d/%m/%Y'),
                        'product_id': product_id.display_name,
                        'collection_amount': [collection_amount],
                        'type': 'collection',
                        'date_start': start_date, 
                        'date_end': end_date, 
                        'product': product_id.id,
                        'commission': [round(commission, 2)],
                    })
        grand_collection_total = sum([sum(line.get('collection_amount')) for line in product_data])
        grand_commission_total = sum([sum(line.get('commission')) for line in product_data])
        vals.update({
            'product_data': product_data,
            'grand_collection_total': grand_collection_total,
            'grand_commission_total': grand_commission_total,
        })
        return vals

    def _prepare_sale_data(self, product_ids, start_date, end_date, user_id, target_line):
        vals = {}
        product_data = []
        temp_product_data = []
        for product_id in product_ids:
            sale_order_line_ids = self.env['sale.order.line'].search([
                    ('product_id', '=', product_id.id),
                    ('state', '=', 'sale'),
                    ('user_id', '=', user_id.id),
                    ('order_id.date_order', '>=', start_date),
                    ('order_id.date_order', '<=', end_date),
                ])
            if sale_order_line_ids:
                sale_amount = sum(sale_order_line_ids.mapped('price_subtotal'))
                sales_cal_amount = round((sale_amount / target_line.sales_amount) * 100, 2)
                commission = (sales_cal_amount / 100) * target_line.commision
                if {'date_start': start_date, 'date_end': end_date, 'product_id': product_id.id} in temp_product_data:
                    filter_line = list(filter(
                                lambda r: r.get('date_start') == start_date and 
                                r.get('date_end') == end_date and
                                r.get('product') == product_id.id, product_data))
                    if filter_line:
                        filter_line[0]['commission'].append(round(commission, 2))
                        filter_line[0]['sales_amount'].append(sales_amount)
                else:
                    temp_product_data.append({
                        'date_start': start_date,
                        'date_end': end_date,
                        'product_id': product_id.id
                    })
                    product_data.append({
                        'date': start_date.strftime('%d/%m/%Y') + ' - ' + end_date.strftime('%d/%m/%Y'),
                        'product_id': product_id.display_name,
                        'sales_amount': [sale_amount],
                        'date_start': start_date, 
                        'date_end': end_date, 
                        'product': product_id.id,
                        'type': 'sale',
                        'commission': [round(commission, 2)],
                    })
        grand_sale_total = sum([sum(line.get('sales_amount')) for line in product_data])
        grand_commission_total = sum([sum(line.get('commission')) for line in product_data])
        vals.update({
            'product_data': product_data,
            'grand_sale_total': grand_sale_total,
            'grand_commission_total': grand_commission_total,
        })
        return vals

    def _get_street(self, partner):
        self.ensure_one()
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
        self.ensure_one()
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