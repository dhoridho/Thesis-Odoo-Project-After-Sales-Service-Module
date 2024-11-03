import time
import base64
import tempfile
from datetime import datetime
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class BinaryOcbcBankFileWizard(models.TransientModel):
    _name = 'binary.ocbc.bank.file.wizard'
    _description = "OCBC Bank File"

    cpf_txt_file = fields.Binary(
        'Click On Download Link To Download Text File', readonly=True)
    name = fields.Char('Name')


class OcbcBankSpecification(models.TransientModel):
    _name = 'ocbc.bank.specification'
    _description = "OCBC Bank Specification"

    @api.model
    def create(self, vals):
        if vals and vals.get('branch_number') and \
                len(str(vals.get('branch_number'))) > 3:
            raise ValidationError(_(
                "Branch number length must be less than or equal "
                "to three digits."))
        if vals and vals.get('batch_number') and \
                len(str(vals.get('batch_number'))) > 3:
            raise ValidationError(_(
                "Batch number length must be less than or equal "
                "to three digits."))
        if vals and vals.get('account_number') and \
                len(str(vals.get('account_number'))) > 9:
            raise ValidationError(_(
                "Account number length must be less than or equal "
                "to nine digits."))
        return super(OcbcBankSpecification, self).create(vals)

    def _get_value_time(self):
        return datetime.today().strftime("%H%M")

    branch_number = fields.Integer(
        'Branch Number', required=True,
        help="Branch number for your bank account")
    batch_number = fields.Integer(
        'Batch Number', required=True,
        help="Batch number for your bank account")
    account_number = fields.Integer(
        'Account Number', required=True,
        help="Employee bank account number")
    start_date = fields.Date(
        'Start Date', required=True,
        default=lambda *a: time.strftime('%Y-%m-01'))
    end_date = fields.Date(
        'End Date', required=True,
        default=lambda *a: str(datetime.now() + relativedelta(
            months=+1, day=1, days=-1))[:10])
    value_date = fields.Date(
        "Value Date", required=True,
        default=lambda *a: datetime.now().strftime('%Y-%m-%d'),
        help="Select any date for value date")
    transaction_code = fields.Selection(
        selection=[('20', '20 - Sundry Credit'),
                   ('21', '21 - Standing Instruction'),
                   ('22', '22 - Salary Credit'),
                   ('23', '23 - Dividend'),
                   ('24', '24 - Inward Remittance'),
                   ('25', '25 - Proceeds of Bill'),
                   ('30', '30 - Direct Debit')],
        string='Transaction Code', required=True, default='20',
        help="Select transaction type for ocbc file")
    on_behalf_of = fields.Char("On Behalf Of", help="Value for on behalf of")
    clearing = fields.Selection([
        ('giro', 'GIRO'), ('fast', 'FAST')], string="Clearing",
        help="Select clearing value from selection")
    reference_no = fields.Char(
        "Reference No", help="Provide your reference number")
    payment_detail = fields.Char(
        "Payment Detail", help="Enter detail related to payment")
    purpose_code = fields.Selection([
        ('OTHR', 'OTHR'), ('SALA', 'SALA'), ('COLL', 'COLL')],
        string="Purpose Code", default="SALA",
        help="Select purpose code from selection")
    invoice_send = fields.Selection([
        ('E', 'Email'), ('F', 'Fax')], string="Invoice Send Mode",
        help="Select invoice send mode detail")
    invoice_send_numebr = fields.Char(
        "Email/Fax Number", help="Enter number for selected invoice send mode")
    record_type = fields.Char(
        "Record Type", help="Enter record type detail")
    invoice_detail = fields.Char(
        "Invoice Detail", help="Enter invoice detail")
    value_time = fields.Integer(
        "Value Time", default=_get_value_time, help="Enter time")
    submission_date = fields.Date(
        "Submission Date", help="Select any date for submission date")
    debtors_reference = fields.Char(
        "Debtors Reference", help="Enter debtors reference detail")

    def get_text_file(self):
        context = dict(self._context) or {}
        data = {}
        wiz_data = self.read([])
        if wiz_data:
            data = wiz_data[0]
        start_date = data.get('start_date', False)
        end_date = data.get('end_date', False)
        if start_date >= end_date:
            raise ValidationError(
                _("You must be enter start date less than end date !"))
        context.update({'branch_number': data.get('branch_number'),
                        'account_number': data.get("account_number"),
                        'end_date': data.get('end_date'),
                        'start_date': data.get('start_date'),
                        'value_date': data.get("value_date"),
                        'batch_number': data.get("batch_number"),
                        'transaction_code': data.get("transaction_code"),
                        'on_behalf_of': data.get("on_behalf_of"),
                        'clearing': data.get("clearing"),
                        'reference_no': data.get("reference_no"),
                        'payment_detail': data.get("payment_detail"),
                        'purpose_code': data.get("purpose_code"),
                        'invoice_send': data.get("invoice_send"),
                        'invoice_send_numebr': data.get("invoice_send_numebr"),
                        'record_type': data.get("record_type"),
                        'invoice_detail': data.get("invoice_detail"),
                        'value_time': data.get("value_time"),
                        'submission_date': data.get('submission_date'),
                        'debtors_reference': data.get('debtors_reference')})
        user_data = self.env.user
        context.update({'company_name': user_data.company_id.name})
        tgz_tmp_filename = tempfile.mktemp('.' + "txt")
        tmp_file = open(tgz_tmp_filename, "w")
        try:
            if not start_date and end_date:
                return False

            header2_record = ''
            header2_record += ('%02s' % context.get(
                                        'transaction_code')).ljust(2)
            header2_record += ('%03d' % context.get('batch_number')).ljust(3)
            if context.get("submission_date"):
                submission_date = context.get("submission_date")
                header2_record += submission_date.strftime('%Y%m%d').ljust(8)
            else:
                header2_record += "".ljust(8)
            emp_ids = self.env['hr.employee'
                               ].search([('bank_account_id', '!=', False)],
                                        order="name")
            for employee in emp_ids:
                bank_code = employee.bank_account_id and \
                            employee.bank_account_id.bank_bic or ''
                if len(bank_code) <= 4:
                    header2_record += bank_code.ljust(11, '0')
                else:
                    header2_record += bank_code[0:11].ljust(11)
                header2_record += ('%34d' % context.get(
                                                'account_number')).ljust(34)
                header2_record += ''.ljust(3)
                if context.get('on_behalf_of'):
                    header2_record += ('%20s' % context.get(
                                                    'on_behalf_of')).ljust(20)
                else:
                    header2_record += "".ljust(20)
                header2_record += ''.ljust(120)
                header2_record += ''.ljust(4)
                header2_record += ('%4s' % context.get('clearing')).ljust(4)
                if context.get('reference_no'):
                    header2_record += ('%16s' % context.get(
                                                    'reference_no')).ljust(16)
                else:
                    header2_record += "".ljust(16)
                if context.get('value_date'):
                    header2_record += context.get("value_date"
                                                  ).strftime('%Y%m%d').ljust(8)
                else:
                    header2_record += "".ljust(8)
                header2_record += ('%4d' % context.get('value_time')).ljust(4)
                header2_record += ''.ljust(1)
                header2_record += ''.ljust(762)
            header2_record += '\r\n'
            tmp_file.write(header2_record)
            emp_ids = self.env['hr.employee'].search([
                                        ('bank_account_id', '!=', False)],
                                        order="name")
            serial_number = 50000
            payment_detail = ''
            for employee in emp_ids:
                if not employee.bank_account_id:
                    raise ValidationError(
                        _("There is no Bank Account define for %s "
                          "employee." % (employee.name)))
