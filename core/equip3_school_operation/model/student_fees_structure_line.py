from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError


class StudentFeesStructureLine(models.Model):
    _name = "student.fees.structure.line"
    _inherit = ["student.fees.structure.line", "mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    @api.model
    def _domain_account_id(self):
        return [('company_id', '=', self.env.company.id)]

    fee_tax_id = fields.Many2one('account.tax', string="GST")
    type = fields.Selection(selection_add=[("one_time", "One Time"), ("term", "Term")], ondelete={
        'one_time': 'cascade', 'term': 'cascade'})

    message_ids = fields.One2many(
        "mail.message",
        "res_id",
        "Messages",
        domain=lambda self: [("model", "=", self._name)],
        auto_join=True,
        help="Messages can entered",
    )
    message_follower_ids = fields.One2many(
        "mail.followers",
        "res_id",
        "Followers",
        domain=lambda self: [("res_model", "=", self._name)],
        help="Select message followers",
    )
    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        groups="base.group_user", )
    account_id = fields.Many2one(
        comodel_name='account.account',
        domain=_domain_account_id,
    )
    company_id = fields.Many2one(
        "res.company",
        change_default=False,
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals_list):
        product_obj = self.env['product.template']
        res = super(StudentFeesStructureLine, self).create(vals_list)
        products_to_create = []
        for rec in res:
            product_vals = {
                'name': rec.name,
                'default_code': rec.code,
                'list_price': rec.amount
            }
            products_to_create.append(product_vals)
        product_obj.create(products_to_create)
        return res

    def write(self, vals):
        if 'amount' in vals:
            self._cr.execute("""
                SELECT fees_id FROM fees_structure_payslip_rel slip
                WHERE slip_id in %s
            """, [tuple(self.ids)])
            result = [r[0] for r in self._cr.fetchall()]
            for fee in self.env['student.fees.structure'].browse(result):
                message_body = "Fees Structure (%s)  Amount Changed -> %s" % (
                    vals.get('name') or self.name, vals['amount'])
                fee.message_post(body=message_body)
        return super(StudentFeesStructureLine, self).write(vals)


class StudentPayslip(models.Model):
    _inherit = "student.payslip"

    year_id = fields.Many2one(
        'academic.year', string='Academic Year')
    term_id = fields.Many2one(
        'academic.month', string="Term")
    amount_taxes = fields.Float(string="Taxes", compute="_compute_amount_tax", store=True)
    total_untaxed = fields.Float(string="Subtotal", compute="_compute_total_untaxed", store=True)
    first_student_payslip = fields.Boolean(string="First Student Payslip", default=False)
    payment_details = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash')
    ], string="Payment Details")
    amount = fields.Float(string="Amount")
    date_of_receipt = fields.Date(string="Date of Receipt")
    proof_of_payment = fields.Binary(string='Proof of Payment')
    proof_of_payment_filename = fields.Char(string='Proof of Payment Filename')
    receipt_number = fields.Char(string="Receipt Number")
    remarks = fields.Text(string="Remarks")
    admission_ref = fields.Many2one(comodel_name="student.student", string="Admission Ref")
    admission_reg_id = fields.Many2one(comodel_name="student.admission.register", string="Admission Register ID")
    student_id = fields.Many2one("student.student", string="Student", required=False)

    # Commented to avoid tupicate lines
    # @api.model
    # def create(self, vals):
    #     res = super(StudentPayslip, self).create(vals)
    #     res.onchange_fees_structure_id()
    #     return res

    def payslip_paid(self):
        res = super(StudentPayslip, self).payslip_paid()
        for record in self:
            if record.admission_reg_id:
                admssion = self.env['student.admission.register'].browse(record.admission_reg_id.id)
                admssion.student_admission_done()
        return res

    @api.onchange('fees_structure_id')
    def onchange_fees_structure_id(self):
        for rec in self:
            if rec.fees_structure_id:
                rec.line_ids = [(5, 0, 0)]
                lines = []
                for data in self.fees_structure_id.line_ids:
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
                rec.line_ids = lines

    @api.depends('line_ids', 'line_ids.price_tax', 'line_ids.amount')
    def _compute_amount_tax(self):
        for record in self:
            record.amount_taxes = sum(record.line_ids.mapped('price_tax'))
            record.total += record.amount_taxes

    @api.depends('line_ids', 'line_ids.amount')
    def _compute_total_untaxed(self):
        for record in self:
            record.total_untaxed = sum(record.line_ids.mapped('amount'))

    def payslip_confirm(self):
        for rec in self:
            if not rec.journal_id:
                raise ValidationError(_("Kindly, Select Account Journal!"))
            if not rec.fees_structure_id:
                raise ValidationError(_("Kindly, Select Fees Structure!"))
            lines = []
            for data in rec.fees_structure_id.line_ids or []:
                payslip_line_exist = rec.line_ids.filtered(lambda line: line.code == data.code)
                if not payslip_line_exist:
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
                }
            )
            for line in rec.line_ids:
                filter_line = line.slip_id.fees_structure_id.line_ids.filtered(
                    lambda r: r.name == line.name and r.code == line.code)
                line.fee_tax_id = filter_line.fee_tax_id.id
        return True

    def student_pay_fees(self):
        res = super(StudentPayslip, self).student_pay_fees()
        for rec in self:
            invoice_ids = self.env['account.move'].search(
                [('student_payslip_id', '=', rec.id)], limit=1)
            invoice_ids.write({
                'partner_id': rec.partner_id.id or rec.student_id.user_id.partner_id.id,
                'branch_id': rec.register_id.branch_id.id or rec.standard_id.branch_id.id,
            })
            for line in rec.line_ids:
                invoice_ids.invoice_line_ids.filtered(lambda r: r.name == line.name).write({
                    'tax_ids': [(6, 0, line.fee_tax_id.ids)]
                })
        return res
    
    @api.onchange('student_id')
    def onchange_student(self):
        res = super(StudentPayslip, self).onchange_student()
        if self.student_id and self.student_id.program_id:
            self.program = self.student_id.program_id.id
        
        return res


class StudentPayslipLine(models.Model):
    _inherit = 'student.payslip.line'

    fee_tax_id = fields.Many2one('account.tax', string="Tax")
    type = fields.Selection(selection_add=[("one_time", "One Time"), ("term", "Term")], ondelete={
        'one_time': 'cascade', 'term': 'cascade'})
    price_tax = fields.Float(compute='_compute_price_tax', string='Price Tax', readonly=True, store=True)

    @api.depends('amount', 'fee_tax_id')
    def _compute_price_tax(self):
        for record in self:
            taxes = record.fee_tax_id.compute_all(record.amount)
            record.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
