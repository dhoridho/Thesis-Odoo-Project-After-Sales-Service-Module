# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime,timedelta
import pytz
import xlwt
import base64
from io import BytesIO
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import tools

class CustCreditLimitData(models.Model):
    _name = 'cust.credit.limit.data'
    _description = "Cust Credit Limit Data"

    company_id = fields.Many2one('res.company')
    branch_id = fields.Many2one('res.branch')
    partner_id = fields.Many2one('res.partner', string='Customer')
    cust_credit_line = fields.One2many('cust.credit.limit.data.line', 'cust_credit_id')

    def get_date(self):
        return datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

class CustCreditLimitDataLine(models.Model):
    _name = 'cust.credit.limit.data.line'
    _description = "Cust Credit Limit Data Line"

    cust_credit_id = fields.Many2one('cust.credit.limit.data')
    partner_id = fields.Many2one('res.partner')
    cust_credit_limit = fields.Float('Customer Credit Limit')
    customer_credit_limit = fields.Float('Customer Available Credit Limit')
    balance_due = fields.Float('Balance Due')
    aval_credit = fields.Float('Aval credit (%)')


class CustCreditLimitExcel(models.Model):
    _name = "cust.credit.limit.xls"
    _description = "Customer Credit Limit XLS"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=cust.credit.limit.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }

