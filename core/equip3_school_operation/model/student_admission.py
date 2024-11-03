import base64
import re

from odoo.modules import get_module_resource
from odoo import api, fields, models, _, tools
from datetime import timedelta, datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from . import school

class StudentAdmissionRegister(models.Model):
    _name = "student.admission.register"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Student Admission Register"
    _order = "create_date desc"

    @api.depends("student_type")
    def _compute_name(self):
        """Method to compute student name"""
        for rec in self:
            if rec.student_type:
                if rec.student_type == "existing_student":
                    student = rec.student_id.student_id
                else:
                    student = ""
                rec.student_name = student

    @api.model
    def _default_image(self):
        """Method to get default Image"""
        image_path = get_module_resource(
            "equip3_school_operation", "static/src/img", "student1.png"
        )
        return base64.b64encode(open(image_path, "rb").read())

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [("school_branch_ids", "in", allowed_branch_ids)]

    @api.model
    def check_current_year(self):
        """Method to get default value of logged in Student"""
        res = self.env["academic.year"].search([("current", "=", True)])
        if not res:
            raise ValidationError(
                _(
                    "There is no current Academic Year defined!\
            Please contact Administator!"
                )
            )
        return res.id

    @api.model
    def domain_intake(self):
        domain = [
            ("standard_id", "=", "program_id"),
            ("start_year", "=", "academic_code"),
            ("company_id", "=", self.env.company.id),
            ("branch_id", "in", self.env.branches.ids),
        ]

        return domain

    name = fields.Char("Name")
    family_con_ids = fields.One2many(
        "student.family.contact",
        "family_contact_id",
        "Family Contact Detail",
        states={"done": [("readonly", True)]},
        help="Select the student family contact",
    )
    user_id = fields.Many2one(
        "res.users",
        "User ID",
        ondelete="cascade",
        required=False,
        delegate=False,
        help="Select related user of the student",
    )

    school_id = fields.Many2one(
        "school.school",
        states={"done": [("readonly", True)]},
        string="School",
        domain=_domainSchool,
    )
    student_type = fields.Selection(
        [("new_student", "New Student"), ("existing_student", "Existing Student")],
        string="Student Type",
        default="new_student",
    )
    student_id = fields.Many2one(
        "student.student", "Student Name", help="Select related student"
    )
    pid = fields.Char(
        "Student ID",
        required=True,
        default=lambda self: _("New"),
        help="Personal Identification Number",
    )
    reg_code = fields.Char("Registration Code", help="Student Registration Code")
    student_code = fields.Char("Student Code", help="Enter student code")
    contact_phone = fields.Char("Phone no.", help="Enter student phone no.")
    contact_mobile = fields.Char("Mobile no", help="Enter student mobile no.")
    roll_no = fields.Integer("Roll No.", readonly=True, help="Enter student roll no.")
    cast_id = fields.Many2one(
        "student.cast", "Religion/Caste", help="Select student cast"
    )
    relation = fields.Many2one(
        "student.relation.master", "Relation", help="Select student relation"
    )
    admission_date = fields.Date(
        "Admission Date",
        default=fields.Date.today(),
        help="Enter student admission date",
    )
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female")],
        "Gender",
        states={"done": [("readonly", True)]},
        help="Select student gender",
    )
    date_of_birth = fields.Date(
        "BirthDate",
        required=True,
        states={"done": [("readonly", True)]},
        help="Enter student date of birth",
    )
    mother_tongue = fields.Many2one(
        "mother.toungue", "Mother Tongue", help="Select student mother tongue"
    )
    age = fields.Integer(
        compute="_compute_student_age",
        string="Age",
        store=True,
        readonly=True,
        help="Enter student age",
    )
    maritual_status = fields.Selection(
        [("unmarried", "Unmarried"), ("married", "Married")],
        "Marital Status",
        states={"done": [("readonly", True)]},
        help="Select student maritual status",
    )
    reference_ids = fields.One2many(
        "student.reference",
        "admission_id",
        "References",
        states={"done": [("readonly", True)]},
        help="Enter student references",
    )
    previous_school_ids = fields.One2many(
        "student.previous.school",
        "previous_school_id",
        "Previous School Detail",
        states={"done": [("readonly", True)]},
        help="Enter student school details",
    )
    doctor = fields.Char(
        "Doctor Name",
        states={"done": [("readonly", True)]},
        help="Enter doctor name for student medical details",
    )
    designation = fields.Char("Designation", help="Enter doctor designation")
    doctor_phone = fields.Char("Contact No.", help="Enter doctor phone")
    blood_group = fields.Char("Blood Group", help="Enter student blood group")
    height = fields.Float("Height", help="Hieght in C.M")
    weight = fields.Float("Weight", help="Weight in K.G")
    eye = fields.Boolean("Eyes", help="Eye for medical info")
    ear = fields.Boolean("Ears", help="Eye for medical info")
    nose_throat = fields.Boolean("Nose & Throat", help="Nose & Throat for medical info")
    respiratory = fields.Boolean("Respiratory", help="Respiratory for medical info")
    cardiovascular = fields.Boolean(
        "Cardiovascular", help="Cardiovascular for medical info"
    )
    neurological = fields.Boolean("Neurological", help="Neurological for medical info")
    muskoskeletal = fields.Boolean(
        "Musculoskeletal", help="Musculoskeletal for medical info"
    )
    dermatological = fields.Boolean(
        "Dermatological", help="Dermatological for medical info"
    )
    blood_pressure = fields.Boolean(
        "Blood Pressure", help="Blood pressure for medical info"
    )
    remark = fields.Text(
        "Remark",
        states={"done": [("readonly", True)]},
        help="Remark can be entered if any",
    )
    stu_name = fields.Char(
        "First Name",
        related="user_id.name",
        readonly=True,
        help="Enter student first name",
    )
    division_id = fields.Many2one(
        "standard.division", "Division", help="Select student standard division"
    )
    medium_id = fields.Many2one(
        "standard.medium", "Medium", help="Select student standard medium"
    )
    parent_id = fields.Many2many(
        comodel_name="school.parent",
        string="Parent(s)",
        states={"done": [("readonly", True)]},
        help="Enter student parents",
    )
    terminate_reason = fields.Text("Reason", help="Enter student terminate reason")
    teachr_user_grp = fields.Boolean(
        "Teacher Group",
        compute="_compute_teacher_user",
        help="Activate/Deactivate teacher group",
    )
    active = fields.Boolean(default=True, help="Activate/Deactivate student record")
    student_name = fields.Char(
        "Name",
        compute="_compute_name",
        store=True,
        help="Enter Student name",
        track_visibility="onchange",
    )
    fees_ids = fields.Many2one(
        "student.fees.structure",
        related="program_id.fees_ids",
        string="Fees Structure",
        store=True,
    )
    middle = fields.Char(required=False, track_visibility="onchange")
    last = fields.Char(required=False, track_visibility="onchange")
    full_name = fields.Char(compute="_compute_full_name")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="school_id.company_id",
        store=True
    )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partner")
    is_pdpa_constent = fields.Boolean(string="PDPA Constent")
    name_presented = fields.Char(
        string="Name Presented on Certificate",
        required=True,
        track_visibility="onchange",
    )
    nric = fields.Char(string="Identification No.", required=True)
    year = fields.Many2one(
        "academic.year",
        readonly=False,
        domain="[('current', '=', True)]",
        default=check_current_year,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("applied", "Applied"),
            ("confirmed", "Pending Payment"),
            ("done", "Done"),
            ("rejected", "Rejected"),
            ("cancel", "Cancel"),
        ],
        "Status",
        readonly=True,
        default="draft",
        help="State of the student registration form",
        track_visibility="onchange",
        tracking=True,
    )
    term_id = fields.Many2one(
        "academic.month", string="Term", compute="_compute_term_id", store=True
    )
    approved_matrix_id = fields.Many2one(
        "school.approval.matrix",
        compute="_compute_approved_matrix",
        string="Approving Matrix",
        store=True,
        required=False,
    )
    approved_matrix_ids = fields.One2many(
        comodel_name="school.approval.matrix.line",
        inverse_name="admission_student_id",
        compute="_approving_matrix_lines",
        store=True,
        string="Approved Matrix",
    )
    is_approve_button = fields.Boolean(
        string="Is Approve Button", compute="_get_approve_button", store=False
    )
    approval_matrix_line_id = fields.Many2one(
        "school.approval.matrix.line",
        string="Approval Matrix Line",
        compute="_get_approve_button",
        store=False,
    )
    program_id = fields.Many2one("standard.standard", string="Program", required=True)
    academic_code = fields.Char(related="year.code", string="Code", store=True)
    standard_id = fields.Many2one(
        "school.standard",
        domain=domain_intake,
        string="Intake",
        help="Select student standard",
    )
    program_ids = fields.One2many(
        "standard.standard",
        related="school_id.school_program_ids",
        string="Program",
        store=False,
    )
    portal_user_id = fields.Many2one("res.users", string="Portal User")
    phone = fields.Char(string="Phone", track_visibility="onchange")
    email = fields.Char(string="Email", track_visibility="onchange")
    mobile = fields.Char(string="Mobile", track_visibility="onchange")
    website = fields.Char(string="Website", track_visibility="onchange")
    photo = fields.Binary("Photo", default=_default_image, help="Attach student photo")
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
        "mail.activity",
        "res_id",
        "Activities",
        auto_join=True,
        groups="base.group_user",
    )
    academic_tracking_ids = fields.One2many("academic.tracking", "student_admission_id")
    subject_ids = fields.Many2many(
        "subject.subject", compute="_compute_subject_ids", store=True
    )
    branch_id = fields.Many2one(
        comodel_name="res.branch",
        related="school_id.branch_id",
        store=True,
        string="Branch",
    )
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="State",
        ondelete="restrict",
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict")
    comment = fields.Text("Notes")
    color = fields.Integer("Color Index")
    company_ids = fields.Many2many("res.company", string="Companies")
    type = fields.Selection(
        selection=[
            ("local_student", "Local Student"),
            ("international_student", "International Student"),
        ],
        string="Type",
        default="local_student",
    )
    personal_document = fields.Binary(string="Personal Document")
    transfer_student = fields.Selection(
        selection=[("yes", "Yes"), ("no", "No")], string="Transfer Student"
    )
    previous_school = fields.Char(string="Previous School")
    student_pass_registry = fields.Char(
        string="Student Pass Registry (SOLAR Application Number)"
    )
    student_pass_status = fields.Char(string="Student Pass Status")
    student_pass_digital = fields.Binary(string="Student Pass Digital")
    appeal_from = fields.Binary(string="Appeal From (If Needed)")
    med_checkup_form = fields.Binary(string="Medical Check Up Form")
    med_checkup_result = fields.Binary(string="Medical Check Up Result")
    med_checkup_date = fields.Date(string="Medical Check Up Date")
    admission_invoice_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending'),
            ('paid', 'Paid')
        ],
        compute='_compute_admission_invoice_state',
        store=True,
        string='Admission Invoice'
    )

    @api.depends('state', 'school_id', 'year', 'program_id')
    def _compute_admission_invoice_state(self):
        for admission in self:
            student_payslip = self.env["student.payslip"].search([
                ("first_student_payslip", "=", True),
                ("admission_reg_id", "=", admission.id)
            ], limit=1)
            if admission.state not in ["draft", "applied"]:
                if student_payslip:
                    invoice = self.env["account.move"].search([
                        ("student_payslip_id", "=", student_payslip.id),
                        ("move_type", "=", "out_invoice")
                    ])

                    if invoice and invoice.payment_state == "paid":
                        admission.admission_invoice_state = "paid"
                    else:
                        admission.admission_invoice_state = "pending"
            else:
                admission.admission_invoice_state = "draft"


    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("school_id.school_branch_ids", "in", context.get("allowed_branch_ids")),
                ("school_id.school_branch_ids", "=", False),
            ]

        result = super(StudentAdmissionRegister, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("school_id.school_branch_ids", "in", context.get("allowed_branch_ids")),
                    ("school_id.school_branch_ids", "=", False),
                ]
            )
        return super(StudentAdmissionRegister, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
    
    @api.model
    def create(self, vals):
        """Method to create user when student is created"""
        if vals.get("student_id"):
            self._update_student_vals(vals)

        if "student_type" in vals and vals["student_type"] == "existing_student":
            if self.env["student.history"].search(
                [
                    ("student_id", "=", vals["student_id"]),
                    ("program_id", "=", vals["program_id"]),
                    ("status", "=", "active"),
                ]
            ):
                raise ValidationError(
                    "Student can't admission with the same active program"
                )
        else:
            student_group = self.env.ref("school.group_school_student")
            emp_group = self.env.ref("base.group_user")
            new_grp_list = [student_group.id, emp_group.id]
            registered_user = self.env["res.users"].search(
                [("login", "=", vals.get("email"))]
            )
            if not registered_user:
                created_user = self.env["res.users"].create(
                    {
                        "name": vals.get("name"),
                        "login": vals.get("email"),
                        "password": vals.get("email"),
                        "groups_id": [(6, 0, new_grp_list)],
                    }
                )

                partner_informations = {
                    "street": vals.get("street"),
                    "street2": vals.get("street2"),
                    "country_id": vals.get("country_id"),
                    "city": vals.get("city"),
                    "state_id": vals.get("state_id"),
                    "zip": vals.get("zip"),
                    "phone": vals.get("phone"),
                    "mobile": vals.get("mobile"),
                    "email": vals.get("email")
                }
                
                if "is_customer" in created_user.partner_id._fields:
                    partner_informations["is_customer"] = True

                created_user.partner_id.write(partner_informations)
                vals["user_id"] = created_user.id

        if vals.get("pid", _("New")) == _("New"):
            vals["pid"] = self.env["ir.sequence"].next_by_code(
                "student.admission.register"
            ) or _("New")

        if vals.get("company_id", False):
            company_vals = {"company_ids": [(4, vals.get("company_id"))]}
            vals.update(company_vals)
        if vals.get("email"):
            school.emailvalidation(vals.get("email"))

        res = super(StudentAdmissionRegister, self).create(vals)

        admission_group = self.env.ref("school.group_school_student")
        res.user_id.write({"groups_id": [(4, admission_group.id)]})

        teacher = self.env["school.teacher"]
        for data in res.parent_id:
            teacher_rec = teacher.search([("stu_parent_id", "=", data.id)])
            for record in teacher_rec:
                record.write({"student_id": [(4, res.id, None)]})

        # Assign group to student based on condition
        emp_grp = self.env.ref("base.group_portal")
        if res.state == "draft":
            admission_group = self.env.ref("school.group_is_admission")
            new_grp_list = [admission_group.id, emp_grp.id]
            res.user_id.write({"groups_id": [(6, 0, new_grp_list)]})
        elif res.state == "done":
            done_student = self.env.ref("school.group_school_student")
            group_list = [done_student.id, emp_grp.id]
            res.user_id.write({"groups_id": [(6, 0, group_list)]})
        if self.env.user.has_group("base.group_portal"):
            res.user_id.active = False

        return res

    def write(self, vals):
        """Inherited write method to update values from student model"""
        if vals.get("student_id"):
            self._update_student_vals(vals)
        
        partner_informations = {}

        if "street" in vals:
            partner_informations["street"] = vals.get("street")
        
        if "street2" in vals:
            partner_informations["street2"] = vals.get("street2")
        
        if "country_id" in vals:
            partner_informations["country_id"] = vals.get("country_id")
        
        if "city" in vals:
            partner_informations["city"] = vals.get("city")
        
        if "zip" in vals:
            partner_informations["zip"] = vals.get("zip")
        
        if "phone" in vals:
            partner_informations["phone"] = vals.get("phone")
        
        if "mobile" in vals:
            partner_informations["mobile"] = vals.get("mobile")

        if "email" in vals:
            if vals.get("email"):
                school.emailvalidation(vals.get("email"))

            partner_informations["email"] = vals.get("email")
            self.user_id.write({"login": vals["email"]})
            
        if "is_customer" in self.user_id.partner_id._fields:
            if "is_customer" in vals:
                partner_informations["is_customer"] = True

        self.user_id.partner_id.write(partner_informations)

        return super(StudentAdmissionRegister, self).write(vals)

    def action_apply(self):
        for record in self:
            record.state = "applied"
            record.message_post(
                body="%s applied admission register" % (self.env.user.name)
            )

    def _prepare_student_values(self):
        values = {
            "pid": "New",
            "name": self.name,
            "middle": self.middle,
            "last": self.last,
            "school_id": self.school_id.id,
            "program_id": self.program_id.id,
            "standard_id": self.standard_id.id,
            "street": self.street,
            "street2": self.street2,
            "country_id": self.country_id.id,
            "city": self.city,
            "state_id": self.state_id.id,
            "zip": self.zip,
            "nric": self.nric,
            "gender": self.gender,
            "date_of_birth": self.date_of_birth,
            "email": self.email,
            "name_presented": self.full_name,
            "user_id": self.user_id.id,
            "state": "done",
        }

        return values

    def _action_create_student_invoice(self):
        for rec in self:
            if rec.student_type == "new_student":
                rec.write({"state": "confirmed"})

                student_journal = self.env["account.journal"].search(
                    [
                        ("type", "=", "sale"),
                        ("company_id", "=", rec.company_id.id)
                    ], limit=1
                )
                vals = {
                    "partner_id": self.user_id.partner_id.id,
                    "program": self.program_id.id,
                    "year_id": self.year.id,
                    "term_id": self.term_id.id,
                    "fees_structure_id": self.fees_ids.id,
                    "standard_id": self.standard_id.id,
                    "medium_id": self.medium_id.id,
                    "journal_id": student_journal.id,
                    "first_student_payslip": True,
                    "admission_reg_id": self.id,
                }
                slip_obj = self.env["student.payslip"].create(vals)
                slip_obj.onchange_student_id()
                slip_obj.payslip_confirm()
                slip_obj.student_pay_fees()

                """Email to Student"""
                template_id = self.env.ref(
                    "equip3_school_operation.student_admission_confirmation_email_template"
                ).id
                template = self.env["mail.template"].browse(template_id)
                template.send_mail(self.id, force_send=True)

                """Email to Parents"""
                if self.parent_id:
                    template_id = self.env.ref(
                        "equip3_school_operation.parents_confirmation_email_template"
                    ).id
                    template = self.env["mail.template"].browse(template_id)
                    template.send_mail(self.id, force_send=True)

                """Student Invoice Redirect"""
                return {
                    "name": _("Student Payslip"),
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "student.payslip",
                    "res_id": slip_obj.id,
                    "type": "ir.actions.act_window",
                    "target": "current",
                }
            elif rec.student_type == "existing_student":
                rec.write({"user_id": rec.student_id.user_id.id, "state": "confirmed"})
                student_journal = self.env["account.journal"].search(
                    [
                        ("type", "=", "sale"),
                        ("company_id", "=", rec.company_id.id)
                    ], limit=1
                )
                vals = {
                    "partner_id": self.user_id.partner_id.id,
                    "program": self.program_id.id,
                    "year_id": self.year.id,
                    "term_id": self.term_id.id,
                    "student_id": self.student_id.id,
                    "fees_structure_id": self.fees_ids.id,
                    "standard_id": self.standard_id.id,
                    "medium_id": self.medium_id.id,
                    "journal_id": student_journal.id,
                    "first_student_payslip": False,
                    "admission_reg_id": self.id,
                }
                slip_obj = self.env["student.payslip"].create(vals)
                slip_obj.onchange_student_id()
                slip_obj.payslip_confirm()
                slip_obj.student_pay_fees()
                """Email to Student"""
                template_id = self.env.ref(
                    "equip3_school_operation.student_confirmation_email_template"
                ).id
                template = self.env["mail.template"].browse(template_id)
                template.send_mail(self.student_id.id, force_send=True)
                """Email to Parents"""
                if self.parent_id:
                    template_id = self.env.ref(
                        "equip3_school_operation.parents_confirmation_email_template"
                    ).id
                    template = self.env["mail.template"].browse(template_id)
                    template.send_mail(self.student_id.id, force_send=True)
                """Student Invoice Redirect"""
                return {
                    "name": _("Student Payslip"),
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "student.payslip",
                    "res_id": slip_obj.id,
                    "type": "ir.actions.act_window",
                    "target": "current",
                }

    def action_reject(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ""
            if name != "":
                name += "\n • %s: Rejected" % (self.env.user.name)
            else:
                name += "• %s: Rejected" % (self.env.user.name)
            date = record.approval_matrix_line_id.approval_time or ""
            if date != "":
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            else:
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            record.approval_matrix_line_id.write(
                {
                    "last_approved": self.env.user.id,
                    "approved_users": [(4, self.env.user.id)],
                    "approval_time": date,
                    "approved_status": name,
                }
            )
            if record.approval_matrix_line_id.approved:
                record.state = "rejected"

    def action_confirm(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ""
            if name != "":
                name += "\n • %s: Approved" % (self.env.user.name)
            else:
                name += "• %s: Approved" % (self.env.user.name)
            date = record.approval_matrix_line_id.approval_time or ""
            if date != "":
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            else:
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            record.approval_matrix_line_id.write(
                {
                    "last_approved": self.env.user.id,
                    "approved_users": [(4, self.env.user.id)],
                    "approval_time": date,
                    "approved_status": name,
                }
            )
            if record.approval_matrix_line_id.approved:
                record.state = "confirmed"
                return record.sudo()._action_create_student_invoice()
            record.message_post(
                body="%s confirmed admission register" % (self.env.user.name)
            )

    def cancel_admission(self):
        self.state = "cancel"

    @api.depends("date_of_birth")
    def _compute_student_age(self):
        """Method to calculate student age"""
        current_dt = fields.Date.today()
        for rec in self:
            rec.age = 0
            if rec.date_of_birth and rec.date_of_birth < current_dt:
                start = rec.date_of_birth
                age_calc = (current_dt - start).days / 365
                # Age should be greater than 0
                if age_calc > 0.0:
                    rec.age = age_calc

    @api.onchange("gender")
    def _onchange_default_image(self):
        if self.gender == "male":
            image_path = get_module_resource(
                "equip3_school_operation", "static/src/img", "student1.png"
            )
        else:
            image_path = get_module_resource(
                "equip3_school_operation", "static/src/img", "student2.png"
            )
        self.photo = base64.b64encode(open(image_path, "rb").read())

    @api.depends("academic_tracking_ids", "academic_tracking_ids.all_score_subject_ids")
    def _compute_subject_ids(self):
        for rec in self:
            rec.subject_ids = [(5, 0, 0)]
            subject_ids = []
            for tracking in rec.academic_tracking_ids:
                subject_ids += tracking.all_score_subject_ids.mapped("subject_id").ids
            rec.subject_ids = [(6, 0, subject_ids)]

    def attendance_action_btn(self):
        action = {
            "type": "ir.actions.act_window",
            "name": "Attendance Line",
            "res_model": "daily.attendance.line",
            "domain": [("student_id", "=", self.id)],
            "view_mode": "tree",
        }
        return action

    @api.model
    def default_get(self, fields):
        res = super(StudentAdmissionRegister, self).default_get(fields)
        year_id = self.env["academic.year"].search(
            [("current", "=", True)], limit=1, order="id"
        )
        res["year"] = year_id and year_id.id or False
        return res

    @api.onchange("name", "middle", "last")
    def _onchange_first_middle_last_name(self):
        name_presented = self.name
        if self.middle:
            name_presented += " " + self.middle
        if self.last:
            name_presented += " " + self.last
        self.name_presented = name_presented

    @api.depends("name", "middle", "last")
    def _compute_full_name(self):
        for rec in self:
            full_name = rec.name
            if rec.middle:
                full_name += " " + rec.middle
            if rec.last:
                full_name += " " + rec.last
            rec.full_name = full_name

    @api.onchange("school_id", "program_id")
    def _onchange_standard_id(self):
        school_standard_id = self.env["school.standard"].search(
            [
                ("standard_id", "=", self.program_id.id),
                ("start_year", "=", self.year.code),
            ],
            limit=1,
        )
        if school_standard_id:
            self.standard_id = school_standard_id
        else:
            self.standard_id = False

        if self.school_id:
            branch_id = self.school_id.branch_id
            if not branch_id:
                branch_id = (
                    self.env["res.branch"]
                    .sudo()
                    .search(
                        [("company_id", "=", self.school_id.company_id.id)],
                        limit=1,
                        order="id desc",
                    )
                )
            self.branch_id = branch_id

    @api.depends("year")
    def _compute_term_id(self):
        for record in self:
            today_date = date.today()
            term_id = record.year.month_ids.filtered(
                lambda r: r.enrollment_date_start
                and r.enrollment_date_stop
                and r.enrollment_date_start <= today_date
                and r.enrollment_date_stop >= today_date
            )
            record.term_id = False
            if term_id:
                record.term_id = term_id and term_id[0].id or False

    def _get_approve_button(self):
        for record in self:
            record.is_approve_button = False
            record.approval_matrix_line_id = False
            if record.state == "applied":
                matrix_lines = sorted(
                    record.approved_matrix_ids.filtered(
                        lambda r: not r.approved and r.state == "confirmed"
                    )
                )
                if len(matrix_lines) > 0:
                    matrix_line_id = matrix_lines[0]
                    if (
                        self.env.user.id in matrix_line_id.user_id.ids
                        and self.env.user.id != matrix_line_id.last_approved.id
                    ):
                        record.is_approve_button = True
                        record.approval_matrix_line_id = matrix_line_id.id
            elif record.state == "confirmed":
                matrix_lines = sorted(
                    record.approved_matrix_ids.filtered(
                        lambda r: not r.approved and r.state == "done"
                    )
                )
                if len(matrix_lines) > 0:
                    matrix_line_id = matrix_lines[0]
                    if (
                        self.env.user.id in matrix_line_id.user_id.ids
                        and self.env.user.id != matrix_line_id.last_approved.id
                    ):
                        record.is_approve_button = True
                        record.approval_matrix_line_id = matrix_line_id.id
            elif record.state == "rejected":
                matrix_lines = sorted(
                    record.approved_matrix_ids.filtered(
                        lambda r: not r.approved and r.state == "draft"
                    )
                )
                if len(matrix_lines) > 0:
                    matrix_line_id = matrix_lines[0]
                    if (
                        self.env.user.id in matrix_line_id.user_id.ids
                        and self.env.user.id != matrix_line_id.last_approved.id
                    ):
                        record.is_approve_button = True
                        record.approval_matrix_line_id = matrix_line_id.id

    @api.depends("approved_matrix_id")
    def _approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            record.approved_matrix_ids = []
            for line in record.approved_matrix_id.approval_matrix_ids:
                data.append(
                    (
                        0,
                        0,
                        {
                            "state": line.state,
                            "user_id": [(6, 0, line.user_id.ids)],
                            "minimum_approver": line.minimum_approver,
                        },
                    )
                )
            record.approved_matrix_ids = data

    @api.depends("school_id", "program_id")
    def _compute_approved_matrix(self):
        for record in self:
            record.approved_matrix_id = False
            if record.school_id and record.program_id:
                approval_matrix_id = self.env["school.approval.matrix"].search(
                    [
                        ("school_id", "=", record.school_id.id),
                        ("program_id", "=", record.program_id.id),
                        "|",
                        ("approval_for", "=", "admission"),
                        ("approval_for", "=", False)
                    ],
                    limit=1,
                )
                record.approved_matrix_id = (
                    approval_matrix_id and approval_matrix_id.id or False
                )

    def action_apply(self):
        for record in self:
            record.state = "applied"
            record.message_post(
                body="%s applied admission register" % (self.env.user.name)
            )

    def action_reject(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ""
            if name != "":
                name += "\n • %s: Rejected" % (self.env.user.name)
            else:
                name += "• %s: Rejected" % (self.env.user.name)
            date = record.approval_matrix_line_id.approval_time or ""
            if date != "":
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            else:
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            record.approval_matrix_line_id.write(
                {
                    "last_approved": self.env.user.id,
                    "approved_users": [(4, self.env.user.id)],
                    "approval_time": date,
                    "approved_status": name,
                }
            )
            if record.approval_matrix_line_id.approved:
                record.state = "rejected"

    def action_set_to_draft(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ""
            if name != "":
                name += "\n • %s: Approved" % (self.env.user.name)
            else:
                name += "• %s: Approved" % (self.env.user.name)
            date = record.approval_matrix_line_id.approval_time or ""
            if date != "":
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            else:
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            record.approval_matrix_line_id.write(
                {
                    "last_approved": self.env.user.id,
                    "approved_users": [(4, self.env.user.id)],
                    "approval_time": date,
                    "approved_status": name,
                }
            )
            if record.approval_matrix_line_id.approved:
                record.state = "draft"

    @api.model
    def academic_year_term(self):
        today_date = date.today()
        start_date = date.today().replace(day=1)
        next_date = start_date.replace(day=28) + timedelta(days=4)
        next_month_date = (next_date - timedelta(days=next_date.day)) + timedelta(
            days=1
        )
        student_records = self.search(
            [
                ("state", "=", "done"),
                ("student_type", "=", "new_student"),
                ("fees_ids", "!=", False),
                ("year", "!=", False),
            ]
        )
        for student in student_records:
            if student.fees_ids.line_ids.filtered(lambda r: r.type == "term"):
                date_filter = student.year.month_ids.filtered(
                    lambda r: r.date_start.month == next_month_date.month
                )
                final_date = date_filter.billing_date
                journal = self.env["account.journal"].search(
                    [("type", "=", "sale"), ("company_id", "=", self.env.company.id)]
                )
                if final_date == today_date:
                    vals = {
                        "student_id": student.id,
                        "fees_structure_id": student.fees_ids.id,
                        "standard_id": student.standard_id.id,
                        "medium_id": student.medium_id.id,
                        "journal_id": journal.company_id.id,
                    }
                    slip_obj = self.env["student.payslip"].create(vals)
                    slip_obj.onchange_student_id()
                    slip_obj.monthly_payslip_confirm()
                    invoice_vals = slip_obj.student_pay_fees()
                    ctx = {
                        "email_from": self.env.company.email,
                    }
                    template_id = self.env.ref(
                        "equip3_school_operation.generate_student_invoice_email_templates"
                    )
                    template_id.with_context(ctx).send_mail(
                        invoice_vals["res_id"], force_send=True
                    )

    def student_admission_done(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ""
            if name != "":
                name += "\n • %s: Approved" % (self.env.user.name)
            else:
                name += "• %s: Approved" % (self.env.user.name)
            date = record.approval_matrix_line_id.approval_time or ""
            if date != "":
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            else:
                date += (
                    "•"
                    + self.env.user.name
                    + ":"
                    + datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
            record.approval_matrix_line_id.write(
                {
                    "last_approved": self.env.user.id,
                    "approved_users": [(4, self.env.user.id)],
                    "approval_time": date,
                    "approved_status": name,
                }
            )
            if record.approval_matrix_line_id.approved:
                record.write({"state": "done"})
                record.admission_done()

    def admission_done(self):
        # Define needed objects
        school_standard_obj = self.env["school.standard"]
        ir_sequence = self.env["ir.sequence"]
        student_group = self.env.ref("school.group_school_student")
        student_history = self.env["student.history"]
        emp_group = self.env.ref("base.group_user")
        new_grp_list = [student_group.id, emp_group.id]
        student_pass_tracker_obj = self.env['student.pass.tracker']

        for rec in self:
            academic_tracking_vals = {
                "program_id": rec.program_id.id,
                "school_id": rec.school_id.id,
                "intake_ids": [
                    (0, 0, {"intake_id": rec.standard_id.id, "status": "active"})
                ],
            }
            if rec.student_type == "new_student":
                # Prepare and create student
                student_values = rec._prepare_student_values()
                created_student = self.env["student.student"].create(student_values)
                rec.student_id = created_student.id
                rec.student_id.parent_id = rec.parent_id

                if rec.portal_user_id:
                    rec.portal_user_id.groups_id = [(6, 0, new_grp_list)]
                    rec.portal_user_id.related_student_id = rec.student_id.id
                elif rec.user_id.has_group('base.group_portal'):
                    rec.user_id.groups_id = [(6, 0, new_grp_list)]
                    rec.user_id.related_student_id = rec.student_id.id

                # Update stuednt payslip and assign student_id
                student_payslip = self.env["student.payslip"].search(
                    [("partner_id", "=", self.user_id.partner_id.id)],
                    limit=1, order="create_date desc"
                )
                student_payslip.student_id = rec.student_id.id

                # Create academic tracking
                academic_tracking_vals.update({"student_id": rec.student_id.id})
                academic_tracking_id = self.env["academic.tracking"].create(
                    academic_tracking_vals
                )

                # Create student pass tracker
                if rec.type == "international_student":
                    sp_digital = False
                    appeal_form = False
                    med_checkup_form = False
                    med_checkup_result = False

                    if rec.student_pass_digital:
                        sp_digital = base64.b64encode(rec.student_pass_digital)
                    if rec.appeal_from:
                        appeal_form = base64.b64encode(rec.appeal_from)
                    if rec.med_checkup_form:
                        med_checkup_form = base64.b64encode(rec.med_checkup_form)
                    if rec.med_checkup_result:
                        med_checkup_result = base64.b64encode(rec.med_checkup_form)

                    student_pass_tracker_obj.create(
                        {
                            'student_name': rec.student_id.id,
                            'school': rec.school_id.id,
                            'source_document': rec.pid,
                            'sp_digital': sp_digital,
                            'sola_id': rec.student_pass_registry,
                            'sp_request_status': rec.student_pass_status,
                            'transfer_student': rec.transfer_student,
                            'appeal_form': appeal_form,
                            'med_checkup_form': med_checkup_form,
                            'med_checkup_result': med_checkup_result,
                            'med_checkup_date': rec.med_checkup_date,
                        }
                    )

                if not rec.standard_id:
                    raise ValidationError(_("Please select class!"))
                if rec.standard_id.remaining_seats <= 0:
                    raise ValidationError(
                        _("Seats of class %s are full")
                        % rec.standard_id.standard_id.name
                    )
                domain = [("school_id", "=", rec.school_id.id)]
                if not school_standard_obj.search(domain):
                    raise UserError(
                        _("Warning! The standard is not defined in school!")
                    )
                number = 1
                for rec_std in rec.search(domain):
                    rec_std.roll_no = number
                    number += 1
                reg_code = ir_sequence.next_by_code("student.registration")
                registation_code = (
                    str(rec.school_id.state_id.name)
                    + str("/")
                    + str(rec.school_id.city)
                    + str("/")
                    + str(rec.school_id.name)
                    + str("/")
                    + str(reg_code)
                )
                stu_code = ir_sequence.next_by_code("student.code")
                student_code = (
                    str(rec.school_id.code)
                    + str("/")
                    + str(rec.year.code)
                    + str("/")
                    + str(stu_code)
                )
                rec.student_id.write(
                    {
                        "student_id": rec.student_id.id,
                        "admission_date": fields.Date.today(),
                        "student_code": student_code,
                        "reg_code": registation_code,
                    }
                )
                student_history.create(
                    {
                        "student_id": self.student_id.id,
                        "academice_year_id": rec.year.id,
                        "division_id": rec.standard_id.division_id.id,
                        "standard_id": rec.standard_id.id,
                        "status": "active",
                        "medium_id": rec.medium_id.id,
                        "school_id": rec.school_id.id or False,
                        "term_id": rec.term_id.id or False,
                        "program_id": rec.program_id.id or False,
                    }
                )

            elif rec.student_type == "existing_student":
                rec.student_id.write(
                    {
                        "name": rec.name,
                        "last": rec.last,
                        "middle": rec.middle,
                        "year": rec.year.id or False,
                        "email": rec.email,
                        "name_presented": rec.name_presented,
                        "nric": rec.nric,
                        "school_id": rec.school_id.id or False,
                        "street": rec.street,
                        "street2": rec.street2,
                        "city": rec.city,
                        "state_id": rec.state_id.id or False,
                        "zip": rec.zip,
                        "country_id": rec.country_id.id or False,
                        "gender": rec.gender,
                        "date_of_birth": rec.date_of_birth,
                        "admission_date": fields.Date.today(),
                        "history_ids": [
                            (
                                0,
                                0,
                                {
                                    "academice_year_id": rec.year.id,
                                    "division_id": rec.standard_id.division_id.id,
                                    "standard_id": rec.standard_id.id,
                                    "status": "active",
                                    "medium_id": rec.medium_id.id,
                                    "school_id": rec.school_id.id or False,
                                    "term_id": rec.term_id.id or False,
                                    "program_id": rec.program_id.id or False,
                                },
                            )
                        ],
                    }
                )
                academic_tracking_vals.update({"student_id": rec.student_id.id})
                academic_tracking_id = self.env["academic.tracking"].create(
                    academic_tracking_vals
                )
                rec.student_id.standard_id.write(
                    {
                        "intake_student_line_ids": [
                            (0, 0, {"student_id": rec.student_id.id})
                        ]
                    }
                )

    @api.onchange("student_id")
    def onchange_student_id(self):
        if self.student_type == "existing_student" and self.student_id:
            self.name = self.student_id.name or False
            self.middle = self.student_id.middle or False
            self.last = self.student_id.last or False
            self.year = self.student_id.year.id or False
            self.email = self.student_id.email or False
            self.fees_ids = self.student_id.fees_ids.id or False
            self.name_presented = self.student_id.name_presented or False
            self.nric = self.student_id.nric or False
            self.school_id = self.student_id.school_id.id or False
            self.street = self.student_id.street or False
            self.street2 = self.student_id.street2 or False
            self.city = self.student_id.city or False
            self.state_id = self.student_id.state_id.id or False
            self.zip = self.student_id.zip or False
            self.country_id = self.student_id.country_id.id or False
            self.gender = self.student_id.gender or False
            self.date_of_birth = self.student_id.date_of_birth or False
            self.term_id = self.student_id.term_id.id or False
        else:
            self.name = False
            self.middle = False
            self.last = False
            self.email = False
            self.fees_ids = False
            self.name_presented = False
            self.nric = False
            self.school_id = False
            self.street = False
            self.street2 = False
            self.city = False
            self.state_id = False
            self.zip = False
            self.country_id = False
            self.gender = False
            self.date_of_birth = False

    def _update_student_vals(self, vals):
        student_rec = self.env["student.student"].browse(vals.get("student_id"))
        partner_id = self.env["res.partner"].browse(vals.get("partner_id"))
        vals.update(
            {
                "name": student_rec.name,
                "middle": student_rec.middle,
                "last": student_rec.last,
                "gender": student_rec.gender,
                "date_of_birth": student_rec.date_of_birth,
            }
        )

    def button_admission_invoice(self):
        action = self.env.ref("school_fees.action_student_payslip_form").read()[0]
        payslips = self.env["student.payslip"].search(
            [("partner_id", "=", self.user_id.partner_id.id)]
        )
        if len(payslips) > 1:
            action["domain"] = [("id", "in", payslips.ids)]
        elif len(payslips) == 1:
            action["views"] = [
                (self.env.ref("school_fees.view_student_payslip_form").id, "form")
            ]
            action["res_id"] = payslips.ids[0]
        else:
            action["domain"] = [("id", "in", [])]
        return action
    
    @api.constrains('date_of_birth')
    def check_age(self):
        current_dt = fields.Date.today()
        for admission in self:
            if admission.date_of_birth and admission.date_of_birth < current_dt:
                birth_day = admission.date_of_birth
                age = ((current_dt - birth_day).days / 365)
                if age < admission.school_id.required_age:
                    raise ValidationError(
                        _(
                            "Age of student should be greater than %s years!" 
                            % (admission.school_id.required_age)
                        )
                    )
            else:
                raise ValidationError(
                    _(
                        "Age of student should be greater than %s years!" 
                        % (admission.school_id.required_age)
                    )
                )


class SchoolApprovalMatrixLineInherit(models.Model):
    _inherit = "school.approval.matrix.line"

    admission_student_id = fields.Many2one(
        comodel_name="student.admission.register", string="Student"
    )
