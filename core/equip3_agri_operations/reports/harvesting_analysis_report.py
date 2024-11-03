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


class ReportHarvestingAnalysisReport(models.AbstractModel):
    _name = 'report.equip3_agri_operations.harvesting_analysis_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['agriculture.harvesting.analysis.report'].browse(docids),
            'doc_model': 'agriculture.harvesting.analysis.report',
        }


class HarvestingAnalysisReport(models.TransientModel):
    _name = 'agriculture.harvesting.analysis.report'
    _description = 'Harvesting Analysis Report'

    @api.model
    def create(self, vals):
        if not vals.get('filter_date'):
            vals['filter_date'] = 'this_year'
        return super(HarvestingAnalysisReport, self).create(vals)
    
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
                months += ['%s %s' % (MONTH_NAMES[(i - 1) % 12], year)]
        return months

    def get_harvesting_values(self, area=None):

        def _prepare(col1=None, col2=None, obj=None):
            return {
                'model': obj and obj._name or False, 
                'id': obj and obj.id or False, 
                'col1': col1 and col1 or '',
                'col2': col2 and col2 or '',
                'children': [],
                'months': {month: {'planned': 0.0, 'actual': 0.0} for month in self._get_months()}
            }

        def _compute_aggregate(parent):
            for key in parent['months'].keys():
                for child in parent['children']:
                    parent['months'][key]['actual'] += child['months'][key]['actual']
            return parent

        division_ids = self.env['agriculture.division'].search([])
        activity_record_ids = self.env['agriculture.daily.activity.record'].search([('state', '=', 'confirm')])
        plan_ids = self.env['agriculture.harvest.planning'].search([])

        data = _prepare()
        months = self._get_months()
        months_number = self._get_months(number=True)

        for division in division_ids:
            division_values = _prepare(col1=division.display_name, col2='%s %s' % (division.area, division.area_uom_id.display_name), obj=division)

            record_ids = activity_record_ids.filtered(
                lambda r: r.division_id == division and
                self.date_from <= r.date_scheduled <= self.date_to
            )

            division_plan_ids = plan_ids.filtered(lambda p: self.date_from.year <= int(p.year) <= self.date_to.year)
            line_ids = division_plan_ids.month_ids.filtered(lambda m: m.division_id == division)
            for month in months:
                planned_qty = sum(line_ids.mapped('val_%s' % month[:3].lower()))
                division_values['months'][month]['planned'] = planned_qty

            for record in record_ids:
                record_values = _prepare(col1=str(record.date_scheduled), col2=record.name, obj=record)

                actual_qty = sum(record.mapped('harvest_ids').filtered(lambda h: h.state == 'done').mapped('quantity_done'))
                month_index = months_number.index((record.date_scheduled.month, record.date_scheduled.year))
                record_values['months'][months[month_index]]['actual'] = actual_qty

                division_values['children'] += [record_values]

            _compute_aggregate(division_values)
            data['children'] += [division_values]

        return {'data': data, 'months': months}

    def print_xlsx_report(self):
        file_name = 'Harvesting Analysis Report.xlsx'

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

        header = ['Division', 'Area'] + months + ['Total']

        width = []
        for i, head in enumerate(header):
            if i <= 1:
                width.append(len(head) + 2)
            else:
                width.append(len('Planned') + 2)
                width.append(len('Actual') + 2)

        row = 1
        worksheet.write(row, 0, '%s: %s' % (self.company_id.name, _('Harvesting Analysis Report')), title_format)

        row += 2
        worksheet.write(row, 0, 'Date', subtitle_format)
        worksheet.write(row, 1, ': %s' % dict(self.fields_get(allfields=['filter_date'])['filter_date']['selection']).get(self.filter_date, 'This Year'), subtitle_format)

        row += 2
        worksheet.merge_range(RNG(row, 0, row + 1, 0), header[0], header_format)
        worksheet.merge_range(RNG(row, 1, row + 1, 1), header[1], header_format)
        for i, head in enumerate(header[2:]):
            col = 2 + (i * 2)
            worksheet.merge_range(RNG(row, col, row, col + 1), head, header_format)
            for j, sub_head in enumerate(('Planned', 'Actual')):
                worksheet.write(row + 1, col + j, sub_head, header_format)

        row += 2
        for division in data['children']:
            worksheet.write(row, 0, division['col1'], subheader_format)
            width[0] = max((width[0], len(str(division['col2'])) + 2))

            worksheet.write(row, 1, division['col2'], subheader_format)
            width[1] = max((width[1], len(str(division['col2'])) + 2))

            total_planned, total_actual = 0.0, 0.0
            for j, (total_month_id, total_month) in enumerate(division['months'].items()):
                col = 2 + (j * 2)
                worksheet.write(row, col, total_month['planned'], subheader_format)
                worksheet.write(row, col + 1, total_month['actual'], subheader_format)
                width[col] = max((width[col], len(str(total_month['planned'])) + 2))
                width[col + 1] = max((width[col + 1], len(str(total_month['actual'])) + 2))
                total_planned += total_month['planned']
                total_actual += total_month['actual']

            col = 2 + ((j + 1) * 2)
            worksheet.write(row, col, total_planned, bold_subheader_format)
            width[col] = max((width[col], len(str(total_planned)) + 2))

            col += 1
            worksheet.write(row, col, total_actual, bold_subheader_format)
            width[col] = max((width[col], len(str(total_actual)) + 2))

            row += 1
            worksheet.write(row, 0, 'Date', bold_bordered)
            worksheet.write(row, 1, 'Reference', bold_bordered)
            width[0] = max((width[0], len('Date') + 2))
            width[1] = max((width[1], len('Reference') + 2))
            for col in range((len(header[2:]) * 2) + 2):
                worksheet.write(row, col + 2, '', bold_bordered)

            row += 1
            for record in division['children']:
                worksheet.write(row, 0, record['col1'], bordered)
                worksheet.write(row, 1, record['col2'], bordered)
                width[0] = max((width[0], len(str(record['col1'])) + 2))
                width[1] = max((width[1], len(str(record['col2'])) + 2))

                total_planned, total_actual = 0.0, 0.0
                for j, (month_id, month) in enumerate(record['months'].items()):
                    col = 2 + (j * 2)
                    worksheet.write(row, col, '', bordered)
                    worksheet.write(row, col + 1, month['actual'], bordered)
                    width[col] = max((width[col], len(str('')) + 2))
                    width[col + 1] = max((width[col + 1], len(str(month['actual'])) + 2))
                    total_planned += month['planned']
                    total_actual += month['actual']

                col = 2 + ((j + 1) * 2)
                worksheet.write(row, col, total_planned, bold_bordered)
                width[col] = max((width[col], len(str('')) + 2))

                col += 1
                worksheet.write(row, col, total_actual, bold_bordered)
                width[col] = max((width[col], len(str(total_actual)) + 2))
                    
                row += 1

        for col, w in enumerate(width):
            worksheet.set_column(col, col, w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return attachment_id.id
