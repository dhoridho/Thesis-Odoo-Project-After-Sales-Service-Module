from collections import OrderedDict
from odoo import fields, models, api, _

import io
import base64
import xlsxwriter
import datetime


def format_float(value, rounding):
    return ("{:." + str(rounding) + "f}").format(value)


class ReportMiningStrippingRatio(models.AbstractModel):
    _name = 'report.equip3_mining_reports.mining_stripping_ratio_report'
    _description = 'Report Mining Stripping Ratio'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['mining.stripping.ratio.report'].browse(docids),
            'doc_model': 'mining.stripping.ratio.report',
        }


class MiningStrippingRatioReport(models.TransientModel):
    _name = 'mining.stripping.ratio.report'
    _description = 'Stripping Ratio Report'

    @api.model
    def create(self, vals):
        if not vals.get('filter_site'):
            vals['filter_site'] = 'all'
        if not vals.get('filter_year'):
            vals['filter_year'] = self._default_filter_year()
        if not vals.get('filter_period'):
            vals['filter_period'] = 'quarterly'
        return super(MiningStrippingRatioReport, self).create(vals)

    @api.model
    def _get_site_selection(self):
        selection = [('all', 'All Sites')]
        for site in self.env['mining.site.control'].search([]):
            selection += [(str(site.id), site.display_name or 'False')]
        return selection

    @api.model
    def _default_filter_year(self):
        return fields.Date.today().replace(day=1, month=1)

    filter_site = fields.Selection(
        selection=_get_site_selection, 
        string='Filter Site',
        default='all'
    )
    filter_year = fields.Date(string='Filter Year', default=_default_filter_year)
    filter_period = fields.Selection(
        selection=[
            ('quarterly', 'Quarterly'),
            ('half', 'Half-year')
        ],
        string='Filter Period',
        default='quarterly'
    )
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def get_report_values(self):
        return {
            'filters': self.get_filters(),
            'data': self.get_asset_values(),
            'digits': int(self.env['ir.config_parameter'].sudo().get_param('equip3_mining_reports.mining_report_precision_rounding', default='1')),
        }

    def get_filters(self):
        site_selection = self.fields_get(allfields=['filter_site'])['filter_site']['selection']
        period_selection = self.fields_get(allfields=['filter_period'])['filter_period']['selection']
        return {
            'filter_site': {
                'selection': site_selection,
                'active': (self.filter_site, dict(site_selection).get(self.filter_site, 'All Sites'))
            },
            'filter_year': self.filter_year,
            'filter_period': {
                'selection': period_selection,
                'active': (self.filter_period, dict(period_selection).get(self.filter_period, 'Quarterly'))
            }
        }

    def get_asset_values(self):
        date_from = datetime.date(self.filter_year.year, 1, 1)
        date_to = datetime.date(self.filter_year.year, 12, 31)

        act_domain = [
            ('state', '=', 'confirm'),
            ('period_from', '>=', date_from),
            ('period_from', '<=', date_to)
        ]
        strip_domain = []
        if self.filter_site != 'all':
            site_id = self.env['mining.site.control'].browse(int(self.filter_site))
            act_domain += [('mining_site_id', '=', site_id.id)]
            strip_domain += [('site_id', '=', site_id.id)]

        act_ids = self.env['mining.production.actualization'].search(act_domain)
        strip_ids = self.env['mining.stripping.ratio'].search(strip_domain)

        data = []
        for strip in strip_ids:
            waste_operation = strip.waste_operation_id
            waste_products = strip.waste_ids
            ore_operation = strip.ore_operation_id
            ore_products = strip.ore_ids

            values = {
                'id': strip.id,
                'waste': {
                    'operation': waste_operation.display_name,
                    'products': ', '.join(product.display_name for product in waste_products),
                    'months': []
                },
                'ore': {
                    'operation': ore_operation.display_name,
                    'products': ', '.join(product.display_name for product in ore_products),
                    'months': []
                },
                'total': {
                    'operation': 'Total',
                    'months': [{'qty': 0, 'uom': ''} for i in range(12)]
                }
            }

            for month in range(1, 13):
                record_ids = act_ids.filtered(lambda a: a.period_from.month == month)
                waste_records = record_ids.filtered(lambda r: r.operation_id == waste_operation)
                ore_records = record_ids.filtered(lambda r: r.operation_id == ore_operation)

                for name, operation, records, products in zip(
                    ['waste', 'ore'],
                    [waste_operation, ore_operation], 
                    [waste_records, ore_records],
                    [waste_products, ore_products]
                ):
                    if operation.operation_type_id in ('production', 'extraction'):
                        field_line = 'output_ids'
                        field_qty = 'qty_done'
                    else:
                        field_line = 'delivery_ids'
                        field_qty = 'total_amount'

                    lines = records.mapped(field_line).filtered(lambda l: l.product_id in products)

                    qty = sum(lines.mapped(field_qty))
                    uom = lines[0].uom_id.display_name if lines else products[0].uom_id.display_name
                    values[name]['months'] += [{'qty': qty, 'uom': uom}]
                    
                for month, (w, o) in enumerate(zip(values['waste']['months'], values['ore']['months'])):
                    values['total']['months'][month]['qty'] = w['qty'] / o['qty'] if o['qty'] > 0 else 0
                    values['total']['months'][month]['uom'] = '%s/%s' % (w['uom'], o['uom']) if w['uom'] or o['uom'] else ''

            data += [values]

        return data

    def print_xlsx_report(self):
        file_name = 'Stripping Ratio Report.xlsx'

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
            'bg_color': '#ECECEC',
        })

        bold_bordered = workbook.add_format({
            'bold': 1,
            'border': 1,
        })

        bordered = workbook.add_format({
            'border': 1
        })

        bold = workbook.add_format({
            'bold': 1
        })

        data = self.get_asset_values()
        digits = int(self.env['ir.config_parameter'].sudo().get_param('equip3_mining_reports.mining_report_precision_rounding', default=2))

        row = 1
        worksheet.write(row, 0, '%s: %s' % (self.company_id.name, _('Stripping Ratio Report')), title_format)

        row += 2
        site_selection = self.fields_get(allfields=['filter_site'])['filter_site']['selection']
        period_selection = self.fields_get(allfields=['filter_period'])['filter_period']['selection']

        worksheet.write(row, 0, 'Site', subtitle_format)
        worksheet.write(row, 1, ': %s' % dict(site_selection).get(self.filter_site, 'All Sites'), subtitle_format)
        worksheet.write(row + 1, 0, 'Year', subtitle_format)
        worksheet.write(row + 1, 1, ': %s' % self.filter_year.year, subtitle_format)
        worksheet.write(row + 2, 0, 'Period', subtitle_format)
        worksheet.write(row + 2, 1, ': %s' % dict(period_selection).get(self.filter_period, 'Quarterly'), subtitle_format)

        if self.filter_period == 'quarterly':
            header = ['Operation',
                'January', 'February', 'March', 'Total', 
                'April', 'May', 'June', 'Total', 
                'July', 'August', 'September', 'Total', 
                'October', 'Novermber', 'December', 'Total'
            ]
        else:
            header = ['Operation',
                'January', 'February', 'March', 'April', 'May', 'June', 'Total', 
                'July', 'August', 'September', 'October', 'Novermber', 'December', 'Total'
            ]

        row += 4
        width = []
        for strip in data:
            worksheet.write(row, 0, 'Waste', bold)
            worksheet.write(row, 1, ': ' + strip['waste']['products'])
            worksheet.write(row, 3, 'Ore', bold)
            worksheet.write(row, 4, ': ' + strip['ore']['products'])
            row += 1

            if self.filter_period == 'quarterly':
                worksheet.merge_range(RNG(row, 0, row + 1, 0), 'Operation', header_format)
                worksheet.merge_range(RNG(row, 1, row, 4), 'Q1', header_format)
                worksheet.merge_range(RNG(row, 5, row, 8), 'Q2', header_format)
                worksheet.merge_range(RNG(row, 9, row, 12), 'Q3', header_format)
                worksheet.merge_range(RNG(row, 13, row, 16), 'Q4', header_format)
            else:
                worksheet.merge_range(RNG(row, 0, row + 1, 0), 'Operation', header_format)
                worksheet.merge_range(RNG(row, 1, row, 7), 'H1', header_format)
                worksheet.merge_range(RNG(row, 8, row, 14), 'H2', header_format)
            row += 1

            for i, head in enumerate(header):
                if i > 0:
                    worksheet.write(row, i, head, header_format)
                width += [len(head) + 2]
            row += 1

            for key in ['waste', 'ore', 'total']:
                worksheet.write(row, 0, strip[key]['operation'], bordered)
                width[0] = max([width[0], len(str(strip[key]['operation'])) + 2])

                col = 1
                total = 0
                for i, line in enumerate(strip[key]['months']):
                    value = '%s %s' % (format_float(line['qty'], digits), line['uom'])
                    worksheet.write(row, col, value, key == 'total' and bold_bordered or bordered)
                    width[col] = max([width[col], len(str(value)) + 2])

                    total += line['qty']

                    if i in (5, 11) or (self.filter_period == 'quarterly' and i in (2, 8)):
                        value = '%s %s' % (format_float(total, digits), line['uom'])
                        worksheet.write(row, col + 1, value, bold_bordered)
                        width[col + 1] = max([width[col + 1], len(str(value)) + 2])
                        total = 0
                        col += 1

                    col += 1
                row += 1
            row += 1

        for col, w in enumerate(width):
            worksheet.set_column(col, col, w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return attachment_id.id
