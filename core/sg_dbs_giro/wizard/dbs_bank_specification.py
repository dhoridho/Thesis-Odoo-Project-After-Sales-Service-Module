import time
import base64
import tempfile
from odoo.tools.misc import get_lang
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BinaryDbsBankFileWizard(models.TransientModel):
    _name = 'binary.dbs.bank.file.wizard'
    _description = "DBS Bank Text Wizard"

    @api.model
    def _get_file_name(self):
        context = dict(self._context) or {}
        start_date = context.get('start_date', False) or False
        end_date = context.get('end_date', False) or False
        if not start_date and end_date:
            return 'dbs_txt_file.txt'
        monthyear = end_date.strftime('%b%Y')
        file_name = 'dbs_txt_file_' + monthyear + '.txt'
        return file_name

    name = fields.Char('Name', default='_get_file_name')
    cpf_txt_file = fields.Binary(
         'Click On Download Link To Download Text File', readonly=True)

    def get_wiz_action(self):
        context = self.env.context
        return {
              'name': 'DBS Text File',
              "view_mode": 'form',
              'res_model': 'dbs.bank.specification',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': context
        }


class DbsBankSpecification(models.TransientModel):
    _name = 'dbs.bank.specification'
    _description = "Dbs Bank Specification"

    batch_ref = fields.Char('Batch Reference', required=True)
    batch_number = fields.Integer('Batch Number', required=True)
    account_number = fields.Char('Account Number', required=True)
    originator_name = fields.Char(
        "Originator's Name", required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    value_date = fields.Date(
        "Value Date", required=True, default=time.strftime('%Y-%m-%d'))
    sender_comp_id = fields.Char(
        "Sender's Company ID", required=True)
    payment_type = fields.Selection([
        ('20', 'Payments'),
        ('22', 'Salary'),
        ('30', 'Collection')], 'Payment Type', required=True)
    product_type = fields.Selection([
        ('ACT', 'Account Transfer'),
        ('ICT', 'Intra Company Transfer'),
        ('TT', 'Telegraphic Transfer'),
        ('MEP', 'MEPS Payment'),
        ('CTS', 'CHATS Payment'),
        ('TTC', 'CNAPS Payment'),
        ('FIS', 'FISC Payment'),
        ('RTS', 'RTGS Payment'),
        ('LVT', 'GIRO / AutoPay / NEFT / SKN Payment'),
        ('BPY', 'Bulk Payment'),
        ('SGE', 'Bulk Payment DBS'),
        ('COL', 'Bulk Collection'),
        ('SCE', 'Bulk Collection DBS'),
        ('SAL', 'Payroll'),
        ('SPE', 'Payroll DBS'),
        ('SL2', 'Payroll - 02'),
        ('SE2', 'Payroll DBS - 02'),
        ('MP', 'Management Payroll'),
        ('MPE', 'Management Payroll DBS'),
        ('MP2', 'Management Payroll - 02'),
        ('ME2', 'Management Payroll DBS - 02'),
        ('BCH', 'Cheque Express'),
        ('CCH', 'Corporate Cheque'),
        ('GPP', 'FAST Payment'),
        ('GPC', 'FAST Collection'),
        ('GOP', 'Express Bulk Payment'),
        ('GOC', 'Express Bulk Collection'),
        ('DD', 'Demand Drafts')])
    payment_date = fields.Date("Payment Date", required=True)
    bank_charges = fields.Selection([
        ('OUR', 'Applicant pay all charges'),
        ('BEN', 'Beneficiary pay all charges'),
        ('SHA',
         'Applicant pay DBS Bank charges,Beneficiary pay Agent Bank charges')
        ])
    transaction_code = fields.Selection([
        ('20', 'Sundry Credit'),
        ('21', 'Standing Instruction Credit (SG)'),
        ('22', 'Salary Credit'),
        ('23', 'Dividend Credit (SG)'),
        ('24', 'Inward Remittance Credit (SG)'),
        ('25', 'Bill Proceeds Credit (SG)'),
        ('30', 'Direct Debit (SG & HK)')])
    delivery_mode = fields.Selection([
        ('P', 'by Email'), ('Q', 'by Fax')], 'Delivery Mode')

    @api.constrains('end_date')
    def validation_date(self):
        if self.start_date >= self.end_date:
            raise ValidationError(
            _("You must enter start date less than end date."))

    def get_text_file(self):
        context = dict(self._context) or {}
        bank_data = {}
        data = self.read([])
        if self.start_date >= self.end_date:
            raise ValidationError(
                _("You must enter start date less than end date."))
        if data:
            bank_data = data[0]
        if bank_data and bank_data.get('batch_number') and \
                len(str(bank_data.get('batch_number'))) > 5:
            raise ValidationError(_("Batch number length must be less than or "
                                    "equal to five digits."))
        context.update({'account_number': bank_data.get("account_number"),
                        'start_date': bank_data.get("start_date", False),
                        'end_date': bank_data.get("end_date", False),
                        'value_date': bank_data.get("value_date"),
                        'batch_number': bank_data.get("batch_number"),
                        'originator_name': bank_data.get('originator_name'),
                        'payment_type': bank_data.get('payment_type', ''),
                        'sender_comp_id': bank_data.get('sender_comp_id'),
                        'batch_ref': bank_data.get('batch_ref', ''),
                        'product_type': bank_data.get('product_type'),
                        'payment_date': bank_data.get('payment_date'),
                        'bank_charges': bank_data.get('bank_charges'),
                        'transaction_code': bank_data.get('transaction_code'),
                        'delivery_mode': bank_data.get('delivery_mode')})
        tgz_tmp_filename = tempfile.mktemp('.' + "txt")
        tmp_file = open(tgz_tmp_filename, "w")
        try:
            start_date = context.get('start_date', False) or False
            end_date = context.get('end_date', False)
            payslip_obj = self.env['hr.payslip']
            if not start_date and end_date:
                return False
            header2_record = ''
            batch_number = context.get('batch_number')
            if batch_number > 89999:
                raise ValidationError(
                    _("Batch Number must be between 00001 to 89999."))
            """ First 6 digit for HEADER """
            header2_record += 'HEADER'.ljust(6)
            """
            First 8 digit for date &time and 14 space in
            header(Creation Date & Time)
            """
            header2_record += time.strftime('%d%m%Y').ljust(8)
            """ Sender's Company ID in header"""
            header2_record += context.get('sender_comp_ids', '').ljust(12)
            """Originator’s Name"""
            header2_record += context.get('originator_name').ljust(35)
            header2_record += '\r\n'
            tmp_file.write(header2_record)

            emp_rec = self.env["hr.employee"].search([
                ('bank_account_id', '!=', False)], order="name")
            if emp_rec and emp_rec.ids:
                payslip_count = payslip_obj.search_count([
                    ('employee_id', 'in', emp_rec.ids),
                    ('date_from', '>=', start_date),
                    ('date_to', '<=', end_date),
                    ('state', '=', 'done')
                ])
                if payslip_count == 0:
                        raise ValidationError(
                            _("There is no single payslip details found "
                              "between selected date %s and %s"
                              ) % (
                                start_date.strftime(
                                    get_lang(self.env).date_format),
                                end_date.strftime(
                                    get_lang(self.env).date_format)))
            for employee in emp_rec:
                payslip_ids = payslip_obj.search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '>=', start_date),
                    ('date_to', '<=', end_date),
                    ('state', '=', 'done')
                ])
                payslip_ref = ''
                for payslip in payslip_ids:
                    payment_detail = ''
                    payslip_ref = payslip.number
                    """ Details of Record """
                    """ Record Type """
                    payment_detail += 'PAYMENT'.ljust(7)
                    """ Product Type """
                    if not context.get('product_type'):
                        context['product_type'] = 'SAL'
                    payment_detail += context.get('product_type').ljust(3)
                    """ Originating Account Number """
                    payment_detail += context.get('account_number').ljust(
                        35)
                    """ Originating Account Currency """
                    payment_detail += 'SGD'.ljust(3)
                    """ Customer Reference or Batch Reference """
                    payment_detail += context.get('batch_ref', '').ljust(
                        35)
                    """ Payment Currency """
                    payment_detail += 'SGD'.ljust(3)
                    """ Batch ID """
                    payment_detail += str(batch_number).ljust(5)
                    """ Payment Date """
                    payment_detail += context.get("payment_date"
                                                  ).strftime('%d%m%Y'
                                                             ).ljust(8)
                    """ Bank Charges """
                    if not context.get('bank_charges'):
                        context['bank_charges'] = 'OUR'
                    payment_detail += context.get('bank_charges').ljust(3)
                    """ Debit Account for Bank Charges """
                    payment_detail += context.get('account_number').ljust(
                        35)
                    """ Receiving Party Name """
                    bnk_acc_id = payslip.employee_id.bank_account_id
                    recv_party_name = (bnk_acc_id and
                                       bnk_acc_id.acc_holder_name or '')
                    payment_detail += recv_party_name.ljust(35)
                    """ Payable To """
                    payment_detail += ' '.ljust(35)
                    """ Receiving Party Address 1 """
                    payment_detail += ' '.ljust(35)
                    """ Receiving Party Address 2 """
                    payment_detail += ' '.ljust(35)
                    """ Receiving Party Address 3 """
                    payment_detail += ' '.ljust(35)
                    """ Receiving Account Number / IBAN """
                    rcv_acc_number = bnk_acc_id and bnk_acc_id.acc_number
                    payment_detail += rcv_acc_number.ljust(34)
                    """ Country Specific """
                    payment_detail += ' '.ljust(2)
                    """ Receiving Bank Code """
                    payment_detail += ' '.ljust(4)
                    """ Receiving Branch Code """
                    payment_detail += ' '.ljust(4)
                    """ Clearing Code """
                    payment_detail += ' '.ljust(12)
                    """ Beneficiary Bank SWIFT BIC """
                    payment_detail += context.get('product_type').ljust(11)
                    """ Beneficiary Bank Name """
                    payment_detail += ' '.ljust(35)
                    """ Beneficiary Bank Address """
                    payment_detail += ' '.ljust(70)
                    """ Beneficiary Bank Country """
                    payment_detail += 'SG'.ljust(2)
                    """ Routing Code """
                    payment_detail += ' '.ljust(31)
                    """ Intermediary Bank SWIFT BIC """
                    payment_detail += ' '.ljust(11)
                    """ Amount Currency """
                    payment_detail += ' '.ljust(1)
                    """ Amount """
                    """ FX Contract Reference 1 """
                    payment_detail += ' '.ljust(50)
                    """ Amount to be Utilized 1 """
                    payment_detail += ' '.ljust(11)
                    """ FX Contract Reference 2 """
                    payment_detail += ' '.ljust(50)
                    """ Amount to be Utilized 2 """
                    payment_detail += ' '.ljust(11)
                    """ Transaction Code """
                    if not context.get('transaction_code'):
                        context['transaction_code'] = '22'
                    payment_detail += context.get('transaction_code'
                                                  ).ljust(2)
                    """ Particulars / Beneficary or Payer Reference (aka \
                    End to End Reference) """
                    payment_detail += ' '.ljust(35)
                    """ detail of payment """
                    payment_detail += payslip_ref.ljust(140)
                    """ Instruction to Ordering Bank """
                    payment_detail += ' '.ljust(128)
                    """ Beneficiary Resident Status """
                    payment_detail += ' '.ljust(1)
                    """ Beneficiary Category """
                    payment_detail += ' '.ljust(2)
                    """ Transaction Relationship """
                    payment_detail += ' '.ljust(1)
                    """ Payee Role """
                    payment_detail += ' '.ljust(1)
                    """ Remitter Identity """
                    payment_detail += ' '.ljust(2)
                    """ Purpose of Payment """
                    payment_detail += ' '.ljust(4)
                    """ Supplementary Info """
                    payment_detail += ' '.ljust(35)
                    """ Delivery Mode """
                    if not context.get('delivery_mode'):
                        context['delivery_mode'] = 'P'
                    payment_detail += context.get('delivery_mode')
                    """ Print At Location/Pick Up Location """
                    payment_detail += ' '.ljust(16)
                    """ Payable Location """
                    payment_detail += ' '.ljust(16)
                    """ Mail to Party Name """
                    payment_detail += ' '.ljust(35)
                    """ Mail to Party Address 1 """
                    payment_detail += ' '.ljust(35)
                    """ Mail to Party Address 2 """
                    payment_detail += ' '.ljust(35)
                    """ Mail to Party Address 3 """
                    payment_detail += ' '.ljust(35)
                    """ Postal Code """
                    payment_detail += ' '.ljust(8)
                    """ Email 1 """
                    email = payslip.employee_id.work_email
                    payment_detail += str(email).ljust(75)
                    """ Email 2 """
                    payment_detail += ' '.ljust(75)
                    """ Email 3 """
                    payment_detail += ' '.ljust(75)
                    """ Email 4 """
                    payment_detail += ' '.ljust(75)
                    """ Email 5 """
                    payment_detail += ' '.ljust(75)
                    """ Phone Number 1 """
                    phone_detail = payslip.employee_id.mobile_phone or\
                        ''
                    payment_detail += phone_detail.ljust(35)
                    """ Phone Number 2 """
                    payment_detail += ' '.ljust(35)
                    """ Phone Number 3 """
                    payment_detail += ' '.ljust(35)
                    """ Phone Number 4 """
                    payment_detail += ' '.ljust(35)
                    """ Phone Number 5 """
                    payment_detail += ' '.ljust(35)
                    """ Invoice Details """
                    payment_detail += ' '.ljust(70000)
                    """ Client Reference 1 """
                    payment_detail += ' '.ljust(40)
                    """ Client Reference 2 """
                    payment_detail += ' '.ljust(40)
                    """ Client Reference 3 """
                    payment_detail += ' '.ljust(40)
                    """ Client Reference 4 """
                    payment_detail += ' '.ljust(40)
                    payment_detail += '\r\n'
                    tmp_file.write(payment_detail)
            """ Trailer Record """
            trailer_details = ''
            """ Record Type """
            trailer_details += 'TRAILER'
            """ Total No. of Transactions """
            trailer_details += ' '.ljust(8)
            """ Total Transaction Amount """
            trailer_details += ' '.ljust(20)
            trailer_details += '\r\n'
            tmp_file.write(trailer_details)
            batch_number += 1
        finally:
            tmp_file.close()
        file_rec = open(tgz_tmp_filename, "rb")
        out = file_rec.read()
        file_rec.close()
        res_base = base64.b64encode(out)
        binary_dbs_txt_obj = self.env['binary.dbs.bank.file.wizard']
        file_name = binary_dbs_txt_obj.with_context(context)._get_file_name()
        dbs_rec = binary_dbs_txt_obj.create({'name': file_name,
                                             'cpf_txt_file': res_base})
        return {
            'name': _('Text file'),
            'res_id': dbs_rec.id,
            "view_mode": 'form',
            'res_model': 'binary.dbs.bank.file.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
