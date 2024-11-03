from odoo import fields,api,models,_
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
import base64
import pytz
from ...equip3_general_features.models.email_wa_parameter import waParam

class HrOfferingrequest(models.Model):
    _name = 'hr.offering.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description="HR Offering Letter Request"
    _rec_name = 'sequence'

    def _default_requester(self):
        return self.env.user.employee_id

    name = fields.Char('Name')
    all_applicant = fields.Boolean('All Applicant')
    apply_to = fields.Selection(
        [('by_applicant', 'By Applicant'), ('by_department', 'By Department'), ('by_job', 'By Job Position')],
        string="Apply To", default='')
    applicant_ids = fields.Many2many('hr.applicant', string="Applicants")
    department_ids = fields.Many2many('hr.department', string="Departments")
    job_ids = fields.Many2many('hr.job', string="Job Positions")
    requester_id = fields.Many2one('hr.employee', string="Requester", default=_default_requester)
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='draft')
    approvers_ids = fields.Many2many('res.users', 'hr_offering_request_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', 'hr_offering_request_approved_user_rel', string='Approved by User')
    offering_line_ids = fields.One2many('hr.offering.request.line','offering_id', string="Offering Lines")
    offering_approval_ids = fields.One2many('hr.offering.request.approval','offering_id', string="Offering Approval Lines")
    approval_matrix_setting = fields.Boolean("Approval Matrix Setting")
    feedback_parent = fields.Text(string='Parent Feedback')
    is_requester = fields.Boolean(string="Is Requester", compute='_compute_is_requester')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    is_offering_letter_approval_matrix = fields.Boolean("Is Offering Letter Approval Matrix", compute='_compute_is_offering_letter_approval_matrix')
    state1 = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Submitted'), ('rejected', 'Rejected')],
        default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    sequence = fields.Char(string="Sequence", readonly=True, tracking=True)
    letter_number = fields.Integer(compute='_get_letter_number')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(HrOfferingrequest, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(HrOfferingrequest, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)



    
    @api.depends('offering_line_ids')
    def _get_letter_number(self):
        for data in self:
            if data.offering_line_ids and data.state == 'approved':
                data.letter_number = len(data.offering_line_ids.ids)
            else:
                data.letter_number = 0
    
    
    def action_get_offering_line(self):
        self.ensure_one()
        domain = [('id','in',[])]
        if self.state == 'approved':
            domain = [('id', 'in', self.offering_line_ids.ids)]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Offering Letter Request',
            'res_model': 'hr.offering.request.line',
            # 'search_view_id':search_view_id.id,
            'domain': domain,
            'view_mode': 'tree,form',
            'context':{'create':False,'edit':False,'delete':False}
            }
        # res = self.env['ir.actions.act_window']._for_xml_id('equip3_hr_recruitment_extend.hr_offering_letter_request_line_act_window')
        # res['domain'] = [('id', 'in', self.offering_line_ids.ids)]
        # # res['context'] = {'default_res_model': 'hr.expense', 'default_res_id': self.id}
        # return res

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('hr.offering.request')
        return super(HrOfferingrequest, self).create(vals)

    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_offering_letter_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.offering_letter_approval_matrix')
            rec.is_offering_letter_approval_matrix = setting


    @api.depends('requester_id')
    def _compute_is_requester(self):
        for rec in self:
            current_user = self.env.user
            if rec.requester_id.user_id == current_user:
                rec.is_requester = True
            else:
                rec.is_requester = False

    @api.onchange('requester_id')
    def _onchange_requester(self):
        for record in self:
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_recruitment_extend.offering_letter_approval_matrix')
            if setting:
                record.approval_matrix_setting = True
                if record.offering_approval_ids:
                    remove = []
                    for line in record.offering_approval_ids:
                        remove.append((2, line.id))
                    record.offering_approval_ids = remove
                approval_method = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_recruitment_extend.offering_letter_approval_method')
                if approval_method == 'employee_hierarchy':
                    record.offering_approval_ids = self.approval_by_hierarchy(record)
                    self.app_list_offering_emp_by_hierarchy()
                else:
                    self.approval_by_matrix(record)
    
    def approval_by_hierarchy(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(record,record.requester_id,data,approval_ids,seq)
        return line

    def get_manager(self, record, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.offering_letter_approval_level')
        if not setting_level:
            raise ValidationError("level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(setting_level):
            approval_ids.append(
                (0, 0, {'sequence': seq, 'approver_id': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(record, employee_manager['parent_id'], data, approval_ids, seq)
                break

        return approval_ids
    
    def app_list_offering_emp_by_hierarchy(self):
        for rec in self:
            app_list = []
            for line in rec.offering_approval_ids:
                app_list.append(line.approver_id.id)
            rec.approvers_ids = app_list
    
    def approval_by_matrix(self, record):
        app_list = []
        approval_matrix = self.env['hr.offering.approval.matrix'].search([('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: record.requester_id.id in line.employee_ids.ids)

        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_type == "specific_approver":
                    data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                  'approver_id': [(6, 0, line.approvers.ids)]}))
                    for approvers in line.approvers:
                        app_list.append(approvers.id)
                elif line.approver_type == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(record, record.requester_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                        app_list.append(approver)
            record.approvers_ids = app_list
            record.offering_approval_ids = data_approvers
        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.offering.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: record.requester_id.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_type == "specific_approver":
                        data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                      'approver_id': [(6, 0, line.approvers.ids)]}))
                        for approvers in line.approvers:
                            app_list.append(approvers.id)
                    elif line.approver_type == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(record, record.requester_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                            app_list.append(approver)
                record.approvers_ids = app_list
                record.offering_approval_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.offering.approval.matrix'].search(
                    [('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(lambda line: record.requester_id.department_id.id in line.deparment_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_type == "specific_approver":
                            data_approvers.append((0, 0,
                                                   {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                    'approver_id': [(6, 0, line.approvers.ids)]}))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                        elif line.approver_type == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(record, record.requester_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                                app_list.append(approver)
                    record.approvers_ids = app_list
                    record.offering_approval_ids = data_approvers
    
    def get_manager_hierarchy(self, record, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(record, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    @api.onchange('apply_to','applicant_ids')
    def _onchange_applicant_ids(self):
        applicants = []
        if self.apply_to == "by_applicant":
            offering_stage_id = self.env.ref('equip3_hr_recruitment_extend.offrering_letter').id
            applicant_obj = self.env['hr.applicant'].search([('stage_id','=',offering_stage_id),('user_id','=',self.env.user.id),('company_id','=',self.env.company.id)])
            if applicant_obj:
                 for app in applicant_obj:
                    applicants.append(app.id)
        return {
			'domain': {'applicant_ids': [('id', 'in', applicants)]},
		}
    
    @api.onchange('apply_to','department_ids')
    def _onchange_department_ids(self):
        departments = []
        if self.apply_to == "by_department":
            offering_stage_id = self.env.ref('equip3_hr_recruitment_extend.offrering_letter').id
            applicant_obj = self.env['hr.applicant'].search([('stage_id','=',offering_stage_id),('user_id','=',self.env.user.id),('company_id','=',self.env.company.id)])
            if applicant_obj:
                 for app in applicant_obj:
                    departments.append(app.department_id.id)
        return {
			'domain': {'department_ids': [('id', 'in', departments)]},
		}
    
    @api.onchange('apply_to','job_ids')
    def _onchange_job_ids(self):
        jobs = []
        if self.apply_to == "by_job":
            offering_stage_id = self.env.ref('equip3_hr_recruitment_extend.offrering_letter').id
            applicant_obj = self.env['hr.applicant'].search([('stage_id','=',offering_stage_id),('user_id','=',self.env.user.id),('company_id','=',self.env.company.id)])
            if applicant_obj:
                 for app in applicant_obj:
                    jobs.append(app.job_id.id)
        return {
			'domain': {'job_ids': [('id', 'in', jobs)]},
		}
                
    @api.onchange('all_applicant', 'apply_to', 'applicant_ids', 'department_ids', 'job_ids')
    def _onchange_apply_to(self):
        for rec in self:
            rec.offering_line_ids = [(5,0,0)]
            if rec.all_applicant or rec.apply_to or rec.applicant_ids or rec.department_ids or rec.job_ids:
                offering_stage_id = self.env.ref('equip3_hr_recruitment_extend.offrering_letter').id
                line_list = []
                if rec.all_applicant:
                    rec.apply_to = False
                    rec.applicant_ids = [(5,0,0)]
                    rec.department_ids = [(5,0,0)]
                    rec.job_ids = [(5,0,0)]
                    applicant_obj = self.env['hr.applicant'].search([('stage_id','=',offering_stage_id),('user_id','=',self.env.user.id)])
                    for app in applicant_obj:
                        line_list.append([0,0,{
                                            'applicant_id': app.id,
                                            'department_id': app.department_id.id,
                                            'job_id': app.job_id.id,
                                            'last_drawn_salary': app.last_drawn_salary,
                                            'salary_expected': app.salary_expected,
                                            'salary_proposed': app.salary_proposed
                                            }])
                elif rec.apply_to == "by_applicant":
                    rec.department_ids = [(5,0,0)]
                    rec.job_ids = [(5,0,0)]
                    if rec.applicant_ids:
                        applicant_obj = self.env['hr.applicant'].search([('id','in',rec.applicant_ids.ids)])
                        for app in applicant_obj:
                            line_list.append([0,0,{
                                                'applicant_id': app.id,
                                                'department_id': app.department_id.id,
                                                'job_id': app.job_id.id,
                                                'last_drawn_salary': app.last_drawn_salary,
                                                'salary_expected': app.salary_expected,
                                                'salary_proposed': app.salary_proposed
                                                }])
                rec.offering_line_ids = line_list

    def action_submit(self):
        setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.offering_letter_approval_matrix')
        for rec in self:
            if setting:
                rec.state = "submitted"
                for line in self.offering_approval_ids:
                    line.write({'approver_state': 'draft'})
                self.approver_mail()
                self.approver_wa_template()
            else:
                rec.state = "approved"
    
    def send_wa_offering(self):
        popup_msg = False
        for rec in self:
            for app_line in rec.offering_line_ids:
                app_line.applicant_id.salary_proposed = app_line.salary_proposed
                send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.send_by_wa')
                offering_stage = self.env.ref('equip3_hr_recruitment_extend.offrering_letter')
                pdf = self.env.ref('equip3_hr_recruitment_extend.hr_offering_letter_report')._render_qweb_pdf(app_line.id)
                wa_body = waParam()
                if send_by_wa:
                    offering_letter_template = offering_stage.offering_letter_template_id
                    if not offering_letter_template:
                        raise ValidationError("Offering Letter Template is empty in stages")
                    wa_template = offering_stage.offering_letter_template_id.wa_template_id
                    if not wa_template:
                        raise ValidationError("WhatsApp Template is empty in Offering Letter")
                    if wa_template:
                        wa_body.set_wa_string(wa_template.message,wa_template._name,template_id= wa_template)
                        wa_body.set_applicant_name(app_line.applicant_id.partner_name)
                        wa_body.set_company(app_line.applicant_id.job_id.company_id.name)
                        wa_body.set_job(app_line.applicant_id.job_id.name)
                        wa_sent = wa_body.send_wa(app_line.applicant_id.partner_mobile)
                        wa_body.send_wa_file(app_line.applicant_id.partner_mobile,pdf,"Offering Letter"+f"_{app_line.applicant_id.partner_name}")
                        if wa_sent:
                            popup_msg = True
        if popup_msg:
            return self.confirm_msg()
        
    def create_letter(self):
        for rec in self:
            for app_line in rec.offering_line_ids:
                app_line.applicant_id.salary_proposed = app_line.salary_proposed
                # send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
                offering_stage = self.env.ref('equip3_hr_recruitment_extend.offrering_letter')
                pdf = self.env.ref('equip3_hr_recruitment_extend.hr_offering_letter_report')._render_qweb_pdf(app_line.id)
                # if send_by_email:
                attachment = base64.b64encode(pdf[0])
                ir_values = {
                    'name': "Offering Letter"+f"_{app_line.applicant_id.partner_name}" + '.pdf',
                    'type': 'binary',
                    'res_model':'hr.offering.request.line',
                    'res_id':app_line.id,
                    'datas': attachment,
                    'store_fname': "Offering Letter"+f"_{app_line.applicant_id.partner_name}",
                    'mimetype': 'application/x-pdf',
                }
                data_id = self.env['ir.attachment'].create(ir_values)
                app_line.offering_letter_id = attachment
                app_line.uploaded_type = 'application/pdf'
                app_line.file_name = "Offering Letter"+f"_{app_line.applicant_id.partner_name}" + '.pdf'
        

    def send_email_offering(self):
        popup_msg = False
        for rec in self:
            for app_line in rec.offering_line_ids:
                app_line.applicant_id.salary_proposed = app_line.salary_proposed
                send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
                offering_stage = self.env.ref('equip3_hr_recruitment_extend.offrering_letter')
                pdf = self.env.ref('equip3_hr_recruitment_extend.hr_offering_letter_report')._render_qweb_pdf(app_line.id)
                if send_by_email:
                    attachment = base64.b64encode(pdf[0])
                    ir_values = {
                        'name': "Offering Letter"+f"_{app_line.applicant_id.partner_name}" + '.pdf',
                        'type': 'binary',
                        'datas': attachment,
                        'store_fname': "Offering Letter"+f"_{app_line.applicant_id.partner_name}",
                        'mimetype': 'application/x-pdf',
                    }
                    data_id = self.env['ir.attachment'].create(ir_values)
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': app_line.applicant_id.email_from,
                        'job': app_line.applicant_id.job_id.name,
                    }
                    offering_letter_template = offering_stage.offering_letter_template_id
                    if not offering_letter_template:
                        raise ValidationError("Offering Letter Template is empty in stages")
                    email_template = offering_stage.offering_letter_template_id.email_template_id
                    if not email_template:
                        raise ValidationError("Email Template is empty in Offering Letter")
                    email_template.attachment_ids = [(5, 0, 0)]
                    email_template.attachment_ids = [(6, 0, [data_id.id])]
                    email_sent = email_template.with_context(ctx).send_mail(app_line.applicant_id.id, force_send=True)
                    if email_sent:
                        popup_msg = True
        if popup_msg:
            return self.confirm_msg()

    def confirm_msg(self):
        # Show the wizard after the email/whatsapp is sent
        return {
            'name': 'Confirmation Message',
            'type': 'ir.actions.act_window',
            'res_model': 'send.email.popup.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_hr_recruitment_extend.view_send_email_popup_wizard_form').id,
            'target': 'new',
            'context': self.env.context,
        }

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_recruitment_extend', 'hr_offering_letter_request_menu')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_recruitment_extend', 'hr_offering_letter_request_act_window')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.offering.request&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def get_auto_follow_up_approver_wa_template(self, rec):
        wa_sender = waParam()
        template = self.env.ref('equip3_hr_recruitment_extend.wa_template_16')
        if template:
            string_test = str(template.message)
            if "${recruiter_name}" in string_test:
                string_test = string_test.replace("${recruiter_name}", rec.create_uid.name)
            if "${offering_letter_seq}" in string_test:
                string_test = string_test.replace("${offering_letter_seq}", rec.sequence)
            phone_num = str(rec.create_uid.mobile_phone)
            if "+" in phone_num:
                phone_num = int(phone_num.replace("+", ""))
            domain = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.url')
            token = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.secret_key')
            app_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid')
            channel_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id')
            name_space = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.name_space')
            template_name = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.template_name')
            wa_sender.set_wa_string(string_test, template._name, template_id=template, domain=domain, token=token,
                                    app_id=app_id, channel_id=channel_id, name_space=name_space,
                                    template_name=template_name)
            wa_sender.send_wa(phone_num)

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        is_auto_follow_up = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.auto_follow_recruitment')
        number_of_repititions = int(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.number_of_repetitions_recruitment'))
        is_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
        is_whatsapp = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.send_by_wa')
        recruitment_approved = self.search([('state', '=', 'approved')])
        if is_auto_follow_up:
            for rec in recruitment_approved:
                if rec.offering_line_ids and any(line.applicant_id.stage_replace_id.stage_id.name == 'Offering Letter' for line in rec.offering_line_ids):
                    try:
                        template_id = ir_model_data.get_object_reference('equip3_hr_recruitment_extend', 'mail_template_auto_follow_up_offering_process')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(rec)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': rec.create_uid.email,
                        'recruiter_name': rec.create_uid.name,
                        'offering_letter': rec.name,
                        'url': url,
                    })
                    if not rec.is_auto_follow_approver:
                        count = number_of_repititions - 1
                        query_statement = """UPDATE hr_offering_request set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, rec.id])
                        if is_email:
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)
                        if is_whatsapp:
                            self.get_auto_follow_up_approver_wa_template(rec)
                    elif rec.is_auto_follow_approver:
                        if rec.repetition_follow_count > 0:
                            count = rec.repetition_follow_count - 1
                            query_statement = """UPDATE hr_offering_request set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, rec.id])
                            if is_email:
                                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)
                            if is_whatsapp:
                                self.get_auto_follow_up_approver_wa_template(rec)


    @api.depends('offering_approval_ids')
    def _compute_can_approve(self):
        for rec in self:
            current_user = self.env.user
            if rec.approval_matrix_setting:
                matrix_line = sorted(rec.offering_approval_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(rec.offering_approval_ids)
                if app < a:
                    for line in rec.offering_approval_ids[app]:
                        if current_user in line.approver_id and current_user not in line.approver_confirm:
                            rec.is_approver = True
                        else:
                            rec.is_approver = False
                else:
                    rec.is_approver = False
            else:
                if rec.requester_id.user_id == current_user:
                    rec.is_approver = True
                else:
                    rec.is_approver = False

    def wizard_approve(self):
        for rec in self:
            if rec.approval_matrix_setting:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.offering.request.approval.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': "Confirmation Message",
                    'context':{'is_approve':True},
                    'target': 'new',
                }
            else:
                rec.state = "approved"
    
    def action_approve(self):
        for rec in self:
            for line_item in rec.offering_approval_ids:
                if line_item.approver_state == 'draft' or line_item.approver_state == 'pending':
                    for user in line_item.approver_id:
                        if self.env.user.id in user.ids:
                            sequence_matrix = [data.sequence for data in rec.offering_approval_ids]
                            sequence_approval = [data.sequence for data in rec.offering_approval_ids.filtered(
                                lambda line: len(line.approver_confirm) != line.minimum_approver)]
                            max_seq = max(sequence_matrix)
                            min_seq = min(sequence_approval)
                            approval = line_item.filtered(
                                lambda line: self.env.user.id in line.approver_id.ids and len(
                                    line.approver_confirm) != line.minimum_approver and line.sequence == min_seq)
                            if approval:
                                rec.approved_user_ids = [(4, self.env.user.id)]
                                approval.approver_confirm = [(4, self.env.user.id)]
                                user_tz = self.env.user.tz or pytz.utc
                                local = pytz.timezone(user_tz)
                                timestamp = datetime.strftime(datetime.now().astimezone(local), '%d/%m/%Y %H:%M:%S')
                                if len(approval.approver_confirm) == approval.minimum_approver:
                                    approval.approver_state = "approved"
                                    approval.is_approve = True
                                else:
                                    approval.approver_state = "pending"

                                if not approval.approval_status:
                                    approval.approval_status = f"{self.env.user.name}:Approved"
                                    if rec.feedback_parent:
                                        approval.feedback = f"{self.env.user.name}:{rec.feedback_parent or ''}"
                                    else:
                                        approval.feedback = f"{''}"
                                    approval.timestamp = f"{self.env.user.name}:{timestamp}"
                                else:
                                    string_approval = []
                                    string_approval.append(approval.approval_status)
                                    string_approval.append(f"{self.env.user.name}:Approved")
                                    approval.approval_status = "\n".join(string_approval)

                                    if rec.feedback_parent:
                                        feedback = f"{self.env.user.name}:{rec.feedback_parent or ''}"
                                    else:
                                        feedback = f"{''}"
                                    feedback_list = [approval.feedback, feedback]
                                    final_feedback = "\n".join(feedback_list)
                                    approval.feedback = f"{final_feedback}"

                                    string_timestamp = [approval.timestamp, f"{self.env.user.name}:{timestamp}"]
                                    final_timestamp = "\n".join(string_timestamp)
                                    approval.timestamp = f"{final_timestamp}"
                            if len(approval.approver_confirm) == approval.minimum_approver and not approval.sequence == max_seq:
                                self.approver_wa_template()
                                self.approver_mail()
                                # self.create_letter()
                                
            matrix_line = sorted(rec.offering_approval_ids.filtered(lambda r: r.is_approve == False))
            if len(matrix_line) == 0:
                rec.state = "approved"
                self.approved_mail()
                self.approved_wa_template()
                self.create_letter()
    
    def wizard_reject(self):
        for rec in self:
            if rec.approval_matrix_setting:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.offering.request.approval.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': "Confirmation Message",
                    'context':{'is_approve':False},
                    'target': 'new',
                }
            else:
                rec.state = "rejected"
    
    def action_reject(self):
        for rec in self:
            for line_item in rec.offering_approval_ids:
                if line_item.approver_state == 'draft' or line_item.approver_state == 'pending':
                    for user in line_item.approver_id:
                        if self.env.user.id in user.ids:
                            line_item.approver_state = "refuse"
                            user_tz = self.env.user.tz or pytz.utc
                            local = pytz.timezone(user_tz)
                            timestamp = datetime.strftime(datetime.now().astimezone(local), '%d/%m/%Y %H:%M:%S')
                            if not line_item.approval_status:
                                line_item.approval_status = f"{self.env.user.name}:Refused"
                                if rec.feedback_parent:
                                    line_item.feedback = f"{self.env.user.name}:{rec.feedback_parent or ''}"
                                else:
                                    line_item.feedback = f"{''}"
                                line_item.timestamp = f"{self.env.user.name}:{timestamp}"
                            else:
                                string_approval = []
                                string_approval.append(line_item.approval_status)
                                string_approval.append(f"{self.env.user.name}:Refused")
                                line_item.approval_status = "\n".join(string_approval)

                                if rec.feedback_parent:
                                    feedback = f"{self.env.user.name}:{rec.feedback_parent or ''}"
                                else:
                                    feedback = f"{''}"
                                feedback_list = [line_item.feedback, feedback]
                                final_feedback = "\n".join(feedback_list)
                                line_item.feedback = f"{final_feedback}"

                                string_timestamp = [line_item.timestamp, f"{self.env.user.name}:{timestamp}"]
                                final_timestamp = "\n".join(string_timestamp)
                                line_item.timestamp = f"{final_timestamp}"
            rec.state = "rejected"
            self.reject_mail()
            self.rejected_wa_template()
    
    @api.constrains('offering_line_ids')
    def _check_salary_proposed(self):
        for rec in self:
            for line in rec.offering_line_ids:
                if line.salary_proposed <= 0:
                    raise ValidationError(_("""You must filled Salary Proposed."""))

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        is_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
        if is_email:
            for rec in self:
                if rec.offering_approval_ids:
                    matrix_line = sorted(rec.offering_approval_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.offering_approval_ids[len(matrix_line)]
                    for user in approver.approver_id:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_recruitment_extend',
                                'email_template_application_for_offering_letter_request_approval')[1]
                        except ValueError:
                            template_id = False
                            
                        ctx = self._context.copy()
                        url = self.get_url(rec)
                        ctx.update({
                            'email_from': self.env.user.company_id.email,
                            'email_to': user.email,
                            'approver_name': user.name,
                            'url': url,
                        })
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,force_send=True)
                    break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        is_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
        if is_email:
            for rec in self:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_recruitment_extend',
                        'email_template_approval_offering_letter_request')[1]
                except ValueError:
                    template_id = False
                ctx = self._context.copy()
                url = self.get_url(rec)
                ctx.update({
                    'email_from': self.env.user.company_id.email,
                    'email_to': rec.create_uid.email,
                    'url': url,
                })
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id, force_send=True)
                break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        is_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
        if is_email:
            for rec in self:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_recruitment_extend',
                        'email_template_rejection_of_offering_letter_request')[1]
                except ValueError:
                    template_id = False
                ctx = self._context.copy()
                url = self.get_url(rec)
                ctx.update({
                    'email_from': self.env.user.company_id.email,
                    'email_to': rec.create_uid.email,
                    'url': url,
                })
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)
                break

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.send_by_wa')
        if send_by_wa:
            template = self.env.ref('equip3_hr_recruitment_extend.wa_template_19')
            wa_sender = waParam()
            if template:
                if self.offering_approval_ids:
                    matrix_line = sorted(self.offering_approval_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.offering_approval_ids[len(matrix_line)]
                    for user in approver.approver_id:
                        string_test = str(template.message)
                        if "${recruiter_name}" in string_test:
                            string_test = string_test.replace("${recruiter_name}", self.create_uid.name)
                        if "${offering_letter_seq}" in string_test:
                            string_test = string_test.replace("${offering_letter_seq}", self.sequence)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        phone_num = str(user.mobile_phone)
                        if "+" in phone_num:
                            phone_num = int(phone_num.replace("+", ""))
                        wa_sender.set_wa_string(string_test, template._name, template_id=template)
                        wa_sender.send_wa(phone_num)

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.send_by_wa')
        if send_by_wa:
            wa_sender = waParam()
            template = self.env.ref('equip3_hr_recruitment_extend.wa_template_17')
            if template:
                string_test = str(template.message)
                if "${recruiter_name}" in string_test:
                    string_test = string_test.replace("${recruiter_name}", self.create_uid.name)
                if "${offering_letter_seq}" in string_test:
                    string_test = string_test.replace("${offering_letter_seq}", self.sequence)
                phone_num = str(self.create_uid.mobile_phone)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))
                wa_sender.set_wa_string(string_test, template._name, template_id=template)
                wa_sender.send_wa(phone_num)

    def rejected_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.send_by_wa')
        if send_by_wa:
            wa_sender = waParam()
            template = self.env.ref('equip3_hr_recruitment_extend.wa_template_18')
            if template:
                string_test = str(template.message)
                if "${recruiter_name}" in string_test:
                    string_test = string_test.replace("${recruiter_name}", self.create_uid.name)
                if "${offering_letter_seq}" in string_test:
                    string_test = string_test.replace("${offering_letter_seq}", self.sequence)
                phone_num = str(self.create_uid.mobile_phone)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))
                wa_sender.set_wa_string(string_test, template._name, template_id=template)
                wa_sender.send_wa(phone_num)