#                if not employee.identification_id:
#                    raise ValidationError(_('There is no identification no define for %s employee.' % (employee.name)))
#                if not employee.work_phone or not employee.work_email:
#                    raise ValidationError(_('You must be configure Contact no or email for %s employee.' % (employee.name)))
                payslip_id = self.env['hr.payslip'].search([
                    ('employee_id', '=', employee.id),
                    ('pay_by_cheque', '=', False),
                    ('date_from', '>=', start_date),
                    ('date_to', '<=', end_date),
                    ('state', 'in', ['draft', 'done', 'verify'])])
                if not payslip_id:
                    raise ValidationError(
                        _("There is no payslip during %s to %s to the %s "
                          "employee." % (start_date, end_date, employee.name)))
                bank_code = employee.bank_account_id and \
                    employee.bank_account_id.bank_bic or ''
                if len(bank_code) == 8:
                    payment_detail += bank_code.rjust(11, 'X')
                else:
                    payment_detail += bank_code[0:11].ljust(11)
#                emp_branch_code = employee.bank_account_id and employee.bank_account_id.branch_id or ''
#                if emp_branch_code.__len__() <= 3:
#                    payment_detail += emp_branch_code.rjust(3, '0')
#                else:
#                    payment_detail += emp_branch_code[0:3].ljust(3)
                emp_bank_ac_no = employee.bank_account_id and \
                    employee.bank_account_id.acc_number or ''
                if emp_bank_ac_no.__len__() <= 34:
                    payment_detail += emp_bank_ac_no.ljust(34, ' ')
                else:
                    payment_detail += emp_bank_ac_no[0:34].ljust(34)
