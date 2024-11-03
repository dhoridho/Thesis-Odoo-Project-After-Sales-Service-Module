
from odoo import api, fields, models, _, tools
from datetime import date
# from datetime import timedelta, datetime, date
# from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError

class StudentFeesRegister(models.Model):
    _inherit = "student.fees.register"
    _order = "create_date desc"

    @api.model
    def _domainSchool(self):
        return [('id','in',self.env.user.company_id.school_ids.ids)]
    
    @api.model
    def _domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    @api.depends('company_id')
    def _getBranch(self):
        for rec in self :
            rec.branch_id = rec.company_id.branch_ids[:1]
        return True

    @api.model
    def _searchBranch(self, operator, value):
        company_ids = self.env["res.company"].search([('branch_ids',operator,value)])
        _domain = [('company_id','in',company_ids.ids)]
        return _domain

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, domain=_domain_company)
    branch_id = fields.Many2one(default=lambda self: self.env.branch.id, search=_searchBranch, comodel_name='res.branch', string='Branch')
    student_ids = fields.One2many('student.student', 'fees_register_id', string='Student')
    academic_year_id = fields.Many2one('academic.year', string='Academic Year', domain=[('current', '=', True)])
    term_id = fields.Many2one('academic.month', string='Term')


    @api.model
    def create(self, vals):
        if vals.get('number', 'New') == 'New':
            vals['number'] = self.env['ir.sequence'].next_by_code('student.fees.register') or 'New'
        return super(StudentFeesRegister, self).create(vals)
    
    def fees_register_confirm(self):
        res = super(StudentFeesRegister, self).fees_register_confirm()
        for rec in self:
            for payslip in rec.line_ids:
                lines = []
                for structure_line in rec.fees_structure.line_ids:
                    line_vals = {
                        "slip_id": payslip.id,
                        "name": structure_line.name,
                        "code": structure_line.code,
                        "type": structure_line.type,
                        "account_id": structure_line.account_id.id,
                        "amount": structure_line.amount,
                        "currency_id": structure_line.currency_id.id or False,
                        "currency_symbol": structure_line.currency_symbol or False,
                    }
                    lines.append((0, 0, line_vals))
                payslip.write({'line_ids': lines})
                amount = 0
                amount = sum(data.amount for data in payslip.line_ids)
                payslip.register_id.write({'total_amount': payslip.total})
                payslip.write({
                    'total': amount,
                    'due_amount': amount,
                    'currency_id': payslip.company_id.currency_id.id or False,
                    'year_id': rec.academic_year_id.id,
                    'term_id': rec.term_id.id,
                    'program': rec.standard_id.id
                })

        return res

    @api.onchange('standard_id')
    def get_student_ids(self):
        for fee in self:
            fee.student_ids = [(5, 0, 0)]
            if fee.standard_id:
                intake_students = fee.standard_id.intake_ids.mapped('intake_student_line_ids').mapped('student_id')
                fee.student_ids = [(6, 0, intake_students.ids)]
    
    @api.onchange('academic_year_id')
    def _onchange_year_id(self):
        for rec in self:
            domain = {'domain': {'term_id': [('checkactive', '=', True), ('year_id', '=', rec.academic_year_id.id)]}}
            return domain

class StudentPayslip(models.Model):
    _inherit = "student.payslip"
    _order = "create_date desc"

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    program = fields.Many2one("standard.standard", string="Program", readonly=True, help="Select school standard")
    tax_id = fields.Many2one('account.tax', string="Taxes")

    @api.model
    def create(self, vals):
        if vals.get('number', 'New') == 'New':
            vals['number'] = self.env['ir.sequence'].next_by_code('student.payslip') or 'New'
        return super(StudentPayslip, self).create(vals)
    
    @api.onchange('student_id')
    def onchange_student_id(self):
        month_and_year = date.today().strftime("%B %Y")
        name = "New"
        if self.student_id:
            name = self.student_id.name + ' - ' + month_and_year
        elif self.partner_id:
            name = self.partner_id.name + ' - ' + month_and_year
        self.name = name
    
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

    def monthly_payslip_confirm(self):
        """Method to confirm payslip"""
        for rec in self:
            if not rec.journal_id:
                raise ValidationError(_("Kindly, Select Account Journal!"))
            if not rec.fees_structure_id:
                raise ValidationError(_("Kindly, Select Fees Structure!"))
            lines = []
            for data in rec.fees_structure_id.line_ids.filtered(lambda r: r.type == 'term') or []:
                line_vals = {
                    "slip_id": rec.id,
                    "name": data.name,
                    "code": data.code,
                    "type": data.type,
                    "account_id": data.account_id.id,
                    "amount": data.amount,
                    "currency_id": data.currency_id.id or False,
                    "currency_symbol": data.currency_symbol or False,
                }
                lines.append((0, 0, line_vals))
            rec.write({"line_ids": lines})
            # Compute amount
            amount = 0
            amount = sum(data.amount for data in rec.line_ids)
            rec.register_id.write({"total_amount": rec.total})
            rec.write(
                {
                    "total": amount,
                    "state": "confirm",
                    "due_amount": amount,
                    # "currency_id": rec.company_id.currency_id.id or False,
                }
            )

    def invoice_view(self):
        invoice_obj = self.env["account.move"]
        for rec in self:
            invoices_rec = invoice_obj.search(
                [("student_payslip_id", "=", rec.id)]
            )
            action = rec.env.ref(
                "account.action_move_out_invoice_type"
            ).read()[0]
            if len(invoices_rec) > 1:
                action["domain"] = [("id", "in", invoices_rec.ids)]
            elif len(invoices_rec) == 1:
                action["views"] = [
                    (rec.env.ref("account.view_move_form").id, "form")
                ]
                action["res_id"] = invoices_rec.ids[0]
            else:
                action["domain"] = [("id", "in", [])]
        return action

    # def payslip_confirm(self):
    #     """Method to confirm payslip"""
    #     for rec in self:
    #         if not rec.journal_id:
    #             raise ValidationError(_("Kindly, Select Account Journal!"))
    #         if not rec.fees_structure_id:
    #             raise ValidationError(_("Kindly, Select Fees Structure!"))
    #         rec.write({"state": "confirm",})