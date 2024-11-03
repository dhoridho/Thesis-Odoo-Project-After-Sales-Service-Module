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


class ReportMiningProductionReport(models.AbstractModel):
    _name = 'report.equip3_mining_reports.mining_production_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['mining.production.report'].browse(docids),
            'doc_model': 'mining.production.report',
        }


class MiningProductionReport(models.TransientModel):
    _name = 'mining.production.report'
    _description = 'Mining Production Report'

    @api.model
    def create(self, vals):
        if not vals.get('filter_date'):
            vals['filter_date'] = 'this_year'
        return super(MiningProductionReport, self).create(vals)
    
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
        data = self.get_production_values()
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

    def _get_months(self, date_from=None, date_to=None):
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
            months += ['%s %s' % (MONTH_NAMES[(i - 1) % 12], year)]
        return months

    def get_production_values(self):

        def _prepare(obj=None, uom=None):
            return {
                'model': obj and obj._name or False, 
                'id': obj and obj.id or False, 
                'name': obj and obj.display_name or False, 
                'uom': uom or self.env['uom.uom'],
                'uom_name': uom and uom.display_name or False, 
                'children': [],
                'months': {month: {'planned': 0.0, 'actual': 0.0, 'achievement': 0.0} for month in months}
            }

        def _compute_aggregate(parent):
            for key in parent['months'].keys():
                for child in parent['children']:
                    parent['months'][key]['planned'] += parent['uom']._compute_quantity(child['months'][key]['planned'], child['uom'])
                    parent['months'][key]['actual'] += parent['uom']._compute_quantity(child['months'][key]['actual'], child['uom'])
                    parent['months'][key]['achievement'] += child['months'][key]['achievement']
            return parent

        operation_ids = self.env['mining.operations.two'].search([])
        act_ids = self.env['mining.daily.production.record'].search([])
        site_ids = sorted(act_ids.mapped('mining_site_id'), key=lambda s: s.id)
        
        months = self._get_months()

        data = _prepare()
        for site in site_ids:
            site_values = _prepare(site, None)

            for operation in operation_ids:
                operation_values = _prepare(operation, operation.uom_id)

                mpa_ids = act_ids.filtered(
                    lambda a: a.mining_site_id == site and a.mining_operation_id == operation and a.date and \
                        self.date_from <= a.date <= self.date_to)

                for mpa in mpa_ids:
                    mpa_values = _prepare(mpa, mpa.nett_uom_id)

                    list_months = self._get_months(mpa.date, mpa.date)
                    for month in list_months:
                        if month in mpa_values['months']:
                            mpa_values['months'][month]['planned'] = mpa.production_target
                            mpa_values['months'][month]['actual'] = mpa.nett_total
                            mpa_values['months'][month]['achievement'] = ((mpa.nett_total / mpa.production_target) * 100) if mpa.production_target else 0.0

                    operation_values['children'] += [mpa_values]

                _compute_aggregate(operation_values)
                site_values['children'] += [operation_values]
            
            _compute_aggregate(site_values)
            data['children'] += [site_values]

        return {'data': data, 'months': months}

    def print_xlsx_report(self):
        file_name = 'Production Report.xlsx'

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

        values = self.get_production_values()
        data = values['data']
        months = values['months']

        header = [''] + months + ['Total']

        width = []
        for i, head in enumerate(header):
            if i == 0:
                width.append(len(head) + 4)
            else:
                width.append(len('Planned') + 2)
                width.append(len('Actual') + 2)
                width.append(len('Achievement (%)') + 2)
                width.append(len('UoM') + 2)

        row = 1
        worksheet.write(row, 0, '%s: %s' % (self.company_id.name, _('Production Report')), title_format)

        row += 2
        worksheet.write(row, 0, 'Date', subtitle_format)
        worksheet.write(row, 1, ': %s' % dict(self.fields_get(allfields=['filter_date'])['filter_date']['selection']).get(self.filter_date, 'This Year'), subtitle_format)

        row += 1
        for site in data['children']:

            row += 1
            worksheet.merge_range(RNG(row, 0, row + 1, 0), site['name'], header_format)
            for i, head in enumerate(header[1:]):
                col = 1 + (i * 4)
                worksheet.merge_range(RNG(row, col, row, col + 3), head, header_format)
                for j, sub_head in enumerate(('Planned', 'Actual', 'Achievement (%)', 'UoM')):
                    worksheet.write(row + 1, col + j, sub_head, header_format)

            row += 2
            for operation in site['children']:
                worksheet.write(row, 0, operation['name'], subheader_format)
                width[0] = max((width[0], len(str(operation['name'])) + 2))

                total_planned, total_actual = 0.0, 0.0
                for j, (total_month_id, total_month) in enumerate(operation['months'].items()):
                    col = 1 + (j * 4)
                    worksheet.write(row, col, total_month['planned'], subheader_format)
                    worksheet.write(row, col + 1, total_month['actual'], subheader_format)
                    worksheet.write(row, col + 2, total_month['achievement'], subheader_format)
                    worksheet.write(row, col + 3, operation['uom_name'], subheader_format)

                    width[col] = max((width[col], len(str(total_month['planned'])) + 2))
                    width[col + 1] = max((width[col + 1], len(str(total_month['actual'])) + 2))
                    width[col + 2] = max((width[col + 2], len(str(total_month['achievement'])) + 2))
                    width[col + 3] = max((width[col + 3], len(str(operation['uom_name'])) + 2))

                    total_planned += total_month['planned']
                    total_actual += total_month['actual']
                
                total_achievement = (total_actual / total_planned) * 100 if total_planned > 0.0 else 0.0

                col = 1 + ((j + 1) * 4)
                worksheet.write(row, col, total_planned, bold_subheader_format)
                width[col] = max((width[col], len(str(total_planned)) + 2))

                col += 1
                worksheet.write(row, col, total_actual, bold_subheader_format)
                width[col] = max((width[col], len(str(total_actual)) + 2))

                col += 1
                worksheet.write(row, col, total_achievement, bold_subheader_format)
                width[col] = max((width[col], len(str(total_achievement)) + 2))

                col += 1
                worksheet.write(row, col, operation['uom_name'], bold_subheader_format)
                width[col] = max((width[col], len(operation['uom_name']) + 2))

                row += 1
                for mpa in operation['children']:
                    mpa_name = '    %s' % mpa['name']
                    worksheet.write(row, 0, mpa_name, bordered)
                    width[0] = max((width[0], len(str(mpa_name)) + 2))

                    total_planned, total_actual = 0.0, 0.0
                    for j, (month_id, month) in enumerate(mpa['months'].items()):
                        col = 1 + (j * 4)
                        worksheet.write(row, col, month['planned'], bordered)
                        worksheet.write(row, col + 1, month['actual'], bordered)
                        worksheet.write(row, col + 2, month['achievement'], bordered)
                        worksheet.write(row, col + 3, mpa['uom_name'], bordered)

                        width[col] = max((width[col], len(str(month['planned'])) + 2))
                        width[col + 1] = max((width[col + 1], len(str(month['actual'])) + 2))
                        width[col + 2] = max((width[col + 2], len(str(month['achievement'])) + 2))
                        width[col + 3] = max((width[col + 3], len(str(mpa['uom_name'])) + 2))

                        total_planned += month['planned']
                        total_actual += month['actual']

                    total_achievement = (total_actual / total_planned) * 100 if total_planned > 0.0 else 0.0

                    col = 1 + ((j + 1) * 4)
                    worksheet.write(row, col, total_planned, bold_bordered)
                    width[col] = max((width[col], len(str(total_planned)) + 2))

                    col += 1
                    worksheet.write(row, col, total_actual, bold_bordered)
                    width[col] = max((width[col], len(str(total_actual)) + 2))

                    col += 1
                    worksheet.write(row, col, total_achievement, bold_bordered)
                    width[col] = max((width[col], len(str(total_achievement)) + 2))

                    col += 1
                    worksheet.write(row, col, mpa['uom_name'], bold_bordered)
                    width[col] = max((width[col], len(mpa['uom_name']) + 2))
                    
                    row += 1


        for col, w in enumerate(width):
            worksheet.set_column(col, col, w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return attachment_id.id
