import io
import base64
import xlsxwriter
import locale

from collections import OrderedDict
from odoo import api, models, _
from odoo.exceptions import ValidationError


class AgricultureListReport(models.AbstractModel):
    _name = 'agriculture.list.report'
    _description = 'List View Report'

    # True: will print all records without paging, and all fields is set based _get_header_fields, _get_aggregate_fields, and _get_grouped_fields
    # False: will print records that showed in list view
    print_all_records = False

    # to override
    @api.model
    def _get_report_name(self):
        return _('Agriculture Report')

    # to override
    @api.model
    def _get_header_fields(self):
        return []

    # to override
    @api.model
    def _get_aggregate_fields(self):
        return []

    # to override
    @api.model
    def _get_grouped_fields(self):
        return []

    @api.model
    def _construct_header(self):
        header = OrderedDict()
        for field_name in self._get_header_fields():
            field_obj = self._fields[field_name]
            header[field_name] = {
                'label': field_obj.string,
                'aggregate': field_name in self._get_aggregate_fields(),
                'type': field_obj.type
            }
        return header

    @api.model
    def get_report_values(self, state):

        if self.print_all_records:
            self._cr.execute(self._query())
            state = self._get_group(self._cr.dictfetchall())

        header = self._get_header_fields()

        def flatten_state(lines, data, level=0):
            for line in data:
                values = {field_name: '' for field_name in header}
                values['type'] = line['type']
                values['level'] = level

                if line['type'] == 'record':
                    for field_name in header:
                        try:
                            values[field_name] = line['data'][field_name]['data']['display_name']
                        except TypeError:
                            values[field_name] = line['data'][field_name]
                    lines += [values]
                else:
                    for field_name, aggregate in line['aggregateValues'].items():
                        values[field_name] = aggregate
                    values[header[0]] = line['value']
                    lines += [values]
                    flatten_state(lines, line['data'], level=level+1)

        report_lines = []
        flatten_state(report_lines, state['data'])

        first_section = [line for line in report_lines if line['level'] == 0]
        total_line = {field_name: '' for field_name in header}
        for field_name in header:
            try:
                total_value = sum(line[field_name] for line in first_section)
            except TypeError:
                total_value = ''
            total_line[field_name] = total_value

        total_line[header[0]] = 'Total'
        total_line['type'] = 'total'
        total_line['level'] = 0
        
        report_lines += [total_line]
        return report_lines

    @api.model
    def _get_field_value(self, f_name, field_value, force_str=False):
        field_name = f_name.split(':')[0]
        if self._fields[field_name].type == 'many2one':
            obj = self.env[self._fields[field_name].comodel_name].browse(field_value)
            return obj.display_name
        if ':' in f_name and self._fields[field_name].type in ('date', 'datetime'):
            locale.setlocale(locale.LC_ALL, 'en_US.utf8')
            abbv = f_name.split(':')[-1]
            if abbv == 'year':
                return field_value.strftime('%Y')
            elif abbv == 'month':
                return field_value.strftime('%B %Y')
            elif abbv == 'day':
                return field_value.strftime('%A %B %Y')
            else:
                raise ValidationError(_('%s is not valid date/datetime format!'))
        if self._fields[field_name].type == 'date':
            return field_value.strftime('%Y-%m-%d')
        if self._fields[field_name].type == 'datetime':
            return field_value.strftime('%Y-%m-%d %H:%M:%S')
        if force_str:
            return str(field_value)
        return field_value

    @api.model
    def _get_group(self, lines, index=0, parent=None):

        def ensure_value(rec, fname):
            try:
                return rec[fname]
            except KeyError:
                return rec[fname.split(':')[0]]

        group = OrderedDict()
        group['aggregateValues'] = {agg_field: 0 for agg_field in self._get_aggregate_fields()}
        group['type'] = 'list'
        group['value'] = parent
        group['data'] = []
        try:
            field_name = self._get_grouped_fields()[index]
        except IndexError:
            for line in lines:
                values = OrderedDict({'type': 'record', 'data': {}})
                for head_field in self._get_header_fields():
                    values['data'][head_field] = self._get_field_value(head_field, ensure_value(line, head_field))
                group['data'] += [values]
            for agg_field in self._get_aggregate_fields():
                group['aggregateValues'][agg_field] = sum(v['data'][agg_field] for v in group['data'])
            return group
                
        field_values = OrderedDict()
        for line in lines:
            field_value = self._get_field_value(field_name, ensure_value(line, field_name), force_str=True)
            if field_value not in field_values:
                field_values[field_value] = [line]
            else:
                field_values[field_value] += [line]

        for field_value, child_lines in field_values.items():
            data = self._get_group(child_lines, index=index+1, parent=field_value)
            group['data'] += [data]

        for agg_field in self._get_aggregate_fields():
            group['aggregateValues'][agg_field] = sum(g['aggregateValues'][agg_field] for g in group['data'])
            
        return group

    @api.model
    def get_xlsx_report(self, state):
        file_name = '%s.xlsx' % self._get_report_name()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        styles = {
            'title': workbook.add_format({
                'bold': 1,
                'font_size': 15
            }),
            'header':  workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            }),
            'list': workbook.add_format({
                'bold': 1,
                'border': 1,
                'bg_color': '#dee2e6'
            }),
            'total': workbook.add_format({
                'bold': 1,
                'border': 1
            }),
            'record': workbook.add_format({
                'border': 1
            })
        }

        header = self._construct_header()
        width = []

        row = 1
        worksheet.write(row, 0, '%s: %s' % (self.env.company.name, self._get_report_name()), styles['title'])

        row += 2
        for col, (field_name, head) in enumerate(header.items()):
            worksheet.write(row, col, head['label'], styles['header'])
            width += [len(head['label']) + 2]

        row += 1
        for line in self.get_report_values(state):
            style = styles[line['type']]

            for col, (field_name, head) in enumerate(header.items()):
                value = line[field_name]
                if col == 0:
                    value = '%s%s' % (' ' * (4 * line['level']), value)
                worksheet.write(row, col, value, style)
                width[col] = max([width[col], len(str(value)) + 2])

            row += 1

        for col, w in enumerate(width):
            worksheet.set_column(col, col, w + 10 if col == 0 else w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return attachment_id.id
