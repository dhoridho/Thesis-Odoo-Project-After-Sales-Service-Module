from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64


class HrContractInherit(models.Model):
    _inherit = 'hr.contract'
    
    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    work_location_id = fields.Many2one('work.location.object', "Work Location",domain=_multi_company_domain)
    branch_id = fields.Many2one("res.branch", string="Branch",
                                tracking=True)
    daily_wage = fields.Monetary()
    contract_template = fields.Many2one('hr.contract.letter')
    edit_hide_css = fields.Html(string='CSS', sanitize=False, compute='_compute_edit_hide_css')
    certificate_attachment = fields.Binary(string='Certificate Attachment')
    certificate_attachment_fname = fields.Char('Certificate Name')
    email_template_id = fields.Many2one(comodel_name="mail.template", string="Email Template",
                                        help="This field contains the Email Template that will be used by default when sending this Email.",
                                        )
    employee_signature = fields.Binary(string="Employee Signature")
    hourly_wage = fields.Monetary()
    partner_id = fields.Many2one('res.partner', 'Partner')
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('other', 'Other Address'),
         ("private", "Private Address"),
         ], string='Address Type',
        help="Invoice & Delivery addresses are used in sales orders. Private addresses are only visible by authorized users.")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrContractInherit, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrContractInherit, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def update_digital_sign(self):
        for rec in self:
            module_installed = self.env['ir.module.module'].search(
                [('name', '=', 'web_digital_sign'), ('state', '=', 'installed')], limit=1)
            if module_installed and rec.employee_id.user_id.digital_signature:
                rec.employee_signature = rec.employee_id.user_id.digital_signature
            else:
                rec.employee_signature = False

    @api.depends('state')
    def _compute_edit_hide_css(self):
        for rec in self:
            if rec.state not in ['draft']:
                rec.edit_hide_css = '<style>.btn.btn-primary.o_form_button_edit {display: none !important;} .o_form_label.o_readonly_modifier{display: none !important;} </style>'
            else:
                rec.edit_hide_css = False
                
                

                
    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=True, submenu=True):
    #     ##Sample Code of Hide print ,action menu and particular report
    #     if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
    #         res = res = super().fields_view_get(view_id=view_id, view_type=view_type)
    #         remove_report_id = self.env.ref('equip3_hr_contract_extend.equip3_hr_contract_letter_mail').id
    #         if view_type == 'form' or view_type == 'tree' and remove_report_id and \
    #             toolbar and res['toolbar'] and res['toolbar'].get('print'):
    #             remove_report_record = [rec for rec in res['toolbar'].get('print') if rec.get('id')== remove_report_id]
    #             if remove_report_record and remove_report_record[0]:
    #                 res['toolbar'].get('print').remove(remove_report_record[0])
    #         return res

    def print_on_page(self):
        self.update_digital_sign()
        for record in self:
            if record.date_start:
                date_start = datetime.strptime(str(record.date_start), "%Y-%m-%d")
                date_start_string = datetime(date_start.year, date_start.month,
                                             date_start.day).strftime("%d %B %Y")
            if record.visa_expire:
                visa_expire = datetime.strptime(str(record.visa_expire), "%Y-%m-%d")
                visa_expire_string = datetime(visa_expire.year, visa_expire.month,
                                              visa_expire.day).strftime("%d %B %Y")

            if record.trial_date_end:
                trial_date_end = datetime.strptime(str(record.trial_date_end), "%Y-%m-%d")
                trial_date_end_string = datetime(trial_date_end.year, trial_date_end.month,
                                                 trial_date_end.day).strftime("%d %B %Y")
            if record.first_contract_date:
                first_contract_date = datetime.strptime(str(record.first_contract_date), "%Y-%m-%d")
                first_contract_date_string = datetime(first_contract_date.year, first_contract_date.month,
                                                      first_contract_date.day).strftime("%d %B %Y")
            if record.date_end:
                date_end = datetime.strptime(str(record.date_end), "%Y-%m-%d")
                date_end_string = datetime(date_end.year, date_end.month,
                                           date_end.day).strftime("%d %B %Y")
            if record.create_date:
                create_date = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
                create_date_string = datetime(create_date.year, create_date.month,
                                              create_date.day).strftime("%d %B %Y")
            if not record.contract_template:
                raise ValidationError("Letter not set in Contract")
            temp = record.contract_template.letter_content
            letter_content_replace = record.contract_template.letter_content
            if "$(name)" in letter_content_replace:
                if not record.name:
                    raise ValidationError("Contract Reference is empty")
                letter_content_replace = str(letter_content_replace).replace("$(name)", record.name)
            if "$(branch_id)" in letter_content_replace:
                if not record.branch_id:
                    raise ValidationError("Branch is empty")
                letter_content_replace = str(letter_content_replace).replace("$(branch_id)", record.branch_id.name)
            if "$(company_country_id)" in letter_content_replace:
                if not record.company_country_id:
                    raise ValidationError("Company country is empty")
                letter_content_replace = str(letter_content_replace).replace("$(company_country_id)",
                                                                             record.company_country_id.name)
            if "$(company_id)" in letter_content_replace:
                if not record.company_id:
                    raise ValidationError("Company is empty")
            if "$(currency_id)" in letter_content_replace:
                if not record.currency_id:
                    raise ValidationError("Currency is empty")
                letter_content_replace = str(letter_content_replace).replace("$(currency_id)", record.currency_id.name)
            if "$(daily_wage)" in letter_content_replace:
                if not record.daily_wage:
                    raise ValidationError("Daily Wage is empty")
                letter_content_replace = str(letter_content_replace).replace("$(daily_wage)", record.daily_wage)
            if "$(date_end)" in letter_content_replace:
                if not record.date_end:
                    raise ValidationError("Date end is empty")
                letter_content_replace = str(letter_content_replace).replace("$(date_end)", date_end_string)
            if "$(employee_id)" in letter_content_replace:
                if not record.employee_id:
                    raise ValidationError("Employee is empty")
                letter_content_replace = str(letter_content_replace).replace("$(employee_id)", record.employee_id.name)
            if "$(employee_signature)" in letter_content_replace:
                if not record.employee_id:
                    raise ValidationError("Employee Signature is empty")
                if record.employee_signature:
                    attachment = self.env['ir.attachment'].search(
                        [('res_model', '=', 'res.users'), ('res_id', '=', record.employee_id.user_id.id),
                         ('res_field', '=', 'digital_signature')], limit=1)
                    sign_url = '''"/web/image/ir.attachment/''' + str(attachment.id) + '''/datas"'''
                    img_tag = '''<img src=''' + str(
                        sign_url) + ' ' + '''class="img img-fluid" border="1" width="200" height="150"/>'''

                    letter_content_replace = str(letter_content_replace).replace("$(employee_signature)", str(img_tag))
                else:
                    letter_content_replace = str(letter_content_replace).replace("$(employee_signature)", str())
            if "$(date_start)" in letter_content_replace:
                if not record.date_start:
                    raise ValidationError("Date  Start is empty")
                letter_content_replace = str(letter_content_replace).replace("$(date_start)", date_start_string)
            if "$(first_contract_date)" in letter_content_replace:
                if not record.first_contract_date:
                    raise ValidationError("First Contract Date   is empty")
                letter_content_replace = str(letter_content_replace).replace("$(first_contract_date)",
                                                                             first_contract_date_string)
            if "$(resource_calendar_id)" in letter_content_replace:
                if not record.resource_calendar_id:
                    raise ValidationError("Resource Calendar is empty")
                letter_content_replace = str(letter_content_replace).replace("$(resource_calendar_id)",
                                                                             record.resource_calendar_id.name)
            if "$(hr_responsible_id)" in letter_content_replace:
                if not record.hr_responsible_id:
                    raise ValidationError("HR Responsible is empty")
                letter_content_replace = str(letter_content_replace).replace("$(hr_responsible_id)",
                                                                             record.hr_responsible_id.name)
            if "$(notes)" in letter_content_replace:
                if not record.notes:
                    raise ValidationError("Notes is empty")
                letter_content_replace = str(letter_content_replace).replace("$(notes)", record.notes)

            if "$(permit_no)" in letter_content_replace:
                if not record.notes:
                    raise ValidationError("Work permit is empty")
                letter_content_replace = str(letter_content_replace).replace("$(permit_no)", record.permit_no)
            if "$(state)" in letter_content_replace:
                if not record.state:
                    raise ValidationError("Status  is empty")
                letter_content_replace = str(letter_content_replace).replace("$(state)", record.permit_no)
            if "$(structure_type_id)" in letter_content_replace:
                if not record.structure_type_id:
                    raise ValidationError("Salary Structure Type is empty")
                letter_content_replace = str(letter_content_replace).replace("$(structure_type_id)",
                                                                             record.structure_type_id.name)
            if "$(trial_date_end_string)" in letter_content_replace:
                if not record.trial_date_end:
                    raise ValidationError("End of Trial Period is empty")
                letter_content_replace = str(letter_content_replace).replace("$(trial_date_end_string)",
                                                                             trial_date_end_string)
            if "$(type_id)" in letter_content_replace:
                if not record.type_id:
                    raise ValidationError("Employee Category is empty")
                letter_content_replace = str(letter_content_replace).replace("$(type_id)", record.type_id.name)
            if "$(visa_expire_string)" in letter_content_replace:
                if not record.visa_expire_string:
                    raise ValidationError("Visa Expire Date is Empty")
                letter_content_replace = str(letter_content_replace).replace("$(visa_expire_string)",
                                                                             visa_expire_string)
            if "$(visa_no)" in letter_content_replace:
                if not record.visa_no:
                    raise ValidationError("Visa No is Empty")
                letter_content_replace = str(letter_content_replace).replace("$(visa_expire_string)",
                                                                             visa_expire_string)
            if "$(wage)" in letter_content_replace:
                if not record.wage:
                    letter_content_replace = str(letter_content_replace).replace("$(wage)","0")
                letter_content_replace = str(letter_content_replace).replace("$(wage)", str(record.wage))

            if "$(job_id)" in letter_content_replace:
                if not record.job_id:
                    raise ValidationError("Job is empty")
                letter_content_replace = str(letter_content_replace).replace("$(job_id)", record.job_id.name)
            if "$(department_id)" in letter_content_replace:
                if not record.department_id:
                    raise ValidationError("Department is empty")
                letter_content_replace = str(letter_content_replace).replace("$(department_id)",
                                                                             record.department_id.name)
            if "$(work_location_id)" in letter_content_replace:
                if not record.work_location_id:
                    raise ValidationError("Work Location is empty")
                letter_content_replace = str(letter_content_replace).replace("$(work_location_id)",
                                                                             record.work_location_id.name)
            if "$(create_date)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(create_date)", create_date_string)

            record.contract_template.letter_content = letter_content_replace
            data = record.contract_template.letter_content
            record.contract_template.letter_content = temp

            return data

    def search_manpower_planning(self):
        mpp_on = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp')
        if mpp_on:
            if self.first_contract_date:
                first_contract_date = datetime.strptime(str(self.first_contract_date), "%Y-%m-%d")
                mpp_line = self.env['manpower.planning.line'].search(
                    [('job_position_id', '=', self.job_id.id), ('work_location_id', '=', self.work_location_id.id)])
                if mpp_line:
                    for record in mpp_line:
                        if record.manpower_id:
                            if first_contract_date.date() >= record.manpower_id.mpp_period.start_period and first_contract_date.date() <= record.manpower_id.mpp_period.end_period:
                                record.total_fullfillment = record.total_fullfillment + 1

    @api.model
    def ir_cron_send_notification(self):
        global_setting = self.env['expiry.contract.notification'].search([])

        now = datetime.now()
        draft_contract = self.search([('state', '=', 'draft'), ('date_start', '<=', now.date())])
        emp_cont_dict = []
        emp_cont_double_dict = []
        for rec in draft_contract:
            if rec.employee_id not in emp_cont_dict:
                emp_cont_dict.append(rec.employee_id)
            elif rec.employee_id in emp_cont_dict and rec.employee_id not in emp_cont_double_dict:
                emp_cont_double_dict.append(rec.employee_id)
        if draft_contract:
            for data in draft_contract.filtered(lambda r: r.employee_id not in emp_cont_double_dict):
                data.state = 'open'
                employee = self.env['hr.employee'].browse(data.employee_id.id)
                employee.department_id = data.department_id.id
                employee.job_id = data.job_id.id
                data.search_manpower_planning()
        running_contract = self.search([('state', '=', 'open'), ('date_end', '<=', now.date())])
        if running_contract:
            contract_expired_ids = []
            for data_running in running_contract:
                data_running.state = 'close'
                contract_expired_ids.append(data_running.id)
            global_setting.send_notification("contract_expire", contract_expired_ids)
        total_days = global_setting.days
        to_renew_contract = self.search([('date_end', '=', now.date() + timedelta(days=total_days))])
        if to_renew_contract:
            data_renew_ids = []
            for data_renew in to_renew_contract:
                data_renew_ids.append(data_renew.id)
            global_setting.send_notification("contract_renew", data_renew_ids)

    def write(self, vals):
        res = super(HrContractInherit, self).write(vals)
        if vals.get('state'):
            if vals.get('state') == 'open':
                self.search_manpower_planning()
            self.employee_id.department_id = self.department_id.id
            self.employee_id.job_id = self.job_id.id
        return res

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.work_location_id = self.employee_id.location_id
            if self.employee_id.newly_hired_employee:
                applicant = self.env['hr.applicant'].search([('emp_id','=',self.employee_id.id)],limit=1)
                if applicant:
                    self.wage = applicant.salary_proposed
                else:
                    self.wage = 0
            else:
                self.wage = 0
        else:
            self.work_location_id = False

    def get_certificate_template(self):
        self.update_digital_sign()
        for rec in self:
            parent_record = rec
            if parent_record.contract_template:
                temp = parent_record.contract_template.letter_content
                letter_content_replace = parent_record.contract_template.letter_content
                if "$(name)" in letter_content_replace:
                    if not parent_record.name:
                        raise ValidationError("Certificate Name is empty")
                    letter_content_replace = str(letter_content_replace).replace("$(name)",
                                                                                 parent_record.name)
                if "$(employee_id)" in letter_content_replace:
                    if not rec.employee_id.name:
                        raise ValidationError("Employee Name is empty")
                    letter_content_replace = str(letter_content_replace).replace("$(employee_id)",
                                                                                 rec.employee_id.name)
                if "$(employee_signature)" in letter_content_replace:
                    if not rec.employee_id:
                        raise ValidationError("Employee Signature is empty")
                    if rec.employee_signature:
                        attachment = self.env['ir.attachment'].search(
                            [('res_model', '=', 'res.users'), ('res_id', '=', rec.employee_id.user_id.id),
                             ('res_field', '=', 'digital_signature')], limit=1)
                        sign_url = '''"/web/image/ir.attachment/''' + str(attachment.id) + '''/datas"'''
                        img_tag = '''<img src=''' + str(
                            sign_url) + ' ' + '''class="img img-fluid" border="1" width="200" height="150"/>'''

                        letter_content_replace = str(letter_content_replace).replace("$(employee_signature)",
                                                                                     str(img_tag))
                    else:
                        letter_content_replace = str(letter_content_replace).replace("$(employee_signature)", str())
                if "$(job_id)" in letter_content_replace:
                    if not parent_record.job_id.name:
                        raise ValidationError("Job is empty")
                    letter_content_replace = str(letter_content_replace).replace("$(job_id)",
                                                                                 rec.job_id.name)
                if "$(wage)" in letter_content_replace:
                    if not rec.wage:
                        letter_content_replace = str(letter_content_replace).replace("$(wage)","0")
                    letter_content_replace = str(letter_content_replace).replace("$(wage)",str(rec.wage))
                if "$(create_date)" in letter_content_replace:
                    if not rec.date_start:
                        raise ValidationError("Create Date is empty")
                    c_date = rec.create_date
                    c_date_format = c_date.strftime('%m/%d/%Y')
                    letter_content_replace = str(letter_content_replace).replace("$(create_date)",
                                                                                 str(c_date_format))

                if "$(start_date)" in letter_content_replace:
                    if not parent_record.start_date:
                        raise ValidationError("Start Date is empty")
                    s_date = parent_record.start_date
                    s_date_format = s_date.strftime('%m/%d/%Y')
                    letter_content_replace = str(letter_content_replace).replace("$(start_date)",
                                                                                 str(s_date_format))
                if "$(end_date)" in letter_content_replace:
                    if not parent_record.end_date:
                        raise ValidationError("End Date is empty")
                    e_date = parent_record.end_date
                    e_date_format = e_date.strftime('%m/%d/%Y')
                    letter_content_replace = str(letter_content_replace).replace("$(end_date)",
                                                                                 str(e_date_format))
                if "$(resource_calendar_id)" in letter_content_replace:
                    if parent_record.resource_calendar_id:
                        letter_content_replace = str(letter_content_replace).replace("$(resource_calendar_id)",
                                                                                     rec.resource_calendar_id.name)
                parent_record.contract_template.letter_content = letter_content_replace
                data = parent_record.contract_template.letter_content
                parent_record.contract_template.letter_content = temp
                return data

    def update_certificate(self):
        for rec in self:
            pdf = self.env.ref('equip3_hr_contract_extend.equip3_hr_contract_letter_mail')._render_qweb_pdf(rec.id)
            attachment = base64.b64encode(pdf[0])
            rec.certificate_attachment = attachment
            rec.certificate_attachment_fname = f"{'contract'}_{rec.employee_id.name}"

    # def action_contract_email_send(self):
    #     ir_model_data = self.env['ir.model.data']
    #     self.update_certificate()
    #     for rec in self:
    #         if not rec.contract_template:
    #             raise ValidationError("Sorry, you can't send a contract letter. Because the Contract Template field has not been filled")
    #         try:
    #             template_id = ir_model_data.get_object_reference(
    #                 'equip3_hr_contract_extend',
    #                 'email_template_contract_letter')[1]
    #         except ValueError:
    #             template_id = False
    #         ir_values = {
    #             'name': self.certificate_attachment_fname + '.pdf',
    #             'type': 'binary',
    #             'datas': self.certificate_attachment,
    #             'store_fname': self.certificate_attachment_fname,
    #             'mimetype': 'application/x-pdf',
    #         }
    #         data_id = self.env['ir.attachment'].create(ir_values)
    #         template = self.env['mail.template'].browse(template_id)
    #         template.attachment_ids = [(6, 0, [data_id.id])]
    #         template.send_mail(rec.id, force_send=True)
    #         template.attachment_ids = [(3, data_id.id)]
    #         break

    # If an employee is not mapped on “user” and doesn't have an email. this contract letter will send to applicant email
    def update_email_to_res_partner(self):
        for rec in self:
            if not rec.employee_id.user_id:
                if rec.employee_id.work_email:
                    applicant = self.env["hr.applicant"].search([("emp_id", "=", rec.employee_id.id), ("active", "=", True)], limit=1)
                    if applicant and applicant.partner_id:
                        applicant.partner_id.update({"email": rec.employee_id.work_email})
                        rec.partner_id = applicant.partner_id.id
                    elif not applicant:
                        part_rec = self.env["res.partner"].search([("name", "=", rec.employee_id.name), ("active", "=", True)], limit=1)
                        if part_rec:
                            part_rec.update({"email": rec.employee_id.work_email})
                            rec.partner_id = part_rec.id
                if not rec.employee_id.work_email:
                    applicant = self.env["hr.applicant"].search([("emp_id", "=", rec.employee_id.id), ("active", "=", True)], limit=1)
                    if applicant and applicant.partner_id and applicant.email_from:
                        applicant.partner_id.update({"email": applicant.email_from})
                        rec.partner_id = applicant.partner_id.id
            elif rec.employee_id.user_id:
                rec.partner_id = rec.employee_id.user_id.partner_id.id

    def action_contract_email_send(self):
        self.ensure_one()
        self.update_email_to_res_partner()
        if not self.partner_id:
            raise ValidationError(
                "Sorry, you can't send a contract letter because the employee is not mapped to related user")
        # if not self.wage:
        #     raise ValidationError(
        #         "Sorry, you can’t send the contract letter because the Wage is empty")
        # The following email sent to the Partner cannot be accepted because this is a private email address.
        self.type = self.partner_id.type
        if self.partner_id.type == 'private':
            self.partner_id.type = False
        ir_model_data = self.env['ir.model.data']
        self.update_certificate()
        if not self.contract_template:
            raise ValidationError(
                "Sorry, you can't send a contract letter. Because the Contract Template field has not been filled")
        try:
            template_id = ir_model_data.get_object_reference(
                'equip3_hr_contract_extend',
                'email_template_contract_letter')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ir_values = {
            'name': self.certificate_attachment_fname + '.pdf',
            'type': 'binary',
            'datas': self.certificate_attachment,
            'store_fname': self.certificate_attachment_fname,
            'mimetype': 'application/x-pdf',
        }
        data_id = self.env['ir.attachment'].create(ir_values)
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'hr.contract',
            'active_model': 'hr.contract',
            'default_res_id': self.id,
            'default_partner_ids': [self.partner_id.id],
            'active_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': " ",
            'default_attachment_ids': (data_id.id,),
            'force_email': True,
            'model_description': 'Contract Letter',
        }
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def certificate_mail(self):
        for rec in self:
            rec.update_certificate()
            ir_model_data = self.env['ir.model.data']
            ir_values = {
                'name': rec.certificate_attachment_fname + '.pdf',
                'type': 'binary',
                'datas': rec.certificate_attachment,
                'store_fname': rec.certificate_attachment_fname,
                'mimetype': 'application/x-pdf',
            }
            data_id = rec.env['ir.attachment'].create(ir_values)
            try:
                template_id = rec.email_template_id.id
            except ValueError:
                template_id = False
            ctx = rec._context.copy()
            ctx.update({
                'email_from': rec.env.user.email,
                'email_to': rec.partner_id.email,
            })
            template = rec.env['mail.template'].browse(template_id)
            template.attachment_ids = [(6, 0, [data_id.id])]
            template.with_context(ctx).send_mail(rec.id, force_send=True)
            template.attachment_ids = [(3, data_id.id)]

    # The following email sent to the Partner cannot be accepted because this is a private email address.
    # After Email sent reverse the Partner type to the Original
    def reverse_partner_type(self):
        for rec in self:
            if rec.type:
                rec.partner_id.type = rec.type

    # The following email sent to the Partner cannot be accepted because this is a private email address.
    # After Email sent reverse the Partner type to the Original
class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        super(MailComposer, self).action_send_mail()
        for rec in self:
            if rec.model == 'hr.contract' and rec.res_id:
                contract = self.env["hr.contract"].search([("id", "=", rec.res_id), ("active", "=", True)], limit=1)
                contract.reverse_partner_type()