#                emp_bank_ac_no = employee.bank_account_id and employee.bank_account_id.acc_number or ''
#                if emp_bank_ac_no.__len__() <= 11:
#                    payment_detail += emp_bank_ac_no.ljust(11, ' ')
#                else:
#                    payment_detail += emp_bank_ac_no[0:11].ljust(11)
#                emp_bank_name = employee.bank_account_id and employee.bank_account_id.owner_name or ''
#                if emp_bank_name:
#                    if emp_bank_name.__len__() <= 20:
#                        payment_detail += emp_bank_name.ljust(20)
#                    else:
#                        payment_detail += emp_bank_name[0:20].ljust(20)
#                else:
#                    if employee.name.__len__() <= 20:
#                        payment_detail += employee.name.ljust(20)
#                    else:
#                        payment_detail += employee.name[0:20].ljust(20)
                emp_bank_name = employee.bank_account_id and \
                    employee.bank_account_id.partner_id.name or ''
                if context.get('clearing') == 'giro':
                    if emp_bank_name:
                        if emp_bank_name.__len__() <= 140:
                            payment_detail += emp_bank_name.ljust(140)
                        else:
                            payment_detail += emp_bank_name[0:140].ljust(140)
                    else:
                        if employee.name.__len__() <= 140:
                            payment_detail += employee.name.ljust(140)
                        else:
                            payment_detail += employee.name[0:140].ljust(140)
                    payment_detail += ''.ljust(3)
                else:
                    if emp_bank_name:
                        if emp_bank_name.__len__() <= 35:
                            payment_detail += emp_bank_name.ljust(140)
                        else:
                            payment_detail += emp_bank_name[0:35].ljust(140) 
                    else:
                        if employee.name.__len__() <= 35:
                            payment_detail += employee.name.ljust(140)
                        else:
                            payment_detail += employee.name[0:35].ljust(140)\
                                                             +''.ljust(3)
                total_amout = 0
                for line in self.env['hr.payslip'].browse(
                                                payslip_id.ids[0]).line_ids:
                    if line.code == "NET":
                        total_amout = line.amount
                if total_amout:
                    total_amout = total_amout * 100
                    total_amout = int(round(total_amout))
                    payment_detail += ('%017d' % total_amout).ljust(17)
                else:
                    payment_detail += ('%017d' % 0).ljust(17)
                if context.get('payment_detail'):
                    payment_detail += ('%35s' % context.get(
                                                'payment_detail')).ljust(35)
                else:
                    payment_detail += "".ljust(35)
                if context.get('purpose_code'):
                    payment_detail += ('%04s' % context.get(
                                                    'purpose_code')).ljust(4)
                else:
                    payment_detail += "".ljust(4)
                if context.get('purpose_code') == 'COLL':
                    payment_detail += ('%35s' % context.get(
                                                'debtors_reference')).rjust(35)
                else:
                    payment_detail += ''.rjust(35)
                payment_detail += "".ljust(140)
                payment_detail += "".ljust(140)
                if context.get('invoice_send'):
                    payment_detail += ('%01s' % context.get(
                                                    'invoice_send')).ljust(1)
                else:
                    payment_detail += "".ljust(1)
                if context.get('invoice_send_numebr'):
                    payment_detail += ('%255s' % context.get(
                                            'invoice_send_numebr')).ljust(255)
                else:
                    payment_detail += "".ljust(255)
                payment_detail += "".ljust(185)
                payment_detail += '\r\n'
                serial_number += 1
            tmp_file.write(payment_detail)
            invoice_detail = ''
            if context.get('record_type'):
                invoice_detail += ('%03s' % context.get(
                                                'record_type')[0:3]).ljust(3)
            else:
                invoice_detail += "".ljust(3)
            if context.get('invoice_detail'):
                invoice_detail += ('%97s' % context.get(
                                                'invoice_detail')).ljust(97)
            else:
                invoice_detail += "".ljust(97)
            invoice_detail += '\r\n'
            tmp_file.write(invoice_detail)
        finally:
            tmp_file.close()
        fileocbc = open(tgz_tmp_filename, "rb")
        out = fileocbc.read()
        fileocbc.close()
        res = base64.b64encode(out)
        if not end_date:
            return 'ocbc_txt_file.txt'
        monthyear = end_date.strftime('%b%Y')
        file_name = 'ocbc_txt_file_' + monthyear + '.txt'
        module_rec = self.env['binary.ocbc.bank.file.wizard'].create({
            'name': file_name, 'cpf_txt_file': res})
        return{
            'name': _('OCBC Text file'),
            'res_id': module_rec.id,
            "view_mode": 'form',
            'res_model': 'binary.ocbc.bank.file.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
