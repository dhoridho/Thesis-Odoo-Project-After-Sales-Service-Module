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


class ReportBudgetAnalysisReport(models.AbstractModel):
    _name = 'report.equip3_agri_reports.budget_analysis_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['agriculture.budget.analysis.report'].browse(docids),
            'doc_model': 'agriculture.budget.analysis.report',
        }


class BudgetAnalysisReport(models.TransientModel):
    _name = 'agriculture.budget.analysis.report'
    _description = 'Budget Analysis Report'

    @api.model
    def create(self, vals):
        if not vals.get('filter_date'):
            vals['filter_date'] = 'this_year'
        return super(BudgetAnalysisReport, self).create(vals)
    
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
        data = self.get_budget_values()
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

    def get_budget_values(self):

        def _prepare(obj=None, area=None):
            return {
                'model': obj and obj._name or False, 
                'id': obj and obj.id or False, 
                'name': obj and obj.display_name or False,
                'area': area and area or '',
                'children': [],
                'months': {month: {'planned': 0.0, 'actual': 0.0} for month in self._get_months()}
            }

        def _compute_aggregate(parent):
            for key in parent['months'].keys():
                for child in parent['children']:
                    parent['months'][key]['actual'] += child['months'][key]['actual']
                    parent['months'][key]['planned'] += child['months'][key]['planned']
            return parent

        division_ids = self.env['agriculture.division'].search([])
        activity_ids = self.env['crop.activity'].search([])
        activity_record_ids = self.env['agriculture.daily.activity.record'].search([('state', '=', 'confirm')])

        data = _prepare()
        months = self._get_months()
        months_number = self._get_months(number=True)

        for division in division_ids:
            division_values = _prepare(division, area='%s %s' % (division.area, division.area_uom_id.display_name))

            plan_ids = self.env['agriculture.budget.planning'].search([('division_id', '=', division.id)])
            plan_ids = plan_ids.filtered(lambda p: self.date_from.year <= int(p.year) <= self.date_to.year)

            for activity in activity_ids:
                activity_values = _prepare(activity)

                for month_label, (month, year) in zip(months, months_number):

                    record_ids = activity_record_ids.filtered(
                        lambda r: r.division_id == division and r.activity_id == activity and
                        r.date_scheduled.month == month and r.date_scheduled.year == year
                    )

                    actual_cost = abs(sum(record_ids.mapped('stock_valuation_layer_ids').mapped('value')))
                    budget_ids = plan_ids.filtered(lambda p: int(p.year) == year) \
                        .mapped('month_ids').filtered(lambda m: m.activity_id == activity)
                    planned_cost = sum(budget_ids.mapped('val_%s' % month_label[:3].lower()))

                    activity_values['months'][month_label]['actual'] = actual_cost
                    activity_values['months'][month_label]['planned'] = planned_cost

                division_values['children'] += [activity_values]

            _compute_aggregate(division_values)
            data['children'] += [division_values]

        return {'data': data, 'months': months}

    def print_xlsx_report(self):
        file_name = 'Budget Analysis Report.xlsx'

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

        values = self.get_budget_values()
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
        worksheet.write(row, 0, '%s: %s' % (self.company_id.name, _('Budget Analysis Report')), title_format)

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
            worksheet.write(row, 0, division['name'], subheader_format)
            width[0] = max((width[0], len(str(division['name'])) + 2))

            worksheet.write(row, 1, division['area'], subheader_format)
            width[1] = max((width[1], len(str(division['area'])) + 2))

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
            for activity in division['children']:
                worksheet.merge_range(RNG(row, 0, row, 1), activity['name'], bold_bordered)

                total_planned, total_actual = 0.0, 0.0
                for j, (month_id, month) in enumerate(activity['months'].items()):
                    col = 2 + (j * 2)
                    worksheet.write(row, col, month['planned'], bordered)
                    worksheet.write(row, col + 1, month['actual'], bordered)
                    width[col] = max((width[col], len(str(month['planned'])) + 2))
                    width[col + 1] = max((width[col + 1], len(str(month['actual'])) + 2))
                    total_planned += month['planned']
                    total_actual += month['actual']

                col = 2 + ((j + 1) * 2)
                worksheet.write(row, col, total_planned, bold_bordered)
                width[col] = max((width[col], len(str(total_planned)) + 2))

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
