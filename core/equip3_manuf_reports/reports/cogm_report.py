import io
import json
import base64
import xlsxwriter
import calendar

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.parser import parse

MONTH_NAMES = [
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december'
]

class ReportCOGMReport(models.AbstractModel):
    _name = 'report.equip3_manuf_reports.cogm_report'
    _description = 'Cost of Goods Manufactured Report Abstract'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['cogm.report'].browse(docids),
            'doc_model': 'cogm.report'
        }


class COGMReport(models.TransientModel):
    _name = 'cogm.report'
    _description = 'Cost of Goods Manufactured Report'

    data = fields.Text(required=True)

    @api.constrains('data')
    def _check_data(self):
        for record in self:
            try:
                json.loads(record.data)
            except Exception as err:
                raise ValidationError(str(err))

    @api.model
    def format_currency(self, amount):
        if isinstance(amount, float) or isinstance(amount, int):
            formatted = '%s %s' % (self.env.company.currency_id.symbol, abs(round(amount, 2)))
            if amount >= 0:
                return formatted
            return '- ' + formatted
        return amount

    def _parse_data(self):
        self.ensure_one()
        data = json.loads(self.data)
        data['company_id'] = [self.env.company.id, self.env.company.display_name]
        return data

    def _get_beginning_inventory(self, date_start, date_end):
        return sum(self.env['stock.quant'].search([
            ('in_date', '<=', date_start),
            ('product_id.manuf_type', '=', 'type_material')
        ]).mapped('value'))

    def _get_purchase_of_direct_material(self, date_start, date_end):
        po_lines = self.env['purchase.order.line'].search([
            ('product_id.manuf_type', '=', 'type_material'),
            ('date_received', '>=', date_start),
            ('date_received', '<=', date_end)
        ])
        untaxed_amount = [line.qty_received * line.price_unit for line in po_lines]
        return sum(untaxed_amount) if untaxed_amount else 0.0

    def _get_ending_inventory(self, date_start, date_end):
        return sum(self.env['stock.quant'].search([
            ('in_date', '<=', date_end),
            ('product_id.manuf_type', '=', 'type_material')
        ]).mapped('value'))

    def _get_overhead_cost(self, date_start, date_end):
        return self.env['mrp.cost.actualization.valuation'].search([
            ('mrp_cost_actualization_id.state', '=', 'post'),
            ('mrp_cost_actualization_id.date_from', '>', date_start),
            ('mrp_cost_actualization_id.date_to', '<', date_end),
        ])

    def _get_beginning_wip(self, date_start, date_end):
        return sum(self.env['stock.quant'].search([
            ('in_date', '<=', date_start),
            ('product_id.manuf_type', '=', 'type_wip')
        ]).mapped('value'))

    def _get_ending_balance_wip(self, date_start, date_end):
        return sum(self.env['stock.quant'].search([
            ('in_date', '<=', date_end),
            ('product_id.manuf_type', '=', 'type_wip')
        ]).mapped('value'))

    def _prepare_html_data(self, data, filters):

        is_default_folded = 'folded' not in filters
        folded = filters.get('folded', [])

        for line in data:
            sections = line['section'].split('_')
            level = len(sections) - 1

            children = []
            for child in data:
                if '_'.join(child['section'].split('_')[:-1]) == line['section']:
                    children += [child['section']]

            class_list = ['o_level_%s' % level, line.get('class', '')]
            if level > 2:
                class_list += ['collapse']
                if not is_default_folded and line['section'] not in folded:
                    class_list += ['show']

            line.update({
                'class': ' '.join(class_list),
                'level': level,
                'position': line.get('position', 'left'),
                'show_values': line.get('show_values', True),
                'parent': False if line['section'] == '0' else '_'.join(sections[:-1]),
                'children': children,
                'data': {
                    'toggle': len(children) > 0 and 'collapse' or '',
                    'target': ','.join(["[data-section='%s']" % csection for csection in children])
                }
            })

        return data

    def _data_flat(self, filters):
        date_from = fields.Date.from_string(filters['date_from'])

        return [
            {
                'title': _('Cost of Goods Manufactured'),
                'section': '0'
            },
            {
                'title': _('Direct Material Used in Operation'),
                'section': '0_1',
                'show_values': False
            },
            {
                'title': _('Direct Materials'),
                'section': '0_1_0',
                'show_values': False
            },
            {
                'title': _('Begining Inventory %s %s' % (MONTH_NAMES[date_from.month - 1].title(), date_from.year)),
                'section': '0_1_0_0'
            },
            {
                'title': _('Purchase of Direct Material'),
                'section': '0_1_0_1'
            },
            {
                'title': _(''),
                'section': '0_1_0_2',
                'class': 'o_bold o_border_top'
            },
            {
                'title': _('Ending Inventory'),
                'section': '0_1_0_3'
            },
            {
                'title': _('Direct Material Used'),
                'section': '0_1_1',
                'position': 'right',
                'class': 'o_bold'
            },
            {
                'title': _('Total Production Cost'),
                'section': '0_2',
                'show_values': False
            },
            {
                'title': _('Direct Material Used in Operation'),
                'section': '0_2_0',
                'position': 'right'
            },
            {
                'title': _('Overhead Cost'),
                'section': '0_2_1',
                'show_values': False
            },
            {
                'title': _('Material'),
                'section': '0_2_1_0'
            },
            {
                'title': _('Overhead'),
                'section': '0_2_1_1'
            },
            {
                'title': _('Labor'),
                'section': '0_2_1_2'
            },
            {
                'title': _('Subcontracting'),
                'section': '0_2_1_3'
            },
            {
                'title': _('Production Overhead Cost'),
                'section': '0_2_2',
                'position': 'right',
                'class': 'o_bold'
            },
            {
                'title': _('Manufacturing Cost Incured'),
                'section': '0_2_3',
                'position': 'right',
                'class': 'o_bold o_border_top'
            },
            {
                'title': _('Cost of Goods Manufactured'),
                'section': '0_3',
                'show_values': False
            },
            {
                'title': _('Total Production Cost'),
                'section': '0_3_0',
                'position': 'right'
            },
            {
                'title': _('Beginnig WIP'),
                'section': '0_3_1',
                'position': 'right'
            },
            {
                'title': _('Total Manufacturing Cost to Account for'),
                'section': '0_3_2',
                'position': 'right',
                'class': 'o_bold o_border_top'
            },
            {
                'title': _('Ending Balance of WIP'),
                'section': '0_3_3',
                'position': 'right'
            },
            {
                'title': _('COGM'),
                'section': '0_3_4',
                'position': 'right',
                'class': 'o_bold o_border_top'
            }
        ]

    @api.model
    def get_report_data(self, filters):
        data = self._data_flat(filters)

        dindex = {}
        for index, d in enumerate(data):
            d['values'] = []
            dindex[d['section']] = index

        for drange in filters['date_ranges']:
            date_from = fields.Date.from_string(drange['from'])
            date_to = fields.Date.from_string(drange['to'])

            for d in data:
                d['values'] += [{'date_from': date_from, 'date_to': date_to, 'value': 0.0}]
            
            mca_valuations = self._get_overhead_cost(date_from, date_to)

            data[dindex['0']]['values'][-1].update({'value': '%s to %s' % (date_from.strftime('%Y/%m/%d'), date_to.strftime('%Y/%m/%d'))})
            data[dindex['0_1_0_0']]['values'][-1].update({'value': self._get_beginning_inventory(date_from, date_to)})
            data[dindex['0_1_0_1']]['values'][-1].update({'value': self._get_purchase_of_direct_material(date_from, date_to)})
            data[dindex['0_1_0_3']]['values'][-1].update({'value': self._get_ending_inventory(date_from, date_to)})
            data[dindex['0_2_1_0']]['values'][-1].update({'value': sum(mca_valuations.filtered(lambda m: m.category == 'material').mapped('add_cost'))})
            data[dindex['0_2_1_1']]['values'][-1].update({'value': sum(mca_valuations.filtered(lambda m: m.category == 'overhead').mapped('add_cost'))})
            data[dindex['0_2_1_2']]['values'][-1].update({'value': sum(mca_valuations.filtered(lambda m: m.category == 'labor').mapped('add_cost'))})
            data[dindex['0_2_1_3']]['values'][-1].update({'value': sum(mca_valuations.filtered(lambda m: m.category == 'subcontracting').mapped('add_cost'))})
            data[dindex['0_3_1']]['values'][-1].update({'value': self._get_beginning_wip(date_from, date_to)})
            data[dindex['0_3_3']]['values'][-1].update({'value': self._get_ending_balance_wip(date_from, date_to)})

            data[dindex['0_1_0_2']]['values'][-1].update({
                'value': data[dindex['0_1_0_0']]['values'][-1]['value'] + data[dindex['0_1_0_1']]['values'][-1]['value'],
            })
            data[dindex['0_1_1']]['values'][-1].update({
                'value': data[dindex['0_1_0_2']]['values'][-1]['value'] + data[dindex['0_1_0_3']]['values'][-1]['value']
            })
            data[dindex['0_2_0']]['values'][-1].update({
                'value': data[dindex['0_1_1']]['values'][-1]['value'],
            })
            data[dindex['0_2_2']]['values'][-1].update({
                'value': data[dindex['0_2_1_0']]['values'][-1]['value'] + data[dindex['0_2_1_1']]['values'][-1]['value'] + data[dindex['0_2_1_2']]['values'][-1]['value'],
            })
            data[dindex['0_2_3']]['values'][-1].update({
                'value': data[dindex['0_2_0']]['values'][-1]['value'] + data[dindex['0_2_2']]['values'][-1]['value'],
            })
            data[dindex['0_3_0']]['values'][-1].update({
                'value': data[dindex['0_2_3']]['values'][-1]['value'],
            })
            data[dindex['0_3_2']]['values'][-1].update({
                'value': data[dindex['0_3_0']]['values'][-1]['value'] + data[dindex['0_3_1']]['values'][-1]['value'],
            })
            data[dindex['0_3_4']]['values'][-1].update({
                'value': data[dindex['0_3_2']]['values'][-1]['value'] + data[dindex['0_3_3']]['values'][-1]['value'],
            })

        data = self._prepare_html_data(data, filters)
        return {
            'data': data,
            'currency_id': self.env.company.currency_id.id
        }

    def print_xlsx_report(self):
        self.ensure_one()
        file_name = 'Cost of Goods Manufactured Report.xlsx'

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        RNG = xlsxwriter.utility.xl_range

        style = {
            'title': workbook.add_format({
                'bold': 1,
                'font_size': 15
            }),
            'bordered': workbook.add_format({
                'border': 1
            }),
            'bold_bordered': workbook.add_format({
                'bold': 1,
                'border': 1
            }),
            'currency_bordered': workbook.add_format({
                'num_format': '%s#.##0' % self.env.company.currency_id.symbol,
                'border': 1
            }),
            'currency_bold_bordered': workbook.add_format({
                'num_format': '%s#.##0' % self.env.company.currency_id.symbol,
                'border': 1,
                'bold': 1
            })
        }

        doc_data = self._parse_data()
        n = 1 + (len(doc_data['data'][0]['values']) * 2)

        title = '%s: %s' % (self.env.company.display_name, 'Cost of Goods Manufactured Report')
        worksheet.write(1, 0, title, style['title'])

        row = 3
        width = [0 for i in range(n)]
        for data in doc_data['data']:
            cell_style = style['bordered']
            if data['level'] <= 1:
                cell_style = style['bold_bordered']

            if data['level'] != 1:
                worksheet.write(row, 0, data['title'], cell_style)
                width[0] = max([width[0], len(data['title']) + 2])
            else:
                worksheet.merge_range(RNG(row, 0, row, n - 1), data['title'], cell_style)
                row += 1
                continue

            for i, value in enumerate(data['values']):
                if data['level'] == 0:
                    c = 1 + (i * 2)
                    worksheet.merge_range(RNG(row, c, row, c + 1), value['value'], cell_style)
                    continue
                
                cell_style = style['currency_bordered']
                if 'o_bold' in data['class']:
                    cell_style = style['currency_bold_bordered']

                for j, pos in enumerate(['left', 'right']):
                    v = ''
                    if data['position'] == pos and data['show_values']:
                        v = value['value']
                        if data['section'] != '0':
                            v = round(value['value'], 2)

                    col = 1 + ((i * 2) + j)
                    worksheet.write(row, col, v, cell_style)
                    width[col] = max([width[col], len(str(v)) + 8])

            row += 1

        for col, w in enumerate(width):
            worksheet.set_column(col, col, w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return attachment_id.id