class HrOfferingrequestLine(models.Model):
    _name = 'hr.offering.request.line'
    _description="HR Offering Letter Request Line"

    offering_id = fields.Many2one('hr.offering.request', string="Offering Request")
    applicant_id = fields.Many2one('hr.applicant', string="Applicant Name")
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string="Job Position")
    last_drawn_salary = fields.Float('Last Drawn Salary')
    salary_expected = fields.Float('Salary Expected')
    salary_proposed = fields.Float('Salary Proposed')
    offering_letter_id = fields.Binary()
    file_name = fields.Char()
    uploaded_type = fields.Char()
    
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'hr.offering.request.line'), ('res_id', '=', self.id)]
        # res['context'] = {'default_res_model': 'hr.expense', 'default_res_id': self.id}
        return res

    @api.onchange('applicant_id')
    def _onchange_applicant(self):
        applicants = []
        for rec in self:
            if rec.applicant_id:
                rec.department_id = rec.applicant_id.department_id
                rec.job_id = rec.applicant_id.job_id
                rec.last_drawn_salary = rec.applicant_id.last_drawn_salary
                rec.salary_expected = rec.applicant_id.salary_expected
                rec.salary_proposed = rec.applicant_id.salary_proposed
        
            offering_stage_id = self.env.ref('equip3_hr_recruitment_extend.offrering_letter').id
            if rec.offering_id.apply_to == "by_department":
                # if rec.offering_id.department_ids.ids:
                applicant_obj = self.env['hr.applicant'].search([('stage_id','=',offering_stage_id),('user_id','=',self.env.user.id),('department_id','in',rec.offering_id.department_ids.ids)])
                for app in applicant_obj:
                    applicants.append(app.id)
            elif rec.offering_id.apply_to == "by_job":
                # if rec.offering_id.job_ids.ids:
                applicant_obj = self.env['hr.applicant'].search([('stage_id','=',offering_stage_id),('user_id','=',self.env.user.id),('job_id','in',rec.offering_id.job_ids.ids)])
                for app in applicant_obj:
                    applicants.append(app.id)
        return {
			'domain': {'applicant_id': [('id', 'in', applicants)]},
		}

    def print_offering_letter(self):
        for rec in self:
            if rec.applicant_id.availability:
                start_working_date = datetime.strptime(str(rec.applicant_id.availability), "%Y-%m-%d")
                start_working_string = datetime(start_working_date.year, start_working_date.month,
                                             start_working_date.day).strftime("%B %d, %Y")
            current_date = date.today()
            current_date_string = datetime(current_date.year, current_date.month,
                                            current_date.day).strftime("%d/%m/%Y")
            offering_stage = self.env.ref('equip3_hr_recruitment_extend.offrering_letter')
            if not offering_stage.offering_letter_template_id:
                raise ValidationError("Letter not set in Offering Letter Stages")
            temp = offering_stage.offering_letter_template_id.letter_content
            letter_content_replace = offering_stage.offering_letter_template_id.letter_content
            if "${applicant_name}" in letter_content_replace:
                if not rec.applicant_id.partner_name:
                    raise ValidationError("Applicant Name is empty")
                letter_content_replace = str(letter_content_replace).replace("${applicant_name}", rec.applicant_id.partner_name)
            if "${job_position}" in letter_content_replace:
                if not rec.applicant_id.job_id:
                    raise ValidationError("Applied Job is empty")
                letter_content_replace = str(letter_content_replace).replace("${job_position}", rec.applicant_id.job_id.name)
            if "${proposed_salary}" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("${proposed_salary}", str(rec.applicant_id.salary_proposed))
            if "${start_working_date}" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("${start_working_date}", start_working_string)
            if "${current_date}" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("${current_date}", current_date_string)

            offering_stage.offering_letter_template_id.letter_content = letter_content_replace
            data = offering_stage.offering_letter_template_id.letter_content
            offering_stage.offering_letter_template_id.letter_content = temp
            return data

class HrOfferingrequestApproval(models.Model):
    _name = 'hr.offering.request.approval'
    _description = "Hr Offering Request Approval"

    offering_id = fields.Many2one('hr.offering.request', string="Offering Request")
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    approver_id = fields.Many2many('res.users', string="Approvers")
    approver_confirm = fields.Many2many('res.users', 'hr_offering_request_user_approve_ids', 'user_id', string="Approvers confirm")
    approval_status = fields.Text('Approval Status')
    timestamp = fields.Text('Timestamp')
    feedback = fields.Text('Feedback')
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    #parent status
    state = fields.Selection(related='offering_id.state', string='Parent Status')

    @api.depends('offering_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.offering_id.offering_approval_ids:
            sl = sl + 1
            line.sequence = sl