import time
import base64
import tempfile
from odoo import tools
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class CimbBankTextFile(models.TransientModel):
    _name = 'cimb.bank.text.file'
    _description = "Cimb Bank Text File"

    source_account_number = fields.Integer('Source Account Number')
    account_name = fields.Char('Account Name')
    remark = fields.Char('Remark')
    transaction_date = fields.Date('Transaction Date')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-01-01'))
    end_date = fields.Date('End Date', default=time.strftime('%Y-12-31'))

    def download_cimb_bank_txt_file(self):
        '''
            The method used to call download file of wizard
            @self : Record Set
            @return: Return of wizard of action in dictionary
            -------------------------------------------------------------------
        '''
        context = dict(self.env.context or {})
        cimb_bnk_data = self.read([])
        data = {}
        if cimb_bnk_data:
            data = cimb_bnk_data[0]
        start_date = data.get('start_date', False)
        end_date = data.get('end_date', False)
        if start_date >= end_date:
            raise ValidationError(_("You must be enter start date less than "
                                    "end date !"))
        context.update({'datas': data})
        emp_ids = self.env['hr.employee'].search([('bank_account_id', '!=',
                                                   False)], order='name')
        payslip_ids = self.env['hr.payslip'].search([
            ('employee_id', 'in', emp_ids.ids),
            ('cheque_number', '=', False),
            ('date_from', '>=', start_date),
            ('date_from', '<=', end_date),
            ('state', 'in', ['draft', 'done', 'verify'])
        ], order="employee_name")
        if not payslip_ids:
            raise ValidationError(_('There is no payslip found to generate '
                                    'text file.'))
#        here maked temporary csv file for pay
        tgz_tmp_filename = tempfile.mktemp('.' + "txt")
        tmp_file = False
        try:
            tmp_file = open(tgz_tmp_filename, "w")
            net_amount_total = 0.0
            detail_record = ''
            for payslip in payslip_ids:
                if not payslip.employee_id.bank_account_id:
                    raise ValidationError(_('There is no bank detail found '
                                            'for %s .' % (
                                                payslip.employee_id.name)))
                bank_list = []
                if not payslip.employee_id.bank_account_id.acc_number:
                    bank_list.append('Bank Account Number')
                if not payslip.employee_id.bank_account_id.branch_id:
                    bank_list.append('Branch Code')
                if not payslip.employee_id.bank_account_id.bank_bic:
                    bank_list.append('Bank Code')
                remaing_bank_detail = ''
                if bank_list:
                    for bank in bank_list:
                        remaing_bank_detail += tools.ustr(bank) + ', '
                    raise ValidationError(_('%s not found For %s '
                                            'Employee.' % (
                                                remaing_bank_detail,
                                                payslip.employee_id.name)))
                net_amount = 0.0
                for line in payslip.line_ids:
                    if line.code == 'NET':
                        net_amount = line.total
                        net_amount_total += line.total
                net_amount = '%.2f' % net_amount
                acc_num = payslip.employee_id.bank_account_id.acc_number
                bank_bic = payslip.employee_id.bank_account_id.bank_bic
                branch_id = payslip.employee_id.bank_account_id.branch_id
                detail_record += tools.ustr(acc_num)[:40] + \
                            ',' + tools.ustr(payslip.employee_id.name)[:100] + \
                            ',SGD'.ljust(4) + \
                            ',' + tools.ustr(net_amount)[:17] + \
                            ',' + tools.ustr(context.get('datas')['remark'] \
                                             or '')[:80] + \
                            ',' + tools.ustr(bank_bic)[:40] + \
                            ',' + tools.ustr(branch_id)[:40] + \
                            ',N'.ljust(2) + \
                            ''[:100] + "\r\n"
            net_amount_total = '%.2f' % net_amount_total
            transactiondate = context.get('datas')['transaction_date']
            transactiondate = transactiondate.strftime('%Y%m%d')
            source_acc_num = context.get('datas')['source_account_number']
            acc_name = context.get('datas')['account_name']
            header_record = tools.ustr(source_acc_num)[:40] + \
                            ',' + tools.ustr(acc_name or '')[:100] + \
                            ',SGD'.ljust(4) + \
                            ',' + tools.ustr(net_amount_total)[:17] + \
                            ',' + tools.ustr(context.get('datas')['remark'] or \
                                             '')[:80] + \
                            ',' + tools.ustr(len(payslip_ids))[:5] + \
                            ',' + tools.ustr(transactiondate or \
                                             '')[:8] + "\r\n"
            tmp_file.write(header_record)
            tmp_file.write(detail_record)
        finally:
            if tmp_file:
                tmp_file.close()
        file = open(tgz_tmp_filename, "rb")
        out = file.read()
        file.close()
        res = base64.b64encode(out)
        text_file_obj = self.env['binary.cimb.bank.text.file.wizard']
        module_rec = text_file_obj.create({'name': 'CIMB_Bank.txt',
                                           'cimb_bank_txt_file': res})
        return {
            'name': _('CIMB Bank File'),
            'res_id': module_rec.id,
            "view_mode": 'form',
            'res_model': 'binary.cimb.bank.text.file.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }


class BinaryCimbBankTextFileWizard(models.TransientModel):
    _name = 'binary.cimb.bank.text.file.wizard'
    _description = "Cimb Bank Text Wizard"

    name = fields.Char('Name', default='CIMB_Bank.txt')
    cimb_bank_txt_file = fields.Binary('Click On Download Link To Download \
    File', readonly=True)
