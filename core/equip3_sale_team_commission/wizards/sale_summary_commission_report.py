
from odoo import tools
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import xlwt
import base64
from io import BytesIO
from xlsxwriter.workbook import Workbook

class SalesSummaryCommissionReport(models.TransientModel):
    _name = 'sale.summary.commission.report'
    _description = "Sale Customer Commission Report"
    
    start_date = fields.Date(string="Start Date", tracking=True)
    end_date = fields.Date(string="End Date", tracking=True)
    sales_persons = fields.Many2many('res.users', string="Sales Person", tracking=True)
    commision_type = fields.Selection([
        ('all', 'ALL'),
        ('sales', 'Sales'),
        ('collection', 'Collection'),
    ], string="Commision Type", default='all', tracking=True)
    company_ids = fields.Many2many('res.company', string="Company")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self:self.env.user.company_id.id)
    
    @api.model
    def default_get(self, fields):
        res = super(SalesSummaryCommissionReport, self).default_get(fields)
        res['company_ids'] = [(6, 0, self.env.user.company_id.ids)]
        return res
    
    def action_print(self):
        return self.env.ref('equip3_sale_team_commission.report_sale_summary_commission_report').report_action(self)

    def action_print_xls(self):
        file_name = 'Sale Commission Summary Report.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        format0 = xlwt.easyxf('font:height 500,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        format1 = xlwt.easyxf('font:height 200,bold True; align: horiz left')
        format12 = xlwt.easyxf('font:height 200,bold True; align: horiz center')
        format13 = xlwt.easyxf('align: horiz left; font:height 200,bold True')
        format14 = xlwt.easyxf('font:height 200; align: horiz left')
        sales_persons = self.sales_persons
        if not self.sales_persons:
            sales_persons = self.set_sales_persons()
        sheet = workbook.add_sheet('Sale Commission Summary Report')
        sheet.col(0).width = int(25*370)
        sheet.col(1).width = int(25*270)
        sheet.col(2).width = int(25*270)
        sheet.col(3).width = int(25*270)
        sheet.col(4).width = int(25*270)
        sheet.col(5).width = int(25*270)
        sheet.col(6).width = int(25*270)
        sheet.col(7).width = int(25*270)
        sheet.write_merge(0, 2, 0, 6, 'Sale Commission Summary Report', format0)
        periods = "Period " + self.start_date.strftime("%d %B %Y") + " - " + self.end_date.strftime("%d %B %Y")
        sheet.write_merge(3, 4, 0, 6, periods, format0)
        sheet.write(7, 0, "Printed On:", format1)
        today_date = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        sheet.write(7, 1, today_date, format1)
        total_amount = self._get_sale_commission_total(sales_persons)
        sheet.write(8, 0, "Grand Total Achievement:", format1)
        sheet.write(8, 1, "{:0,.2f}".format(total_amount[0]), format1)
        sheet.write(9, 0, "Grand Total Commission Amount:", format1)
        sheet.write(9, 1, "{:0,.2f}".format(total_amount[1]), format1)
        row = 11
        for user in sales_persons:
            final_data = self._get_sale_commission_data(user)
            if final_data:
                sheet.write(row, 0, "Sales Person:", format1)
                sheet.write(row, 1, user.name, format1)
                for line_data in final_data:
                    row += 1
                    sheet.write(row, 0, "No:", format1)
                    sheet.write(row, 1, "Periode:", format1)
                    if line_data.get('type') == 'sales':
                        sheet.write(row, 2, "Achievement:", format1)
                    sheet.write(row, 3, "Commission Amount:", format1)
                    counter = 1
                    row += 1
                    total_achievement_amount = 0
                    total_commission_amount = 0
                    for product_lines in line_data.get('data'):
                        for line in product_lines.get('product_data'):
                            sheet.write(row, 0, counter, format14)
                            sheet.write(row, 1, line.get('date'), format14)
                            if line_data.get('type') == 'sales':
                                sheet.write(row, 2, "{:0,.2f}".format(line.get('achievement')), format14)
                            sheet.write(row, 3, "{:0,.2f}".format(line.get('commission')), format14)
                            total_achievement_amount += line.get('achievement')
                            total_commission_amount += line.get('commission')
                            row += 1
                            counter += 1    
                    total_achievement = "{:0,.2f}".format(total_achievement_amount)
                    total_commission = "{:0,.2f}".format(total_commission_amount)
                    sheet.write_merge(row, row, 0, 1, "Total", format12)
                    sheet.write(row, 2, total_achievement, format13)
                    sheet.write(row, 3, total_commission, format13)
                    row += 2
        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['sale.commission.excel.report'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': file_name})
        fp.close()
        return{
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=sale.commission.excel.report&field=excel_file&download=true&id=%s&filename=%s' % (export_id.id, export_id.file_name),
            'target': 'self',
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

    def _get_sale_commission_total(self, user_ids):
        for record in self:
            grand_total_achievement = 0
            grand_commission_total = 0
            for user in user_ids:
                data = record._get_sale_commission_data(user)
                if data:
                    total_achievement = data[0].get('grand_total_achievement')
                    commission_total = data[0].get('grand_commission_total')
                    grand_total_achievement += total_achievement
                    grand_commission_total += commission_total
            return [grand_total_achievement,grand_commission_total]

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