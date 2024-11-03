# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.web.controllers.main import GroupExportXlsxWriter


def _write_group_header(self, row, column, label, group, group_depth=0):
    aggregates = group.aggregated_values

    label = '%s%s (%s)' % ('    ' * group_depth, label, group.count)
    self.write(row, column, label, self.header_bold_style)
    self.monetary_format = f'#,##0'
    for field in self.fields[1:]: # No aggregates allowed in the first column because of the group title
        column += 1
        aggregated_value = aggregates.get(field['name'])
        if field.get('type') == 'monetary':
            self.header_bold_style.set_num_format(self.monetary_format)
        elif field.get('type') == 'float':
            self.header_bold_style.set_num_format(self.float_format)
        else:
            aggregated_value = aggregated_value if aggregated_value is not None else ''
        self.write(row, column, aggregated_value, self.header_bold_style)
    return row + 1, 0

GroupExportXlsxWriter._write_group_header = _write_group_header
