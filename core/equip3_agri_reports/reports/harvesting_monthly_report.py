from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta

import io
import base64
import calendar
import xlsxwriter

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def safe_div(a, b):
    try:
        return round(a / b, 2)
    except ZeroDivisionError:
        return a


class ReportHarvestingMonthlyReport(models.AbstractModel):
    _name = 'report.equip3_agri_reports.harvesting_monthly_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['agriculture.harvesting.monthly.report'].browse(docids),
            'doc_model': 'agriculture.harvesting.monthly.report',
        }


class HarvestingMonthlyReport(models.TransientModel):
    _name = 'agriculture.harvesting.monthly.report'
    _description = 'Harvesting Monthly Report'

    @api.model
    def create(self, vals):
        if not vals.get('filter_date'):
            vals['filter_date'] = 'this_year'
        return super(HarvestingMonthlyReport, self).create(vals)
    
    @api.model
    def _get_month_range(self, date):
        last_of_month = calendar.monthrange(date.year, date.month)[1]
        return date.replace(day=1), date.replace(day=last_of_month)

    @api.model
    def _get_quarter_range(self, date):
        start_month = (((date.month - 1) // 3) * 3) + 1
        end_month = (((date.month - 1) // 3) * 3) + 3
        last_of_month = calendar.monthrange(date.year, end_month)[1]
        return date.replace(day=1, month=start_month), date.replace(day=last_of_month, month=end_month)

    @api.model
    def _get_year_range(self, date):
        return date.replace(day=1, month=1), date.replace(day=31, month=12)

    @api.depends('filter_date', 'custom_date_from', 'custom_date_to')
    def _compute_date_range(self):
        for record in self:
            date_from = False
            date_to = False

            filter_date = record.filter_date

            today = fields.Date.today()
            if filter_date == 'this_month':
                date_from, date_to = self._get_month_range(today)
            elif filter_date == 'this_quarter':
                date_from, date_to = self._get_quarter_range(today)
            elif filter_date == 'this_year':
                date_from, date_to = self._get_year_range(today)
            elif filter_date == 'last_month':
                date_from, date_to = self._get_month_range(today - relativedelta(months=1))
            elif filter_date == 'last_quarter':
                date_from, date_to = self._get_quarter_range(today - relativedelta(months=3))
            elif filter_date == 'last_year':
                date_from, date_to = self._get_year_range(today - relativedelta(years=1))
            elif filter_date == 'custom':
                date_from, date_to = record.custom_date_from, record.custom_date_to

            record.date_from = date_from
            record.date_to = date_to

    date_from = fields.Date(string='Date From', compute=_compute_date_range)
    date_to = fields.Date(string='Date To', compute=_compute_date_range)
    custom_date_from = fields.Date(string='Custom Date From')
    custom_date_to = fields.Date(string='Custom Date To')

    filter_date = fields.Selection(
        selection=[
            ('this_month', 'This Month'),
            ('this_quarter', 'This Quarter'),
            ('this_year', 'This Year'),
            ('last_month', 'Last Month'),
            ('last_quarter', 'Last Quarter'),
            ('last_year', 'Last Year'),
            ('custom', 'Custom')
        ], 
        string='Filter Date',
        default='this_year'
    )
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def get_report_values(self):
        data = self.get_harvesting_values()
        return {
            'filters': self.get_filters(),
            'data': data['data'],
            'months': data['months']
        }

    def get_filters(self):
        selection = self.fields_get(allfields=['filter_date'])['filter_date']['selection']
        return {
            'filter_date': {
                'selection': selection,
                'active': (self.filter_date, dict(selection).get(self.filter_date, 'This Year'))
            }
        }

    def _get_months(self, date_from=None, date_to=None, number=False):
        if not date_from:
            date_from = self.date_from
        if not date_to:
            date_to = self.date_to
        index_from = date_from.month
        index_to = date_to.month + ((date_to.year - date_from.year) * 12)
        current_year = date_from.year
        months = []
        for i in range(index_from, index_to + 1):
            year = current_year + ((i - 1) // 12)
            if number:
                months += [(((i - 1) % 12) + 1, year)]
            else:
                months += [(((i - 1) % 12) + 1, '%s %s' % (MONTH_NAMES[(i - 1) % 12].upper(), year))]
        return months

    def get_harvesting_values(self, area=None):

        activity_record_ids = self.env['agriculture.daily.activity.record'].search([
            ('state', '=', 'confirm'),
            ('date_scheduled', '>=', self.date_from),
            ('date_scheduled', '<=', self.date_to)
        ])
        block_ids = activity_record_ids.mapped('block_id')
        division_ids = activity_record_ids.mapped('division_id')
        estate_ids = activity_record_ids.mapped('estate_id')

        data = []
        months_number = self._get_months(number=True)

        sequence = 0
        for estate in estate_ids:
            for division in division_ids:
                for block in block_ids:
                    
                    ha = block.size
                    pkk = sum(block.crop_ids.mapped('crop_count'))

                    values = {
                        'sequence': sequence,
                        'estate': estate.display_name,
                        'division': division.display_name,
                        'block': block.display_name,
                        'tt': ', '.join(str(d) for d in set(block.crop_ids.mapped('crop_date'))),
                        'ha': ha,
                        'pkk': pkk,
                        'pkk/ha': safe_div(pkk, ha),
                        'children': [],
                        'months': {month_seq: {
                            'rotasi': 0.0,
                            'kg': 0.0,
                            'ton/ha': 0.0,
                            'rp': 0.0,
                            'rp/kg': 0.0,
                            'jjg': 0.0,
                            'bjr': 0.0,
                            'jjg/pkk': 0.0,
                            'hk': 0.0,
                            'kg/hk': 0.0
                        } for month_seq, month_year in months_number}
                    }

                    record_ids = activity_record_ids.filtered(lambda a: \
                        a.block_id == block \
                            and a.division_id == division \
                                and a.estate_id == estate)

                    if not record_ids:
                        continue

                    for record in record_ids:

                        child = {
                            'name': record.name,
                            'model': record._name,
                            'id': record.id,
                            'months': {month_seq: {
                                'rotasi': 0.0,
                                'kg': 0.0,
                                'ton/ha': 0.0,
                                'rp': 0.0,
                                'rp/kg': 0.0,
                                'jjg': 0.0,
                                'bjr': 0.0,
                                'jjg/pkk': 0.0,
                                'hk': 0.0,
                                'kg/hk': 0.0
                            } for month_seq, month_year in months_number}
                        }

                        kg = sum(record.harvest_ids.mapped('quantity_done'))
                        rp = 10000
                        jjg = sum(record.harvest_ids.mapped('bunch'))
                        hk = 10

                        record_month = record.date_scheduled.month
                        child['months'][record_month]['kg'] = kg
                        child['months'][record_month]['ton/ha'] = (kg/1000) * ha
                        child['months'][record_month]['rp'] = rp
                        child['months'][record_month]['rp/kg'] = safe_div(rp, kg)
                        child['months'][record_month]['jjg'] = jjg
                        child['months'][record_month]['jjg/pkk'] = safe_div(jjg, pkk)
                        child['months'][record_month]['hk'] = hk
                        child['months'][record_month]['kg/hk'] = safe_div(kg, hk)

                        values['children'] += [child]
                    
                    for month_seq, month_year in months_number:
                        for key in ['rotasi', 'kg', 'ton/ha', 'rp', 'rp/kg', 'jjg', 'bjr', 'jjg/pkk', 'hk', 'kg/hk']:
                            values['months'][month_seq][key] = sum(c['months'][month_seq][key] for c in values['children'])
                    
                        values['months'][month_seq]['rp'] = 10000
                        values['months'][month_seq]['hk'] = 10
                        values['months'][month_seq]['ton/ha'] = safe_div(values['months'][month_seq]['kg'], 1000) * ha
                        values['months'][month_seq]['rp/kg'] = safe_div(values['months'][month_seq]['rp'], values['months'][month_seq]['kg'])
                        values['months'][month_seq]['jjg/pkk'] = safe_div(values['months'][month_seq]['jjg'], pkk)
                        values['months'][month_seq]['kg/hk'] = safe_div(values['months'][month_seq]['kg'], values['months'][month_seq]['hk'])

                    data += [values]
                    sequence += 1

        return {'data': data, 'months': self._get_months()}


    def print_xlsx_report(self):
        file_name = 'Harvesting Monthly Report.xlsx'

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        
        RNG = xlsxwriter.utility.xl_range

        title_format = workbook.add_format({
            'bold': 1,
            'font_size': 15
        })

        subtitle_format = workbook.add_format({
            'bold': 1,
            'font_size': 13
        })

        header_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        bold_subheader_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'bg_color': '#dee2e6',
        })

        subheader_format = workbook.add_format({
            'border': 1,
            'bg_color': '#dee2e6',
        })

        bold_bordered = workbook.add_format({
            'bold': 1,
            'border': 1
        })

        bordered = workbook.add_format({
            'border': 1
        })

        values = self.get_harvesting_values()
        data = values['data']
        months = values['months']

        header = ['Estate', 'Division', 'Block', 'TT', 'HA', 'PKK', 'PKK/HA'] + [m[1] for m in months]

        width = []
        for i, head in enumerate(header):
            if i <= 6:
                width.append(len(head) + 2)
            else:
                for sub_head in ['ROTASI', 'KG', 'TON/HA', 'RP', 'RP/KG', 'JJG', 'BJR', 'JJG/PKK', 'HK', 'KG/HK']:
                    width.append(len(sub_head) + 2)

        row = 1
        worksheet.write(row, 0, '%s: %s' % (self.company_id.name, _('Harvesting Monthly Report')), title_format)

        row += 2
        worksheet.write(row, 0, 'Date', subtitle_format)
        worksheet.write(row, 1, ': %s' % dict(self.fields_get(allfields=['filter_date'])['filter_date']['selection']).get(self.filter_date, 'This Year'), subtitle_format)

        row += 2
        for i, head in enumerate(header[:7]):
            worksheet.merge_range(RNG(row, i, row + 1, i), head, header_format)

        for i, head in enumerate(header[7:]):
            col = 7 + (i * 10)
            worksheet.merge_range(RNG(row, col, row, col + 9), head, header_format)
            for j, sub_head in enumerate(['ROTASI', 'KG', 'TON/HA', 'RP', 'RP/KG', 'JJG', 'BJR', 'JJG/PKK', 'HK', 'KG/HK']):
                worksheet.write(row + 1, col + j, sub_head, header_format)

        row += 2
        for line in data:
            for i, key in enumerate(['estate', 'division', 'block', 'tt', 'ha', 'pkk', 'pkk/ha']):
                worksheet.write(row, i, line[key], subheader_format)
                width[i] = max((width[i], len(str(line[key])) + 2))

            for i, line_month in enumerate(line['months'].values()):
                for j, key in enumerate(['rotasi', 'kg', 'ton/ha', 'rp', 'rp/kg', 'jjg', 'bjr', 'jjg/pkk', 'hk', 'kg/hk']):
                    worksheet.write(row, j + 7 + (i * 10), line_month[key], subheader_format)
                    width[j + 7 + (i * 10)] = max((width[j + 7 + (i * 10)], len(str(line_month[key])) + 2))

            row += 1

        for col, w in enumerate(width):
            worksheet.set_column(col, col, w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return attachment_id.id
