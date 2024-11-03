# -*- coding: utf-8 -*-
import xlsxwriter
import tempfile
import binascii
import base64
import xlrd

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    pos_validate_file = fields.Binary(string='File')
    pos_validate_filename = fields.Char(string='Filename')
    validate_data = fields.Html(string='Validation Table', default=False)
    validated_line_ids = fields.Many2many('account.move.line', string='Validated Lines')

    
    def action_create_payments(self):

        validated_line_ids = self.mapped('validated_line_ids')
        validated_line_ids.write({
            'check_reconcile_flag': True, 
            'check_reconcile_done': True,
            'check_payment': True,
            })
        self.write({'validated_line_ids': [(5, 0, 0)]})

        res = super(AccountPaymentRegister, self).action_create_payments()

        move = self.env['account.move'].browse(self.env.context.get('active_ids'))
        if move.pos_order_id and move.is_from_pos_receivable:
            if move.payment_state == 'partial':
                move.pos_order_id.write({ 'state': 'partially paid' })
            if move.payment_state == 'paid':
                move.pos_order_id.write({ 'state': 'done' })

        return res

    def button_download_template(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(_("The Python library xlsxwriter is not installed. Please contact your system administrator"))
        file_name = 'POS Payment Validation'
        file_path = tempfile.mktemp(suffix='.xlsx')
        workbook = xlsxwriter.Workbook(file_path)
        text_format = workbook.add_format({'num_format': '@'})
        worksheet = workbook.add_worksheet(file_name)
        worksheet.set_column(0, 0, 5)
        worksheet.set_column(0, 1, 30)
        worksheet.set_column(0, 2, 30, text_format)
        worksheet.set_column(0, 3, 30)
        worksheet.write(0, 0, "SNO")
        worksheet.write(0, 1, "Approval Code", text_format)
        worksheet.write(0, 2, "Amount")
        workbook.close()
        with open(file_path, 'rb') as r:
            xls_file = base64.b64encode(r.read())
        att_vals = {
            'name': file_name + '.xlsx',
            'type': 'binary',
            'datas': xls_file,
        }
        attachment_id = self.env['ir.attachment'].create(att_vals)
        self.env.cr.commit()
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id),
            'target': 'self',
        }
        return action

    def request_for_approval(self):
        super(AccountPaymentRegister, self).request_for_approval()
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            raise ValidationError('Request For Approval->[active_ids] is None')
        
        moves = self.env[active_model].browse(active_ids)
        for move in moves:
            for line in move.invoice_line_ids:
                if line.check_reconcile_flag:
                    line.check_reconcile_done = True
                    line.check_reconcile_flag = False


        return True

    def button_validate_data(self):
        import_name_extension = self.pos_validate_filename.split('.')[1]
        if import_name_extension not in ['xls', 'xlsx']:
            raise ValidationError('The upload file is using the wrong format. Please upload your file in xlsx or xls format.')

        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.pos_validate_file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        keys = sheet.row_values(0)
        xls_reader = [sheet.row_values(i) for i in range(1, sheet.nrows)]

        data = '''
        <br/>
        <h2 class='text-center'>VALIDATION RESULT</h2>
        <br/>
        <table style="width:100%; border: 1px solid black;">
            <tr>
                <th style='border: 1px solid black; font-size: 15px;' class='text-center'>SNO</th>
                <th style='border: 1px solid black; font-size: 15px;'>POS Order Ref</th>
                <th style='border: 1px solid black; font-size: 15px;' class='text-right'>Approval Code</th>
                <th style='border: 1px solid black; font-size: 15px;' class='text-right'>Amount</th>
                <th style='border: 1px solid black; font-size: 15px;' class='text-center'>Check</th>
            </tr>
        '''
        validated_line_ids = self.env['account.move.line']
        row_count = 1
        for line in self.line_ids:
            move = line.move_id
            unreconciled_move_line_ids = move.invoice_line_ids.filtered(lambda l: not l.check_reconcile_done)
            unreconciled_move_line_ids.write({'check_reconcile_flag': False})

            valid_amount = 0.0
            check_true = '<span class="fa-solid fa fa-check text-success"/>'
            check_false = '<span class="fa-solid fa fa-close text-danger"/>'
            xls_reader_copy = xls_reader.copy()
            for row in xls_reader_copy:
                line_data = dict(zip(keys, row))
                approval_code = line_data.get('Approval Code')
                if isinstance(approval_code, (int, float)):
                    approval_code = str(int(approval_code))
                amount = line_data.get('Amount')
                line_id = self.env['account.move.line'].search([
                    ('move_id','=',move.id),
                    ('approval_code','=',approval_code),
                    ('price_total','=',amount),
                ])
                if line_id:
                    check = check_true
                    valid_amount += line_id.price_total
                    validated_line_ids |= line_id

                    data += '''
                        <tr>
                            <td style='border: 1px solid black; font-size: 15px;' class='text-center'>%s</td>
                            <td style='border: 1px solid black; font-size: 15px;'>'%s'</td>
                            <td style='border: 1px solid black; font-size: 15px;' class='text-right'>%s</td>
                            <td style='border: 1px solid black; font-size: 15px;' class='text-right'>%s</td>
                            <td style='border: 1px solid black; font-size: 18px;' class='text-center'>
                                %s
                            </td>
                        </tr>
                    ''' % (row_count, move.name, approval_code, amount, check)
                    row_count += 1
                    xls_reader.remove(row)

        for row in xls_reader:
            line_data = dict(zip(keys, row))
            approval_code = line_data.get('Approval Code')
            if isinstance(approval_code, (int, float)):
                approval_code = str(int(approval_code))
            amount = line_data.get('Amount')
            check = check_false

            data += '''
                <tr>
                    <td style='border: 1px solid black; font-size: 15px;' class='text-center'>%s</td>
                    <td style='border: 1px solid black; font-size: 15px;'>-</td>
                    <td style='border: 1px solid black; font-size: 15px;' class='text-right'>%s</td>
                    <td style='border: 1px solid black; font-size: 15px;' class='text-right'>%s</td>
                    <td style='border: 1px solid black; font-size: 18px;' class='text-center'>
                        %s
                    </td>
                </tr>
            ''' % (row_count, approval_code, amount, check)
            row_count += 1

        self.write({
                'amount': valid_amount,
                'validate_data': data,
            })
        data += '</table>'

        self.validated_line_ids = validated_line_ids

        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': self.env.context,
            'res_id': self.id,
            'target': 'new',
        }

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        ''' Extract values from the batch passed as parameter (see '_get_batches')
        to be mounted in the wizard view.
        :param batch_result:    A batch returned by '_get_batches'.
        :return:                A dictionary containing valid fields
        '''
        key_values = batch_result['key_values']
        lines = batch_result['lines']
        company = lines[0].company_id

        source_amount = 0
        if len(lines) == 1:
            if not lines.move_id.is_from_pos_partner:
                source_amount = abs(lines.amount_residual)
            if key_values['currency_id'] == company.currency_id.id:
                source_amount_currency = source_amount
            else:
                source_amount_currency = abs(sum(lines.mapped('amount_residual_currency')))
                # raise UserError(_('Currency does not match with invoice currency'))
        else:
            source_amount = abs(sum(lines.mapped('amount_residual')))
            if key_values['currency_id'] == company.currency_id.id:
                source_amount_currency = source_amount
            else:
                source_amount_currency = abs(sum(lines.mapped('amount_residual_currency')))

        return {
            'company_id': company.id,
            'partner_id': key_values['partner_id'],
            'partner_type': key_values['partner_type'],
            'payment_type': key_values['payment_type'],
            'source_currency_id': key_values['currency_id'],
            'source_amount': source_amount,
            'source_amount_currency': source_amount_currency,
        }