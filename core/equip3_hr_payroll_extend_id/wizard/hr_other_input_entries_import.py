# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError, Warning
import logging
import tempfile
import binascii
import datetime

_logger = logging.getLogger(__name__)

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

class HrOtherInputsEntriesImport(models.TransientModel):
    _name = "hr.other.input.entries.import"
    _description = 'Import Other Input Entries'

    import_file = fields.Binary(string="Import File")
    import_name = fields.Char('Import Name', size=64)

    def import_action(self):
        import_name_extension = self.import_name.split('.')[1]
        if import_name_extension not in ['xls', 'xlsx']:
            raise ValidationError('The upload file is using the wrong format. Please upload your file in xlsx or xls format.')
        
        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.import_file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        keys = sheet.row_values(0)
        xls_reader = [sheet.row_values(i) for i in range(1, sheet.nrows)]

        vals = []
        for row in xls_reader:
            line = dict(zip(keys, row))

            if line.get('Employee ID'):
                employee = self.env['hr.employee'].search([('sequence_code','=',line.get('Employee ID'))], limit=1)
                contract = self.env['hr.contract'].search([('employee_id','=',employee.id),('state','=','open')], limit=1)
                if not employee:
                    raise ValidationError(('Employee ID %s not found') % (line.get('Employee ID')))
                if not contract:
                    raise ValidationError(('Contract for Employee ID %s not found / not running') % line.get('Employee ID'))
            
            if line.get('Other Input Code'):
                other_inputs = self.env['hr.other.inputs'].search([('code','=',line.get('Other Input Code')),('state','=','confirm')], limit=1)
                if not other_inputs:
                    raise ValidationError(('Other Input Code %s not found') % line.get('Other Input Code'))
                if other_inputs.input_type == 'manual_entries':
                    input_type = 'Manual Entries'
                elif other_inputs.input_type == 'get_from_other_object':
                    input_type = 'Get from Other Object'

            if line.get('Payslip Period') and line.get('Month'):
                payslip_period = self.env['hr.payslip.period'].search([('code','=',int(line.get('Payslip Period'))),('state','=','open')], limit=1)
                payslip_period_line = self.env['hr.payslip.period.line'].search([('period_id','=',payslip_period.id),('month','=',line.get('Month')),('state','=','open')], limit=1)
                if not payslip_period:
                    raise ValidationError(('Payslip period %s not found') % int(line.get('Payslip Period')))
                if not payslip_period_line:
                    raise ValidationError(('Month %s not found in Payslip Period %s') % (line.get('Month'), int(line.get('Payslip Period'))))
            
            if line.get('Amount'):
                amount = float(line.get('Amount'))

            data = {
                'employee': employee.id,
                'employee_id': employee.sequence_code,
                'contract_id': contract.id,
                'contract': contract.name,
                'other_input_id': other_inputs.id,
                'code': other_inputs.code,
                'input_type': input_type,
                'payslip_period_id': payslip_period.id,
                'month': payslip_period_line.id,
                'periode_start_date': payslip_period_line.start_date,
                'periode_end_date': payslip_period_line.end_date,
                'amount': amount,
            }
            vals += [data]
        for rec in vals:
            check_entries = self.env['hr.other.input.entries'].search([('employee','=',rec['employee']),('other_input_id','=',rec['other_input_id']),('month','=',rec['month'])])
            if check_entries:
                check_entries.write({'amount': rec['amount']})
            else:
                self.env['hr.other.input.entries'].create(rec)