class CustCreditLimitReportWizard(models.TransientModel):
    _name = "cust.credit.limit.report.wizard"
    _description = "Customer Credit Limit Wizard"

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return


   

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    partner_ids = fields.Many2many('res.partner', string='Customer')
    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)
    branch_id = fields.Many2one('res.branch', required=True, domain=_domain_branch, string="Branch")

    def print_report(self):
        domain = [('customer_rank', '>=', 1)]
        if self.partner_ids:
            domain.append(('id', 'in', self.partner_ids.ids))

        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))

        if self.branch_id:
            domain.append(('branch_id', '=', self.branch_id.id))

        partners = self.env['res.partner'].sudo().search(domain)

        cust_credit_data = self.env['cust.credit.limit.data']
        cust_credit_data_line = self.env['cust.credit.limit.data.line']
        list_id = []
        list_line_id = []
        balance_due = 0
        aval_credit = 0
        if partners:
            for partner in partners:
                rec1 = cust_credit_data.search([('company_id', '=', partner.company_id.id),('branch_id', '=', partner.branch_id.id),('id', 'in', list_id)], limit=1)
                if not rec1:
                    cust_credit = cust_credit_data.create({
                        'partner_id': partner.id,
                        'company_id': partner.company_id.id or self.env.user.company_id.id,
                        'branch_id': partner.branch_id.id
                    })
                    list_id.append(cust_credit.id)
                    balance_due = partner.cust_credit_limit - partner.customer_credit_limit
                    if partner.customer_credit_limit:
                        if partner.cust_credit_limit:
                            aval_credit = balance_due / partner.cust_credit_limit * 100
                        else:
                            aval_credit = 0
                    line = cust_credit_data_line.create({
                        'cust_credit_id': cust_credit.id,
                        'partner_id': partner.id,
                        'cust_credit_limit': partner.cust_credit_limit,
                        'customer_credit_limit': partner.customer_credit_limit,
                        'balance_due': balance_due,
                        'aval_credit': round(aval_credit,2),
                    })
                    list_line_id.append(line.id)
                else:
                    balance_due = partner.cust_credit_limit - partner.customer_credit_limit
                    if partner.customer_credit_limit:
                        if partner.cust_credit_limit:
                            aval_credit = balance_due / partner.cust_credit_limit * 100
                        else:
                            aval_credit = 0
                    line = cust_credit_data_line.create({
                        'cust_credit_id': rec1.id,
                        'partner_id': partner.id,
                        'cust_credit_limit': partner.cust_credit_limit,
                        'customer_credit_limit': partner.customer_credit_limit,
                        'balance_due': balance_due,
                        'aval_credit': round(aval_credit,2),
                    })
                    list_line_id.append(line.id)

        else:
            raise ValidationError(_('There is no customer based on your request.'))
        credit = cust_credit_data.browse(list_id)
        if credit:
            return self.env.ref('equip3_sale_other_operation.cust_credit_report_action').report_action(credit)

    def print_credit_limit_xls_report(self,):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:height 225,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        b1 = xlwt.easyxf('font:bold True;align: horiz left')
        b12 = xlwt.easyxf('font:bold True;align: horiz left;borders: left thin, right thin, top thin, bottom thin')
        bold_right = xlwt.easyxf('align: horiz right')
        center = xlwt.easyxf('font:bold True;align: horiz center;pattern: pattern solid, fore_colour gray25;borders: left thin, right thin, top thin, bottom thin')
        right = xlwt.easyxf('align: horiz right')
        left = xlwt.easyxf('align: horiz left;borders: left thin, right thin, top thin, bottom thin')
        right_border = xlwt.easyxf('align: horiz right;borders: left thin, right thin, top thin, bottom thin')
        center_border = left = xlwt.easyxf('align: horiz center;borders: left thin, right thin, top thin, bottom thin')

        domain = [('customer_rank', '>=', 1)]
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        if self.branch_id:
            domain.append(('branch_id', '=', self.branch_id.id))
        if self.partner_ids:
            domain.append(('id', 'in', self.partner_ids.ids))

        partners = self.env['res.partner'].sudo().search(domain)
        if partners:
            cust_credit_data = self.env['cust.credit.limit.data']
        else:
            raise ValidationError(_('There is no customer based on your request.'))
        cust_credit_data_line = self.env['cust.credit.limit.data.line']
        list_id = []
        list_line_id = []
        balance_due = 0
        aval_credit = 0
        credits = []
        if partners:
            for partner in partners:
                rec1 = cust_credit_data.search([('company_id', '=', partner.company_id.id),('branch_id', '=', partner.branch_id.id),('id', 'in', list_id)], limit=1)
                if not rec1:
                    cust_credit = cust_credit_data.create({
                        'partner_id': partner.id,
                        'company_id': partner.company_id.id or self.env.user.company_id.id,
                        'branch_id': partner.branch_id.id
                    })
                    list_id.append(cust_credit.id)
                    balance_due = partner.cust_credit_limit - partner.customer_credit_limit
                    if partner.customer_credit_limit:
                        if partner.cust_credit_limit:
                            aval_credit = balance_due / partner.cust_credit_limit * 100
                        else:
                            aval_credit = 0
                    line = cust_credit_data_line.create({
                        'cust_credit_id': cust_credit.id,
                        'partner_id': partner.id,
                        'cust_credit_limit': partner.cust_credit_limit,
                        'customer_credit_limit': partner.customer_credit_limit,
                        'balance_due': balance_due,
                        'aval_credit': aval_credit,
                    })
                    list_line_id.append(line.id)
                else:
                    balance_due = partner.cust_credit_limit - partner.customer_credit_limit
                    if partner.customer_credit_limit:
                        if partner.cust_credit_limit:
                            aval_credit = balance_due / partner.cust_credit_limit * 100
                        else:
                            aval_credit = 0
                    line = cust_credit_data_line.create({
                        'cust_credit_id': rec1.id,
                        'partner_id': partner.id,
                        'cust_credit_limit': partner.cust_credit_limit,
                        'customer_credit_limit': partner.customer_credit_limit,
                        'balance_due': balance_due,
                        'aval_credit': aval_credit,
                    })
                    list_line_id.append(line.id)

                credits = cust_credit_data.browse(list_id)
        if credits:
            for credit in credits:
                user_currency = self.env.company.currency_id
                worksheet = workbook.add_sheet(u'Customer Credit Analysis', cell_overwrite_ok=True)
                worksheet.write_merge(0, 0, 0, 5, "Customer Credit Limit Report", heading_format)
                user_tz = self.env.user.tz or pytz.utc
                local = pytz.timezone(user_tz)



                worksheet.write(5, 0, "Printed On:", b1)
                worksheet.write(6, 0, "Company:", b1)
                worksheet.write(7, 0, "Branch:", b1)

                worksheet.write(5, 1, fields.Date.to_string(datetime.today()), b1)
                worksheet.write(6, 1, credit.company_id.name, b1)
                worksheet.write(7, 1, credit.branch_id.name, b1)

                worksheet.col(0).width = int(25 * 200)
                worksheet.col(1).width = int(25 * 260)
                worksheet.col(2).width = int(25 * 260)
                worksheet.col(3).width = int(25 * 260)
                worksheet.col(4).width = int(25 * 260)
                worksheet.col(5).width = int(25 * 260)

                worksheet.write(12, 0, "No.", center)
                worksheet.write(12, 1, "Customer", center)
                worksheet.write(12, 2, "Credit Limit", center)
                worksheet.write(12, 3, "Balance Due", center)
                worksheet.write(12, 4, "% of Credit Used", center)
                worksheet.write(12, 5, "Aval Credit limit", center)
                row = 13
                i = 1
                for rec in credit.cust_credit_line:

                    worksheet.write(row, 0, i, center_border)
                    worksheet.write(row, 1, rec.partner_id.name, left)
                    worksheet.write(row, 2, "{:0,.2f}".format(rec.cust_credit_limit), right_border)
                    worksheet.write(row, 3, "{:0,.2f}".format(rec.balance_due), right_border)
                    worksheet.write(row, 4, "{:0,.2f}".format(rec.aval_credit) + "%", right_border)
                    worksheet.write(row, 5, "{:0,.2f}".format(rec.customer_credit_limit), right_border)
                    row += 1
                    i += 1

                filename = ('Customer Credit Limit Xls Report' + '.xls')
                fp = BytesIO()
                workbook.save(fp)

                export_id = self.env['cust.credit.limit.xls'].sudo().create({
                    'excel_file': base64.encodestring(fp.getvalue()),
                    'file_name': filename,
                })

                return{
                    'type': 'ir.actions.act_window',
                    'name': 'Customer Credit Limit Analysis',
                    'res_id': export_id.id,
                    'res_model': 'cust.credit.limit.xls',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }
