# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from datetime import datetime, date


class wizard_scrap_order_report(models.TransientModel):
    _name = 'wizard.scrap.order.report'
    _description = "Wizard Scrap Order Report"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    name = fields.Char(string='File Name', readonly=True)
    data = fields.Binary(string='File', readonly=True)

    def check_date_range(self):
        if self.end_date < self.start_date:
            raise ValidationError(_('End Date should be greater than Start Date.'))

    def get_scrap_order_data(self):
        scrap_order_obj = self.env['stock.scrap']
        scrap_order_obj = scrap_order_obj.search([('state','=','done'),('date_done','>=',self.start_date),
        ('date_done','<=',self.end_date),('company_id','=',self.company_id.id)],order='date_done')
        return scrap_order_obj

    def print_report(self):
        self.check_date_range()
        datas = {'form':
                    {
                        'id': self.id
                    },
                }
        return self.env.ref('eq_scrap_order_report.action_scrap_order_report_template').report_action(self, data=datas)

    def go_back(self):
        self.state = 'choose'
        return {
            'name': 'Scrap order Report',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new'
        }

    def print_xls_report(self):
        self.check_date_range()
        scrap_order_ids = self.get_scrap_order_data()
        has_lot_serial = scrap_order_ids.mapped('lot_id')
        xls_filename = 'Scrap Order Report.xlsx'
        workbook = xlsxwriter.Workbook('/tmp/' + xls_filename)

        header_merge_format = workbook.add_format({'bold':True, 'align':'center', 'valign':'vcenter', \
                                            'font_size':10, 'bg_color':'#D3D3D3', 'border':1})

        header_data_format = workbook.add_format({'align':'center', 'valign':'vcenter', \
                                                   'font_size':10, 'border':1})

        worksheet = workbook.add_worksheet('Scrap Order')
        if has_lot_serial:
            worksheet.merge_range(0, 0, 2, 5, "Scrap Order Report", header_merge_format)
        else:
            worksheet.merge_range(0, 0, 2, 4, "Scrap Order Report", header_merge_format)

        worksheet.set_column('A:B', 14)
        worksheet.set_column('C:C', 28)
        worksheet.set_column('D:F', 14)
        worksheet.write(5, 0, 'Company', header_merge_format)
        worksheet.write(5, 1, 'Start Date', header_merge_format)
        worksheet.write(5, 2, 'End Date', header_merge_format)

        worksheet.write(6, 0, self.company_id.name, header_data_format)
        worksheet.write(6, 1, self.start_date.strftime('%d-%m-%Y'), header_data_format)
        worksheet.write(6, 2, self.end_date.strftime('%d-%m-%Y'), header_data_format)
        rows = 10

        if has_lot_serial:
            worksheet.write(9, 0, "Date", header_merge_format)
            worksheet.write(9, 1, "Name", header_merge_format)
            worksheet.write(9, 2, "Product", header_merge_format)
            worksheet.write(9, 3, "Quantity", header_merge_format)
            worksheet.write(9, 4, "Lot/Serial Number", header_merge_format)
            worksheet.write(9, 5, "Location", header_merge_format)

            for record in scrap_order_ids:
                worksheet.write(rows, 0, record.date_done.strftime('%d-%m-%Y'), header_data_format)
                worksheet.write(rows, 1, record.name, header_data_format)
                worksheet.write(rows, 2, record.product_id.display_name, header_data_format)
                worksheet.write(rows, 3, str(record.scrap_qty) + ' ' + record.product_uom_id.name, header_data_format)
                worksheet.write(rows, 4, record.lot_id.name or '', header_data_format)
                worksheet.write(rows, 5, record.location_id.display_name, header_data_format)
                rows +=1

        else:
            worksheet.write(9, 0, "Date", header_merge_format)
            worksheet.write(9, 1, "Name", header_merge_format)
            worksheet.write(9, 2, "Product", header_merge_format)
            worksheet.write(9, 3, "Quantity", header_merge_format)
            worksheet.write(9, 4, "Location", header_merge_format)

            for record in scrap_order_ids:
                worksheet.write(rows, 0, record.date_done.strftime('%d-%m-%Y'), header_data_format)
                worksheet.write(rows, 1, record.name, header_data_format)
                worksheet.write(rows, 2, record.product_id.display_name, header_data_format)
                worksheet.write(rows, 3, str(record.scrap_qty) + ' ' + record.product_uom_id.name, header_data_format)
                worksheet.write(rows, 4, record.location_id.display_name, header_data_format)
                rows +=1

        worksheet.write(rows + 1, 2, "Total", header_merge_format)
        worksheet.write(rows + 1, 3, sum(scrap_order_ids.mapped('scrap_qty')), header_merge_format)

        workbook.close()
        self.write({
            'state': 'get',
            'data': base64.b64encode(open('/tmp/' + xls_filename, 'rb').read()),
            'name': xls_filename
        })
        return {
            'name': 'Scrap Order Report',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new'
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: