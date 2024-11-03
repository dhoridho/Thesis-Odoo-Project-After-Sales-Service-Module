from odoo import fields, models, api
from datetime import date


class EmployeeProbationMass(models.Model):
    _name = "employee.probation.mass"
    _description = "Employee Probation Mass"

    name = fields.Char(string="Name")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        string="Company",
    )
    period = fields.Selection(
        selection=[
            ("by_specific_date", "Specific Date"),
            ("with_masterdata", "Using Masterdata Periods"),
        ],
        default="by_specific_date",
        string="Period",
    )
    probation_period_id = fields.Many2one(
        "employee.probation.period", string="Probation Period"
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("on_going", "On Going"),
            ("done", "Done"),
        ],
        default="draft",
        string="Status",
    )
    employee_ids = fields.One2many(
        comodel_name="employee.probation.mass.line",
        inverse_name="employee_probation_mass_id",
        string="Employee",
    )
    show_submit = fields.Boolean()

    @api.model
    def create(self, vals):
        vals["name"] = (
            self.env["ir.sequence"].next_by_code("employee.probation.mass.sequence")
            or "New"
        )
        vals["show_submit"] = True
        return super(EmployeeProbationMass, self).create(vals)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeProbationMass, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeProbationMass, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def action_submit(self):
        for line in self.employee_ids:
            data = {
                "employee_id": line.name.id,
                "employee_email": line.name.work_email,
                "department_id": line.department_id.id,
                "manager_id": line.name.parent_id.id,
                "employee_probation_period": self.period,
                "emp_probation_period_id": self.probation_period_id.id,
                "start_date": line.start_date,
                "end_date": line.end_date,
                "state": "draft",
                "probation_mass_line_id": line.id,
            }

            employee_probation = self.env["employee.probation"].create(data)
            employee_probation.action_submit()
            line.number = employee_probation.name

        self.write({"show_submit": False, "state": "submitted"})

    @api.onchange("period")
    def _onchange_period(self):
        for probation in self:
            if probation.period == "with_masterdata":
                probation.start_date = False
                probation.end_date = False
            else:
                probation.probation_period_id = False
                probation.start_date = False
                probation.end_date = False

    @api.onchange("probation_period_id")
    def _onchangeprobation_period(self):
        for probation in self:
            if probation.probation_period_id:
                probation.start_date = probation.probation_period_id.start_date
                probation.end_date = probation.probation_period_id.end_date
            else:
                probation.start_date = False
                probation.end_date = False

    @api.onchange("employee_ids", "start_date", "end_date")
    def _onchange_date(self):
        for line in self.employee_ids:
            if not line.start_date:
                line.start_date = self.start_date if self.start_date else False
            if not line.end_date:
                line.end_date = self.end_date if self.end_date else False

    @api.onchange("employee_ids")
    def _onchange_employee_ids(self):
        for line in self.employee_ids:
            line.department_id = line.name.department_id.id if line.name else False


class EmployeeProbationMassLine(models.Model):
    _name = "employee.probation.mass.line"
    _description = "Employee Probation Mass Line"

    @api.model
    def _employee_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    @api.model
    def _department_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    name = fields.Many2one(comodel_name="hr.employee", string="Employee", domain=_employee_domain)
    number = fields.Char(string="Refference", readonly=True)
    department_id = fields.Many2one(comodel_name="hr.department", string="Department", domain=_department_domain)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("on_going", "On Going"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
    )
    employee_probation_mass_id = fields.Many2one(
        comodel_name="employee.probation.mass", string="Employee Probation Mass"
    )


class EmployeePribationExtend(models.Model):
    _inherit = "employee.probation"

    probation_mass_line_id = fields.Many2one(
        comodel_name="employee.probation.mass.line",
        string="Employee Probation Mass Line",
    )
