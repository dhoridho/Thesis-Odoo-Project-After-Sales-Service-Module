from collections import OrderedDict
from odoo import fields, models, api, _

import io
import base64
import xlsxwriter
import datetime


MONTHS_NAME = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July', 
    'August', 'September', 'October', 'November', 'December'
]

def format_float(value, rounding):
    return ("{:." + str(rounding) + "f}").format(value)


class ReportMiningAssetsEfficiency(models.AbstractModel):
    _name = 'report.equip3_mining_reports.mining_assets_efficiency_report'
    _description = 'Report Mining Assets Efficiency'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['mining.assets.efficiency.report'].browse(docids),
            'doc_model': 'mining.assets.efficiency.report',
        }


class MiningAssetsEfficiencyReport(models.TransientModel):
    _name = 'mining.assets.efficiency.report'
    _description = 'Assets Efficiency Report'

    @api.model
    def create(self, vals):
        if not vals.get('filter_site'):
            vals['filter_site'] = 'all'
        if not vals.get('filter_pit'):
            vals['filter_pit'] = 'all'
        if not vals.get('filter_year'):
            vals['filter_year'] = self._default_filter_year()
        return super(MiningAssetsEfficiencyReport, self).create(vals)

    @api.model
    def _get_site_selection(self):
        selection = [('all', 'All Sites')]
        for site in self.env['mining.site.control'].search([]):
            selection += [(str(site.id), site.display_name or 'False')]
        return selection

    @api.model
    def _get_pit_selection(self):
        selection = [('all', 'All Pits')]
        for pit in self.env['mining.project.control'].search([]):
            selection += [(str(pit.id), pit.display_name or 'False')]
        return selection

    @api.model
    def _default_filter_year(self):
        return fields.Date.today().replace(day=1, month=1)

    filter_site = fields.Selection(
        selection=_get_site_selection, 
        string='Filter Site',
        default='all'
    )
    filter_pit = fields.Selection(
        selection=_get_pit_selection, 
        string='Filter Pit',
        default='all'
    )
    filter_year = fields.Date(string='Filter Year', default=_default_filter_year)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def get_report_values(self):
        return {
            'filters': self.get_filters(),
            'data': self.get_asset_values(),
            'months': ['%s %s' % (month_name, self.filter_year.year) for month_name in MONTHS_NAME],
            'digits': int(self.env['ir.config_parameter'].sudo().get_param('equip3_mining_reports.mining_report_precision_rounding', default='1'))
        }

    def get_filters(self):
        site_selection = self.fields_get(allfields=['filter_site'])['filter_site']['selection']
        pit_selection = self.fields_get(allfields=['filter_pit'])['filter_pit']['selection']
        return {
            'filter_site': {
                'selection': site_selection,
                'active': (self.filter_site, dict(site_selection).get(self.filter_site, 'All Sites'))
            },
            'filter_pit': {
                'selection': pit_selection,
                'active': (self.filter_pit, dict(pit_selection).get(self.filter_pit, 'All Pits'))
            },
            'filter_year': self.filter_year,
        }

    def get_asset_values(self):
        date_from = datetime.date(self.filter_year.year, 1, 1)
        date_to = datetime.date(self.filter_year.year, 12, 31)
        act_domain = [
            ('state', '=', 'confirm'),
            ('period_from', '>=', date_from),
            ('period_from', '<=', date_to)
        ]
        if self.filter_site != 'all':
            site_id = self.env['mining.site.control'].browse(int(self.filter_site))
            act_domain += [('mining_site_id', '=', site_id.id)]

        if self.filter_pit != 'all':
            pit_id = self.env['mining.project.control'].browse(int(self.filter_pit))
            act_domain += [('mining_project_id', '=', pit_id.id)]

        act_ids = self.env['mining.production.actualization'].search(act_domain)
        operation_ids = act_ids.mapped('operation_id')

        data = []
        for operation in operation_ids:
            values = {
                'name': operation.display_name,
                'uom': operation.uom_id.display_name,
                'children': []
            }
            record_ids = act_ids.filtered(lambda a: a.operation_id == operation)

            if not record_ids:
                continue

            if operation.operation_type_id in ('production', 'extraction'):
                o2m_name = 'output_ids'
                qty_name = 'qty_done'
            else:
                o2m_name = 'delivery_ids'
                qty_name = 'total_amount'

            asset_ids = record_ids.mapped('assets_ids').mapped('assets_id')

            asset_uoms = {}
            for a_efficiency in record_ids.mapped('output_ids'):
                if a_efficiency.asset_id.id not in asset_uoms:
                    asset_uoms[a_efficiency.asset_id.id] = [a_efficiency.product_id.uom_id]
                else:
                    asset_uoms[a_efficiency.asset_id.id] += [a_efficiency.product_id.uom_id]

            for asset in asset_ids:
                child = {
                    'name': asset.display_name,
                    'uom': None,
                    'months': []
                }
                for month in range(1, 13):
                    act_month_ids = record_ids.filtered(lambda a: a.period_from.month == month)
                    production = sum(act_month_ids.mapped(o2m_name).mapped(qty_name))
                    total_hour_meter = sum(act_month_ids.mapped('assets_ids').filtered(lambda f: f.assets_id == asset).mapped('duration'))
                    child['months'] += [{
                        'production': production,
                        'total_hour_meter': total_hour_meter,
                        'assets_efficiency': total_hour_meter / production if total_hour_meter != 0 else production
                    }]
                values['children'] += [child]
            data += [values]

        return data

    def print_xlsx_report(self):
        file_name = 'Assets Efficiency Report.xlsx'

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
        worksheet.write(row, 0, '%s: %s' % (self.company_id.name, _('Assets Efficiency Report')), title_format)

        row += 2
        site_selection = self.fields_get(allfields=['filter_site'])['filter_site']['selection']
        pit_selection = self.fields_get(allfields=['filter_pit'])['filter_pit']['selection']

        worksheet.write(row, 0, 'Site', subtitle_format)
        worksheet.write(row, 1, ': %s' % dict(site_selection).get(self.filter_site, 'All Sites'), subtitle_format)
        worksheet.write(row + 1, 0, 'Pit', subtitle_format)
        worksheet.write(row + 1, 1, ': %s' % dict(pit_selection).get(self.filter_pit, 'All Pits'), subtitle_format)
        worksheet.write(row + 2, 0, 'Year', subtitle_format)
        worksheet.write(row + 2, 1, ': %s' % self.filter_year.year, subtitle_format)

        header = ['Operation'] + (['Total Hour Meter', 'Production', 'Assets Efficiency'] * 12)

        row += 4
        for i, head in enumerate(['Operation'] + ['%s %s' % (m, self.filter_year.year) for m in MONTHS_NAME]):
            if i == 0:
                worksheet.merge_range(RNG(row, 0, row + 1, 0), head, header_format)
            else:
                j = ((i - 1) * 3) + 1
                worksheet.merge_range(RNG(row, j, row, j + 2), head, header_format)

        row += 1
        width = []
        for i, head in enumerate(header):
            if i > 0:
                worksheet.write(row, i, head, header_format)
            width += [len(head) + 2]

        row += 1
        for operation in data:
            worksheet.merge_range(RNG(row, 0, row, 36), operation['name'], bold_bordered)

            row += 1
            for child in operation['children']:
                worksheet.write(row, 0, child['name'], bordered)
                width[0] = max([width[0], len(str(child['name'])) + 2])

                col = 1
                for month in child['months']:
                    for key, uom in zip(
                        ['production', 'total_hour_meter', 'assets_efficiency'],
                        [operation['uom'], child['uom'], '%s/%s' % (operation['uom'], child['uom'])]
                    ):
                        value = '%s' % (format_float(month[key], digits))
                        worksheet.write(row, col, value, key != 'fuel_ratio' and bordered or bold_bordered)
                        width[col] = max([width[col], len(str(value)) + 2])
                        col += 1
                row += 1

        for col, w in enumerate(width):
            worksheet.set_column(col, col, w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return attachment_id.id
