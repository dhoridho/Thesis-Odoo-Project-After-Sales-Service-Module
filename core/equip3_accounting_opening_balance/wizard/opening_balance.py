# -*- coding: utf-8 -*-
import base64
import io
import logging
import re
import xlwt
from odoo import api, fields, models, _
from odoo.http import content_disposition
from odoo.exceptions import UserError, ValidationError
try:
    import csv
except ImportError:
    raise UserError(_("Please install python3-csv package."))
try:
    import xlrd
except ImportError:
    raise UserError(_("Please install python3-xlrd package."))



class OpeningBalance(models.TransientModel):
    _name = "opening.balance"

    account_date = fields.Date(string='Account Date')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    journal_id = fields.Many2one('account.journal', string='Journal', domain="[('company_id', '=', company_id)]")
    partner_id = fields.Many2one('res.partner', string='Partner')
    date_id = fields.Date(string='Due Date')
    is_import = fields.Boolean(string='Import Opening Balance')
    # analytic_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Group',
    #                                       domain="[('company_id', '=', company_id)]")
    line_ids = fields.One2many('opening.balance.line', 'move_id', string='Journal Items')
    attachement_opening_balance_ids = fields.Many2many('ir.attachment', string='Attachement Opening Balance')

    @api.onchange('journal_id')
    def onchange_line_item(self):
        for rec in self:
            if rec.line_ids:
                remove = []
                for line in rec.line_ids:
                    remove.append((2, line.id))
                rec.line_ids = remove
            if rec.journal_id:
                self.coa_list(rec)

    def coa_list(self, rec):
        line_item = []
        coa_list = self.env['account.account'].sudo().search(
            [('deprecated', '=', False), ('company_id', '=', rec.company_id.id), ('is_off_balance', '=', False),
             ('internal_group', 'in', ['equity', 'asset', 'liability'])])
        for coa_rec in coa_list:
            line_item.append((0, 0, {'account_id': coa_rec}))
        rec.line_ids = line_item

    def generate_je(self):
        move_obj = self.env["account.move"]
        for je in self:
            move = {
                "journal_id": je.journal_id.id,
                "date": je.account_date,
                "company_id": je.company_id.id,
                # "analytic_group_ids": [(6, 0, je.analytic_group_ids.ids,)],

            }
            move_id = move_obj.create(move)
            je_line_item = []
            for line in je.line_ids:
                if line.debit > 0 or line.credit > 0:
                    je_line_item.append((0, 0, {
                        "debit": line.debit,
                        "credit": line.credit,
                        "account_id": line.account_id.id,
                        "date_id": line.date_id,
                        # "analytic_tag_ids": [(6, 0, line.analytic_tag_ids.ids,)],
                        "journal_id": je.journal_id.id,
                        "currency_id": line.company_currency_id.id,
                        "date": je.account_date, 
                        "date_maturity": line.date_id,
                        "partner_id": line.partner_id.id}))
                else:pass
            move_id.line_ids = je_line_item
            move_id.action_post()

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': move_id.id,
                'views': [(False, 'form')],
            }


    def import_opening_balance(self):
        for data_file in self.attachement_opening_balance_ids:
            if data_file.name.endswith('.csv'):
                file_data = base64.b64decode(data_file.datas)
                file_data = file_data.decode('utf-8')
                file_data = file_data.split('\n')
                move_obj = self.env["account.move"]
                for line in file_data:
                    line = line.split(',')
                    if line[0] == 'Account Code':
                        pass
                    else:
                        move = {
                            "journal_id": self.journal_id.id,
                            "date": self.account_date,
                            "company_id": self.company_id.id,
                            # "analytic_group_ids": [(6, 0, self.analytic_group_ids.ids,)],
                        }
                        move_id = move_obj.create(move)
                        je_line_item = []
                        ob_line_item = []
                        for line in file_data:
                            line = line.split(',')
                            if len(line) >= 4:  # Check if line contains at least 4 elements
                                if (line[0] == 'Account Code'):
                                    pass
                                else:
                                    debit = float(line[2]) if len(line) > 2 and line[2] else 0.0  # Safely access debit amount
                                    credit = float(line[3]) if len(line) > 3 and line[3] else 0.0  # Safely access credit amount
                                    account_id = self.env['account.account'].search([('code', '=', line[0])])

                                    if debit == 0.0 and credit == 0.0:
                                        pass
                                    else:
                                        je_line_item.append((0, 0, {
                                            "debit": debit,
                                            "credit": credit,
                                            "move_id": move_id.id,
                                            "account_id": account_id.id,
                                            "date_id": self.date_id,
                                            "journal_id": self.journal_id.id,
                                            "currency_id": self.company_id.currency_id.id,
                                            "date": self.account_date,
                                            "date_maturity": self.date_id,
                                            "partner_id": self.partner_id.id
                                        }))

                                        ob_line_item.append((0, 0, {
                                            "debit": debit,
                                            "credit": credit,
                                            "account_id": account_id.id,
                                            "date_id": self.date_id,
                                            "partner_id": self.partner_id.id
                                        }))
                            else:
                                # Handle incomplete or unexpected lines
                                pass
                        move_id.line_ids = je_line_item
                        move_id.action_post()

                        self.line_ids = ob_line_item

            elif data_file.name.endswith('.xls'):
                file_data = base64.b64decode(data_file.datas)
                xls_data = xlrd.open_workbook(file_contents=file_data)
                sheet = xls_data.sheet_by_index(0)
                move_obj = self.env["account.move"]  

                # Initialize debit and credit with default values before the loop
                debit = 0.0
                credit = 0.0
                vals_list = []
                for row_no in range(sheet.nrows):
                    val = {}
                    values = {}
                    if row_no <= 0:
                        fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
                    else:
                        line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                        if line[0] == 'Account Code':
                            pass
                        else:
                            debit = float(line[2]) if len(line) > 2 and line[2] else 0.0
                            credit = float(line[3]) if len(line) > 3 and line[3] else 0.0
                            account_id = self.env['account.account'].search([('code', '=', line[0])])

                            if debit == 0.0 and credit == 0.0:
                                pass
                            else:
                                values.update({
                                    "debit": debit,
                                    "credit": credit,
                                    "account_id": account_id.id,
                                    "date_id": self.date_id,
                                    "partner_id": self.partner_id.id
                                })
                                vals_list.append(values)
                move = {
                    "journal_id": self.journal_id.id,
                    "date": self.account_date,
                    "company_id": self.company_id.id,
                    # "analytic_group_ids": [(6, 0, self.analytic_group_ids.ids,)],
                }
                move_id = move_obj.create(move)
                je_line_item = []
                ob_line_item = []
                for vals in vals_list:
                    je_line_item.append((0, 0, {
                        "debit": vals['debit'],
                        "credit": vals['credit'],
                        "move_id": move_id.id,
                        "account_id": vals['account_id'],
                        "date_id": self.date_id,
                        "journal_id": self.journal_id.id,
                        "currency_id": self.company_id.currency_id.id,
                        "date": self.account_date,
                        "date_maturity": self.date_id,
                        "partner_id": self.partner_id.id
                    }))

                    ob_line_item.append((0, 0, {
                        "debit": vals['debit'],
                        "credit": vals['credit'],
                        "account_id": vals['account_id'],
                        "date_id": self.date_id,
                        "partner_id": self.partner_id.id
                    }))
                move_id.line_ids = je_line_item
                move_id.action_post()

                self.line_ids = ob_line_item

            else:
                raise UserError(_("Please upload only CSV or XLS file!"))
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': move_id.id,
                'views': [(False, 'form')],
            }

    def download_opening_balance_csv(self):
        return self.download_csv()
    
    def _generate_opening_balance_csv(self):
        header = ['Account Code', 'Account Name', 'Debit', 'Credit']
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        for line in self.line_ids:
            writer.writerow([line.account_id.code, line.account_id.name, line.debit, line.credit])
        my_utf8 = output.getvalue().encode("utf-8")
        out = base64.b64encode(my_utf8)
        attachment = self.env['ir.attachment'].create({
            'name': 'opening_balance_%s.csv' % self.account_date,
            'type': 'binary',
            'datas': out,
        })
        return attachment
    
    def download_csv(self):
        """Download CSV file."""
        attachment = self._generate_opening_balance_csv()
        action = {
            'name': _('Opening Balance'),
            'type': 'ir.actions.act_url',
            'url': "web/content/%s?download=true" % attachment.id,
            'target': 'self',
        }
        return action
    
    def _generate_oepening_balance_xls(self):
        output = io.BytesIO()
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Opening Balance')
        worksheet.write(0, 0, 'Account Code')
        worksheet.write(0, 1, 'Account Name')
        worksheet.write(0, 2, 'Debit')
        worksheet.write(0, 3, 'Credit')
        row = 1
        for line in self.line_ids:
            worksheet.write(row, 0, line.account_id.code)
            worksheet.write(row, 1, line.account_id.name)
            worksheet.write(row, 2, line.debit)
            worksheet.write(row, 3, line.credit)
            row += 1
        workbook.save(output)
        my_utf8 = output.getvalue()
        out = base64.b64encode(my_utf8)
        attachment = self.env['ir.attachment'].create({
            'name': 'opening_balance_%s.xls' % self.account_date,
            'type': 'binary',
            'datas': out,
        })
        return attachment
    
    def download_xls(self):
        """Download XLS file."""
        attachment = self._generate_oepening_balance_xls()
        action = {
            'name': _('Opening Balance'),
            'type': 'ir.actions.act_url',
            'url': "web/content/%s?download=true" % attachment.id,
            'target': 'self',
        }
        return action
    
    def download_opening_balance_xls(self):
        return self.download_xls()

        

class OpeningBalanceLine(models.TransientModel):
    _name = "opening.balance.line"
    move_id = fields.Many2one('opening.balance', string='Journal Entry')
    company_id = fields.Many2one(related='move_id.company_id', default=lambda self: self.env.company)
    account_id = fields.Many2one('account.account', string='Account',
                                 domain="[('deprecated', '=', False), ('company_id', '=', company_id),('is_off_balance', '=', False), ('internal_group', 'in', ['equity', 'asset', 'liability'])]")
    # analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group',
    #                                     related='move_id.analytic_group_ids')
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency')
    debit = fields.Monetary(string='Debit', default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', default=0.0, currency_field='company_currency_id')
    date_id = fields.Date(string='Due Date')
