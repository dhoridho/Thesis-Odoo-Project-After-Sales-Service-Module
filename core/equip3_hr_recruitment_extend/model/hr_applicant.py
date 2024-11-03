
import base64
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, SUPERUSER_ID,_
from odoo.exceptions import ValidationError
from odoo.exceptions import Warning
from lxml import etree
from odoo.http import request
import werkzeug,requests
import mimetypes
from openerp import http
from odoo.tools import format_datetime, format_date, is_html_empty
from odoo.addons.hr_recruitment.models.hr_recruitment import Applicant
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam



headers = {'content-type': 'application/json'}
class HrApplicant(models.Model):
    _inherit='hr.applicant'

    applicant_question_answer=fields.One2many('applicant.answer','applicant_id')
    applicant_question_answer_spesific=fields.One2many('applicant.answer','applicant_specific_id')
    stage_before_replace_id = fields.Many2one('job.stage.line', 'Stage Before')
    stage_replace_id = fields.Many2one('job.stage.line', 'Stage',compute='compute_stage_replace_id', store=True, tracking=True)
    shadow_stage_replace_id = fields.Many2one('job.stage.line', 'Stage')
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage',domain=[])
    stage_domain_ids = fields.Many2many('hr.recruitment.stage',compute='_compute_stage_domain_ids')
    stage_replace_domain_ids = fields.Many2many('job.stage.line',compute='_compute_stage_domain_ids')
    aplicant_create_date = fields.Date(default=datetime.now())
    file_cv = fields.Binary("CV")
    cv_name = fields.Char("CV", compute='_compute_file_name', default="", store=True)
    uploaded_cv_type = fields.Char("File Type",)
    cv_type_from_job_portal = fields.Char("File Type from Portal")
    response_id = fields.Many2one('survey.user_input', "Response", ondelete="set null")
    previous_score = fields.Float()
    past_experience_ids = fields.One2many('hr.applicant.past.experience','applicant_id',string="Past Experience")
    wa_url  = fields.Char(compute='_get_wa_url')
    wa_url_second  = fields.Char(compute='_get_wa_url_second')
    card_id_number = fields.Char()
    applicant_id = fields.Char("Applicant's ID")
    identification_no = fields.Char('Identification No')
    is_hide_assign = fields.Boolean()
    is_hide_pass_stage = fields.Boolean()
    is_hide_wa = fields.Boolean(compute='_is_hide_wa')
    is_hide_pass_next = fields.Boolean(compute='_is_hide_pass_next',default=True)
    apply_pass_stage = fields.Many2many('res.users')
    gender = fields.Selection([('male','Male'),('female','Female')],string="Gender")
    date_of_birth = fields.Date(string="Date Of Birth")
    address = fields.Text()
    marital_status = fields.Many2one('employee.marital.status')
    religion = fields.Many2one('employee.religion')
    birth_years = fields.Integer(string="Years of Service", compute='compute_birth_year', compute_sudo=True)
    birth_months = fields.Integer(compute='compute_birth_year', compute_sudo=True)
    birth_days = fields.Integer(compute='compute_birth_year', compute_sudo=True)
    birth_year = fields.Char(string=' ', default='-year(s) -')
    birth_month = fields.Char(string=' ', default='month(s) -')
    birth_day = fields.Char(string=' ', default='day(s)')
    age = fields.Integer('Age', compute='compute_birth_year', store=True)
    participations_count = fields.Integer(compute="_get_participations_count")
    last_drawn_salary = fields.Float()
    is_auto_follow =  fields.Boolean()
    repetion_count = fields.Integer()
    in_college = fields.Boolean()
    employee_skill_ids = fields.One2many("hr.applicant.skill",'applicant_id',"Employee Skill")
    is_interview = fields.Boolean()
    interview_id = fields.Many2one('survey.user_input')
    refuse_is_sent = fields.Boolean()
    quadran_line_ids = fields.One2many("quadrant.score.line", "applicant_id")
    category_id = fields.Many2one("quadrant.category", string="Category", compute="compute_quadrant_category", store=True)
    is_invite =  fields.Boolean(default=False)
    is_reminder_invite =  fields.Boolean(default=False)
    reminder_schedule_count = fields.Integer()
    working_experience = fields.Integer(compute='_compute_total_working_experience_years', string='Total Working Experience',store=True)
    working_experience_months = fields.Integer(compute='_compute_total_working_experience_years', compute_sudo=True)
    working_experience_days = fields.Integer(compute='_compute_total_working_experience_years', compute_sudo=True)
    working_experience_year = fields.Char(string=' ', default='-year(s) -')
    working_experience_month = fields.Char(string=' ', default='month(s) -')
    working_experience_day = fields.Char(string=' ', default='day(s)')
    job_id = fields.Many2one('hr.job', required=True)
    past_experience_year = fields.Float('Past Experience', compute='_compute_past_experience_year', store=True)
    is_hide_blacklist = fields.Boolean(default=False)
    is_blacklist = fields.Boolean(default=False)
    is_blacklist_active = fields.Boolean(compute='_compute_is_blacklist_active')
    is_hide_remove_blacklist = fields.Boolean(default=True)
    blacklist_reason_description_id = fields.Many2one('hr.applicant.blacklist.reason.description')
    work_location_id  = fields.Many2one('work.location.object',related='job_id.custom_work_location_id',store=True)
    outsource_id = fields.Many2one('hr.recruitment.outsource.master', string="Outsource")
    is_hire = fields.Boolean(default=False)
    

    @api.depends('job_id')
    def _compute_is_blacklist_active(self):
        for data in self:
            if data.job_id:
                setting = self.env['hr.config.settings'].sudo().search([],limit=1)
                data.is_blacklist_active = setting.applicant_blacklist
            else:
                data.is_blacklist_active = False
    
    def get_blacklist_reason(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Blacklist Reason',
            'res_model': 'hr.applicant.blacklist.reason.description',
            # 'view_type': 'form',
            'view_mode': 'form',
            'target':'current',
            'res_id': self.blacklist_reason_description_id.id,
            'context':{'create':False,'edit':False,'delete':False},
            
        }
    
    def blacklist_applicant(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Blacklist Reason',
            'res_model': 'blacklist.wizard',
            # 'view_type': 'form',
            'view_mode': 'form',
            'target':'new',
            'domain': [],
            'context':{'default_applicant_id':self.id},
            
        }
                
    def remove_blacklist(self):
        for data in self:
            data.with_context({'bypass_blacklist':True}).write({
                'is_blacklist':False,
                'is_hide_blacklist':False,
                'is_hide_remove_blacklist':True,
                'blacklist_reason_description_id':False
                })
        
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(HrApplicant, self).fields_get(allfields, attributes)
        # Modify the field attributes as needed
        hide = ['past_experience_ids', 'working_experience']
        for field in hide:
            if field in res:
                res[field]['searchable'] = False
        return res

    def hire_applicant(self):
        for rec in self:
            stage_replace_id = self.env['job.stage.line'].search(
                [('job_id', '=', rec.job_id.id), ('is_final_stage', '=', True)], limit=1)
            if stage_replace_id:
                final_stage = self.env['hr.recruitment.stage'].search([('id','=',stage_replace_id.stage_id.id)], limit=1)
                rec.stage_id = final_stage.id if final_stage else False
                rec.is_hire = True
                rec.stage_replace_id = stage_replace_id.id
                rec.shadow_stage_replace_id = stage_replace_id.id

    @api.depends('past_experience_ids')
    def _compute_total_working_experience_years(self):
        for applicant in self:
            total_years = 0
            total_months = 0
            total_days = 0
            for experience in applicant.past_experience_ids:
                start_date = experience.start_date
                end_date = experience.end_date

                if experience.is_currently_work_here:
                    end_date = datetime.now().date()

                if start_date and end_date:
                    delta = relativedelta(end_date, start_date)
                    total_years += delta.years
                    total_months += delta.months
                    total_days += delta.days

            total_months += total_years * 12
            years = total_months // 12
            months, days = divmod(total_days, 30)
            total_months += months
            days -= months * 30
            years = total_months // 12
            months = total_months % 12

            applicant.working_experience = years
            applicant.working_experience_months = months
            applicant.working_experience_days = days


    @api.depends('working_experience', 'working_experience_months')
    def _compute_past_experience_year(self):
        for applicant in self:
            past_experience_year = False
            if applicant.working_experience or applicant.working_experience_months:
                total_years = applicant.working_experience
                total_months = applicant.working_experience_months
                if total_months >= 12:
                    total_years += total_months // 12
                    total_months %= 12
                if total_months % 10 == 0:
                    past_experience_year = f'{total_years}.{total_months // 10}'
                else:
                    past_experience_year = f'{total_years}.{total_months}'
            applicant.past_experience_year = float(past_experience_year)

    def get_link_template_stage_id(self):
        url = '/web'
        if self.stage_replace_id.survey_id:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            access_token = self.stage_replace_id.survey_id.access_token
            url = self.stage_replace_id.survey_id.get_start_url()+f"?surveyId={self.stage_replace_id.survey_id.id}&applicantId={self.id}&jobPosition={self.job_id.id}&survey_id={self.stage_replace_id.survey_id.id}"
            if self.stage_replace_id.survey_id.state == 'draft':
                self.stage_replace_id.survey_id.action_open()
            url = werkzeug.urls.url_join(base_url, url) if self.stage_replace_id.survey_id else False
        return url
    
    
    def _track_template(self, changes):
        res = super(Applicant, self)._track_template(changes)
        
        applicant = self[0]
        if 'stage_id' in changes and applicant.stage_id.template_id and applicant.active and not applicant.stage_replace_id.survey_id.is_manual_test:   
            res['stage_id'] = (applicant.stage_id.sudo().template_id, {
                'auto_delete_message': False,
                'subtype_id': self.env['ir.model.data'].sudo().xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
        return res
    
    
        
    def send_refuse_mail(self):
        context = EmailParam()
        my_context = self.env.context = dict(self.env.context)
        refuse_template = self.stage_id.refuse_template_id
        cron_id = self.env.ref('equip3_hr_recruitment_extend.send_email_applicant_refuse')
        cron_refuse = self.env['ir.cron'].search([('id','=',cron_id.id)])
        if not cron_refuse.active or not cron_refuse:
            if refuse_template:
                self.write({'refuse_is_sent': True})
                context.set_email(self.email_from)
                my_context.update(context.get_context())
                refuse_template.send_mail(self.id, force_send=True)
                refuse_template.with_context(my_context)
    
        
        
    
    @api.model
    def get_all_quadrant_score(self,domain=[]):
        dataresult = {}
        result = []
        datas = self.env['hr.applicant'].search(domain)
        for data in datas:
            if not data.partner_name or not data.category_id.name:
                continue
            line = []
            for data_line in data.quadran_line_ids:
                if data_line.name:
                    text_line = (data_line.name or '-')+' Index : '+ str(data_line.index)
                    line.append(text_line)
            if not line:
                continue
            if dataresult.get(data.category_id.name):
                dataresult[data.category_id.name] += 1
            else:
                dataresult[data.category_id.name] = 1
            result.append({
                'id':data.id,
                'name':data.partner_name,
                'category_name':data.category_id.name,
                'line':line
            })
        dataresult['result'] = result
        for check in dataresult:
            if check != 'result':
                if dataresult[check] <= 6:
                    dataresult[check] = 1
                elif dataresult[check] >= 36:
                    dataresult[check] = 6
                else:
                    dataresult[check] = round(float(dataresult[check]) / 6,0)
        return dataresult
    
    
    
    @api.depends('quadran_line_ids.index')
    def compute_quadrant_category(self):
        for res in self:
            skills_index = 0
            personality_index = 0
            if res.quadran_line_ids:
                for line in res.quadran_line_ids:
                    if line.name == "Skills":
                        skills_index += line.index
                    elif line.name == "Personality":
                        personality_index += line.index
            quadrant_category = self.env['quadrant.category'].sudo().search(
                [('skill_score_from', '<=', skills_index),
                ('skill_score_to', '>=', skills_index),
                ('personality_score_from', '<=', personality_index),
                ('personality_score_to', '>=', personality_index)], limit=1)
            if quadrant_category:
                res.category_id = quadrant_category.id
            else:
                res.category_id = False
    
    
    
    def action_makeMeeting(self):
        data_ids = []
        self.env.cr.execute("""SELECT b.id from applicant_schedulling_meeting_result_confirmed a INNER JOIN applicant_schedulling_meeting_result b on a.parent_id = b.id WHERE a.applicant_id = %s""" % self.id)
        interview = self.env.cr.dictfetchall()
        if interview:     
            data_ids.extend(rec['id'] for rec in interview)
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interview Calendar'),
            'res_model': 'applicant.schedulling.meeting.result',
            'view_mode': 'calendar,tree',
            'domain': [('id','in',data_ids)],
            'context':{}
          
        }
        
    def _compute_meeting_count(self):
        meeting_count = 0
        data_ids = []
        for line in self:
            interview = self.env['applicant.schedulling.meeting.result.confirmed'].search([('applicant_id','=',line.id)])
            if interview:     
                data_ids.extend(record.id for record in interview)
                meeting_count = len(data_ids)
            line.meeting_count = meeting_count


    def action_print_interview(self):
        return {
                    'res_id': self.interview_id.id,
                    'name': 'Interview Result',
                    'res_model': 'survey.user_input',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'context': "{'create': False, 'edit': False}",
                }
    
    
    
    def action_start_survey(self):
        self.ensure_one()
        return self.action_start_survey_interview(self.stage_replace_id.interview_id)
    
    
    def action_start_survey_interview(self,survey):
        """ Open the website page with the survey form """
        self.ensure_one()
        survey_url = survey.get_start_url()+f"?surveyId={survey.id}&applicantId={self.id}&jobPosition={self.job_id.id}"
        return {
            'type': 'ir.actions.act_url',
            'name': "Start Survey",
            'target': 'self',
            'url': survey_url,
        }
    
    
    
    
    def invitation_interview(self):
        for record in self:
            if not record.is_invite:
                template = self.env.ref('equip3_hr_recruitment_extend.interview_template_applicant_extend', raise_if_not_found=False)
                template.send_mail(record.id, force_send=True)
                
    def reminder_send_wa(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        wa_sender = waParam()
        template = self.stage_id.wa_template_id
        if template:
            # if template:
            #     special_var =[{'variable':'{link_choose_schedule}',
            #     'value':f"{base_url}/interview/invite/schedule?name={self.partner_name}&email={self.email_from}&phone={self.partner_mobile}&applicant_id={self.id}"},
                            
            #                 ]
            #     wa_sender.set_special_variable(special_var)
            #     wa_sender.send_wa_qiscuss(template.message_line_ids,self,template)
            wa_sender.set_wa_string(template.message,template._name, template,self.env['ir.config_parameter'].sudo().get_param('chat.api.url'),self.env['ir.config_parameter'].sudo().get_param('chat.api.token'))
            wa_sender.set_applicant_name(self.partner_name or '')
            wa_sender.set_job(self.job_id.name)
            wa_sender.set_company(self.job_id.company_id.name)
            wa_sender.set_link_schedule(f"{base_url}/interview/invite/schedule?name={self.partner_name}&email={self.email_from}&phone={self.partner_mobile}&applicant_id={self.id}")
            wa_sender.send_wa(self.partner_mobile)
            
                
    def reminder_invitation_interview(self,repetion):
        for record in self:
            applicany_apply = self.env['applicant.schedulling.meeting.result.confirmed'].search([('applicant_id','=',record.id)])
            if not record.is_reminder_invite and not applicany_apply:
                template = self.stage_id.email_template_id
                if template:
                    template.send_mail(record.id, force_send=True)
                record.is_reminder_invite = True
                self.reminder_send_wa()
                record.reminder_schedule_count = repetion
            if record.is_reminder_invite and not applicany_apply:
                if record.reminder_schedule_count > 0:
                    template = self.env.ref('equip3_hr_recruitment_extend.interview_template_applicant_reminder_extend', raise_if_not_found=False)
                    template.send_mail(record.id, force_send=True)
                    record.reminder_schedule_count = record.reminder_schedule_count - 1
                    self.reminder_send_wa()
        
    
    def re_do_current_test(self):
        for record in self:
            template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)
            survey_latest = self.env['survey.user_input'].search([('applicant_id','=',record.id)],order='id desc',limit=1)
            my_context = self.env.context = dict(self.env.context)
            context = EmailParam()
            wa_sender = waParam()
            if survey_latest:
                survey_latest.is_use = False
                survey=self.env['survey.invite'].create({'survey_id':survey_latest.survey_id.id,'emails':str(self.email_from),'template_id':template.id})
                send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email') 
                survey_url = survey.survey_start_url+f"?surveyId={survey_latest.survey_id.id}&applicantId={record.id}&jobPosition={record.job_id.id}"
                if send_by_email:
                    context.set_email(record.email_from)
                    context.set_name(record.partner_name)
                    context.set_url_test(survey_url)
                    context.set_title(survey_latest.survey_id.title)
                    context.set_company_id(self.job_id.company_id.name)
                    context.set_work_location(self.job_id.custom_work_location_id.name)
                    template = self.env.ref('equip3_hr_recruitment_extend.mail_template_invite_test')
                    my_context.update(context.get_context())
                    template.send_mail(record.id, force_send=True)
                    template.with_context(my_context)
                send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.send_by_wa')
                if send_by_wa:
                    template = self.env.ref('equip3_hr_recruitment_extend.wa_template_1')
                    if template:
                        # special_var =[{'variable':'{survey_name}',
                        # 'value':survey_latest.survey_id.title if survey_latest else ''},
                        # {'variable':'{survey_url}',
                        # 'value':survey_url if survey_url else ''},
                        # {'variable':'{stage_before_technical}'
                        #  }]
                        # wa_sender.set_special_variable(special_var)
                        # wa_sender.send_wa_qiscuss(template.message_line_ids,self,template)
                        wa_sender.set_wa_string(template.message,template._name,template_id=template)
                        wa_sender.set_applicant_name(self.partner_name)
                        wa_sender.set_survey_url(survey_url)
                        wa_sender.set_survey_name(survey_latest.survey_id.title)
                        wa_sender.send_wa(self.partner_mobile)

    def open_new_tab_record(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        return {
            'name': 'Applicant',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': '_blank',
            'url': f"{base_url}/open_new_applicant/{self.env.context.get('active_id')}"
       }

    @api.depends('date_of_birth')
    def compute_birth_year(self):
        for record in self:
            if record.date_of_birth:
                current_day = date.today()
                d1 = record.date_of_birth
                d2 = current_day
                record.age = ((d2 - d1).days) / 365
                record.birth_years = ((d2 - d1).days) / 365
                d3 = record.date_of_birth + relativedelta(years=+record.birth_years)
                record.birth_months = ((d2 - d3).days) / 30
                d4 = d3 + relativedelta(months=+record.birth_months)
                record.birth_days = ((d2 - d4).days)
            else:
                record.age = 0
                record.birth_years = 0
                record.birth_months = 0
                record.birth_days = 0
    
    
    
    
    def _is_hide_pass_next(self):
        if self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_user') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            self.is_hide_pass_next = False
            if self.env.user.id in self.apply_pass_stage.ids:
                self.is_hide_pass_next = True
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') :
            self.is_hide_pass_next = True
        else:
            self.is_hide_pass_next = True
            
    
    
    
    
    @api.depends('email_from')
    def _compute_application_count(self):
        count = 0
        ids =[]
        for record in self:
            if record.email_from:
                email_from = self.search([('email_from','in',self.mapped('email_from')),('id','!=',record._origin.id )])
                for data in email_from:
                    ids.append(data.id)
            if record.identification_no:
                identification_no = self.search([('identification_no','in',self.mapped('identification_no')),('id','!=',record._origin.id )])
                for data in identification_no:
                    ids.append(data.id)
            if record.partner_phone and not record.partner_phone == '+62alse':
                partner_phone = self.search([('partner_phone','in',self.mapped('partner_phone')),('id','!=',record._origin.id )])
                for data in partner_phone:
                    ids.append(data.id)
            if record.partner_mobile and not record.partner_mobile == '+62alse':
                partner_mobile = self.search([('partner_mobile','in',self.mapped('partner_mobile')),('id','!=',record._origin.id)])
                for data in partner_mobile:
                    ids.append(data.id)
            record.application_count = len(set(ids)) 

        # if self.application_count > 1:
        #     raise ValidationError(f"You already applied for this job position!")
                
    def get_participations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Participations'),
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('applicant_id','=',self.id),('survey_type','!=','INTERVIEW')],
            'context':{'search_default_group_by_survey': True}
          
        }
    
    def _get_participations_count(self):
        for record in self:
            count =0
            survey_user_input = self.env['survey.user_input'].search([('applicant_id','=',record.id),('survey_type','!=','INTERVIEW')])
            if survey_user_input:
                for data in survey_user_input:
                    count+=1
            record.participations_count = count
        
            
            
    
    
    def action_applications_email(self):
        ids = []
        if self.email_from:
            email_from = self.search([('email_from','in',self.mapped('email_from')),('id','!=',self.id )])
            for data in email_from:
                ids.append(data.id)
        if self.identification_no:
            identification_no = self.search([('identification_no','in',self.mapped('identification_no')),('id','!=',self.id )])
            for data in identification_no:
                ids.append(data.id)
        if self.partner_phone and not self.partner_phone == '+62alse':
            partner_phone = self.search([('partner_phone','in',self.mapped('partner_phone')),('id','!=',self.id )])
            for data in partner_phone:
                ids.append(data.id)
        if self.partner_mobile and not self.partner_mobile == '+62alse':
            partner_mobile = self.search([('partner_mobile','in',self.mapped('partner_mobile')),('id','!=',self.id)])
            for data in partner_mobile:
                ids.append(data.id)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Applications'),
            'res_model': self._name,
            'view_mode': 'kanban,tree,form,pivot,graph,calendar,activity',
            'domain': [('id', 'in', ids)],
            'context': {
                'active_test': False
            },
        }
    
    def pass_to_next_stage(self):
        for record in self:
            if record.job_id:
                line = record.job_id.stage_ids.filtered(lambda line:line.sequence == record.stage_replace_id.sequence + 1)
                if line:
                    record.stage_id = line[0].stage_id.id
                    record.apply_pass_stage = [(4,self.env.user.id)]
                else:
                    raise ValidationError("Stage not found")

    def get_all_menu(self):
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            job_id = self.env['hr.job'].search([])
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            data_job = []
            for record in job_id:
                data_stage = [data.id for data in record.stage_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids )]
                data_job.extend(data_stage)
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot,activity',
            'context':{},
            'domain': [('job_id.real_second_user_ids','in',self.env.user.id),('stage_replace_id','in',data_job)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') and not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot,activity',
            'context':{},
            'domain': [('job_id.user_ids','in',self.env.user.id)]
            }
        elif  self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot,activity',
            'context':{},
            'domain': [('job_id.user_ids','in',self.env.user.id)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot,activity',
            'context':{}
            }
            
    def get_all_menu_blacklist(self):
        views = [(self.env.ref('equip3_hr_recruitment_extend.blacklist_tree').id,'tree'),
                (self.env.ref('hr_recruitment.hr_kanban_view_applicant').id,'kanban'),
                 (self.env.ref('hr_recruitment.hr_applicant_view_form').id,'form'),
                 ]
        
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            job_id = self.env['hr.job'].search([])
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            data_job = []
            for record in job_id:
                data_stage = [data.id for data in record.stage_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids )]
                data_job.extend(data_stage)
            return {
            'type': 'ir.actions.act_window',
            'name': 'Blacklisted Applicants',
            'res_model': 'hr.applicant',
            'views':views,
            'search_view_id':search_view_id.id,
            'view_mode': 'tree,kanban,form',
            'context':{'create':False,'edit':False,'delete':False},
            'domain': [('job_id.real_second_user_ids','in',self.env.user.id),('stage_replace_id','in',data_job),('is_blacklist','=',True)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') and not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Blacklisted Applicants',
            'res_model': 'hr.applicant',
            'search_view_id':search_view_id.id,
            'views':views,
            'view_mode': 'tree,kanban,form',
            'context':{'create':False,'edit':False,'delete':False},
            'domain': [('job_id.user_ids','in',self.env.user.id),('is_blacklist','=',True)]
            }
        elif  self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Blacklisted Applicants',
            'res_model': 'hr.applicant',
            'search_view_id':search_view_id.id,
            'view_mode': 'tree,kanban,form',
            'views':views,
            'context':{'create':False,'edit':False,'delete':False},
            'domain': [('job_id.user_ids','in',self.env.user.id),('is_blacklist','=',True)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Blacklisted Applicants',
            'res_model': 'hr.applicant',
            'search_view_id':search_view_id.id,
            'domain': [('is_blacklist','=',True)],
            'view_mode': 'tree,kanban,form',
            'views':views,
            'context':{'create':False,'edit':False,'delete':False}
            }
            
    def get_report_menu(self):
        action = self.env.ref("hr_recruitment.hr_applicant_action_analysis")
        result = action.read()[0]
        if not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            job_ids = []
            for record in self.env['hr.job'].search([]):
                data_stage = [data.stage_id.id for data in record.stage_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids )]
                job_ids.extend(data_stage)
            result.update({
                'domain': [('job_id.real_second_user_ids','in',self.env.user.id),('stage_id','in',job_ids)],
            })
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') and not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            result.update({
                'domain': [('job_id.user_ids', 'in', self.env.user.id)],
            })
        elif self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            result.update({
                'domain': [('job_id.user_ids', 'in', self.env.user.id)],
            })
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            pass
        return result

    def get_menu(self):
        search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            job_id = self.env['hr.job'].search([])
            data_job = []
            for record in job_id:
                data_stage = [data.stage_id.id for data in record.stage_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids )]
                data_job.extend(data_stage)
        
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            # 'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot',
            'context':{'search_default_job_id': self.env.context.get('active_id'), 'default_job_id': self.env.context.get('active_id')},
            'domain': [('job_id.real_second_user_ids','in',self.env.user.id),('stage_id','in',data_job)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') and not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            # 'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot',
            'context':{'search_default_job_id': self.env.context.get('active_id'), 'default_job_id': self.env.context.get('active_id')},
            'domain': [('job_id.user_ids','in',self.env.user.id)]
            }
        elif  self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            # 'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot',
            'context':{'search_default_job_id': self.env.context.get('active_id'), 'default_job_id': self.env.context.get('active_id')},
           
            }

    def _is_hide_wa(self):
        for record in self:
            hide_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.is_whatsapp')
            if hide_wa:
                record['is_hide_wa']= False
            else:
                record['is_hide_wa']= True

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrApplicant, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        
        # print(res)
        arch = str(res['arch'])
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            arch = str(arch).replace("""<field name="stage_replace_id" clickable="0" widget="statusbar" options="{\'clickable\': \'0\', \'fold_field\': \'fold\',\'sequence_field\':\'sequence\'}" domain="[(\'id\',\'in\',stage_replace_domain_ids)]" force_Save="1" on_change="1" can_create="true" can_write="true" modifiers="{&quot;readonly&quot;: true}"/>\n""","""<field name="stage_replace_id" clickable="1" widget="statusbar" options="{\'clickable\': \'1\', \'fold_field\': \'fold\',\'sequence_field\':\'sequence\'}" domain="[(\'id\',\'in\',stage_replace_domain_ids)]" force_Save="1" on_change="1" can_create="true" can_write="true" modifiers="{&quot;readonly&quot;: false}"/>\n""")
            root = etree.fromstring(arch)
            res['arch'] = etree.tostring(root)
        
        sms = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.is_sms')
        if not sms:
            #dont change or inherit the fields string
            arch = str(arch).replace("""<field name="partner_phone" nolabel="1" widget="phone" class="oe_inline" modifiers="{}"/>""","""<field name="partner_phone" class="oe_inline" modifiers="{}"/>""")
            arch = str(arch).replace("""<field name="partner_mobile" nolabel="1" widget="phone" class="oe_inline" modifiers="{}"/>""","""<field name="partner_mobile" nolabel="1" class="oe_inline" modifiers="{}"/>""")
            root = etree.fromstring(arch)
            res['arch'] = etree.tostring(root)
        return res
    
    def _get_wa_url(self):
        for record in self:
            if record.partner_phone:
                record.wa_url = f"https://api.whatsapp.com/send?phone={record.partner_phone}"
            else:
                record.wa_url = False
                
    def open_wa_phone(self):  
        for record in self:
            if record.partner_phone:
                phone =  str(record.partner_phone)
                if phone[0:3] != "+62":
                    phone = "+62"+phone[1:range]
                elif phone[0:3] == "+62":
                    phone = phone[1:]
                
                return {
                   'name'     : 'wa website',
                  'res_model': 'ir.actions.act_url',
                  'type'     : 'ir.actions.act_url',
                  'target'   : '_blank',
                  'url'      : f"https://api.whatsapp.com/send?phone={phone}"
               }
            else:
                pass
            
    def open_wa_mobile(self):  
        for record in self:
            if record.partner_mobile:
                phone =  str(record.partner_mobile)
                if phone[0:3] != "+62":
                    phone = "+62"+phone[1:range]
                elif phone[0:3] == "+62":
                    phone = phone[1:]
                return {
                   'name'     : 'wa website',
                  'res_model': 'ir.actions.act_url',
                  'type'     : 'ir.actions.act_url',
                  'target'   : '_blank',
                  'url'      : f"https://api.whatsapp.com/send?phone={phone}"
               }
            else:
                pass
                
    def _get_wa_url_second(self):
        for record in self:
            if record.partner_mobile:
                record.wa_url_second = f"https://api.whatsapp.com/send?phone={record.partner_mobile}"
            else:
                record.wa_url_second = False
    
    
    def assign_to_self(self):
        for record in self:
            record.user_id = self.env.user.id
            record.is_hide_assign = True

    # def get_special_var(self):
    #     stage_replace_id = self.env['job.stage.line'].search(
    #             [('job_id', '=', self.job_id.id), ('stage_id', '=', self.stage_id.id)], order='sequence asc',limit=1)
    #     survey=self.env['survey.invite'].create({'survey_id':stage_replace_id.survey_id.id,'emails':str(self.email_from),'template_id':template.id})
    #     survey_url = survey.survey_start_url+f"?surveyId={stage_replace_id.survey_id.id}&applicantId={self.id}&jobPosition={self.job_id.id}"
    #     stage_before_id = self.env['job.stage.line'].search([('job_id', '=', self.job_id.id),('sequence', '<', stage_replace_id.sequence)], order='sequence desc',limit=1)
    #     next_stage_id = self.env['job.stage.line'].search([('job_id', '=', self.job_id.id),('sequence', '>', stage_replace_id.sequence)], order='sequence asc',limit=1)
    #     special_var = [{'variable':'{survey_name}',
    #                     'value':stage_replace_id.survey_id.title if stage_replace_id else ''},
    #                     {'variable':'{survey_url}',
    #                     'value':survey_url if survey_url else ''},
    #                     {'variable':'{stage_before_technical}',
    #                     'value':stage_before_id.stage_id.name if stage_before_id else ''},
    #                     {'variable':'{next_stage}',
    #                     'value': next_stage_id.stage_id.name},
    #                     {'variable':'{stage_now}',
    #                     'value': stage_replace_id.name if stage_replace_id else ''},
                                       
    #                                    ]
        
    #     return special_var
    
    

    def write(self, vals):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if 'stage_id' in vals:
            if self.is_blacklist:
                if not self.env.context.get('bypass_blacklist'):
                    raise ValidationError("This applicant is currently blacklisted. Please Whitelist this applicant by clicking the “Remove Blacklist” button on the applicant data before moving it to another stage.")
        if 'partner_phone' in vals:
            number = str(vals['partner_phone'])
            range = len(number)
            if number[0:3] != "+62":
                vals['partner_phone'] = "+62"+number[1:range]
        if 'partner_mobile' in vals:
            number = str(vals['partner_mobile'])
            range = len(number)
            if number[0:3] != "+62":
                vals['partner_mobile'] = "+62"+number[1:range]
        if 'stage_id' in vals and self.active and self.id:
            my_context = self.env.context = dict(self.env.context)
            context = EmailParam()
            wa_body = waParam()
            context.set_email(self.email_from)
            context.set_stage_now(self.job_id.name)
            context.set_name(self.partner_name)
            context.set_company_id(self.job_id.company_id.name)
            context.set_work_location(self.job_id.custom_work_location_id.name)
            context.set_job_position(self.job_id.name)
            context.set_job_url(f"{base_url}/jobs/detail/{self.job_id.id}")
            stage_replace_id = self.env['job.stage.line'].search(
                [('job_id', '=', self.job_id.id), ('stage_id', '=', vals['stage_id'])], order='sequence asc',limit=1)
            stage_before_id = self.env['job.stage.line'].search([('job_id', '=', self.job_id.id),('sequence', '<', stage_replace_id.sequence)], order='sequence desc',limit=1)
            context.set_stage_before(stage_before_id.stage_id.name if stage_before_id else '')
            next_stage_id = self.env['job.stage.line'].search([('job_id', '=', self.job_id.id),('sequence', '>', stage_replace_id.sequence)], order='sequence asc',limit=1)
            current_stage_id = self.env['job.stage.line'].search([
                ('job_id', '=', self.job_id.id),
                ('stage_id', '=', self.stage_id.id)
            ], order='sequence asc',limit=1)
            context.set_next_stage(next_stage_id.stage_id.name if next_stage_id else '')
            context.set_title(stage_replace_id.survey_id.title)
            context.set_stage_now(stage_replace_id.stage_id.name)
            context.set_recruiter_email(self.user_id.login if self.user_id else '')
            context.set_recruiter_name(self.user_id.name if self.user_id else '')
            if stage_replace_id:
                    self.stage_replace_id = stage_replace_id.id
                    self.shadow_stage_replace_id = stage_replace_id.id
                    if stage_replace_id.is_final_stage:
                        self.is_hire = True
                    else:
                        self.is_hire = False
            send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.send_by_wa')
            send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
            
            
            if stage_replace_id.interview_id:
                self.is_interview = True
            if stage_replace_id.survey_id and not stage_replace_id.survey_id.is_manual_test:
                template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)
                survey=self.env['survey.invite'].create({'survey_id':stage_replace_id.survey_id.id,'emails':str(self.email_from),'template_id':template.id})
                survey_url = survey.survey_start_url+f"?surveyId={stage_replace_id.survey_id.id}&applicantId={self.id}&jobPosition={self.job_id.id}"
                if not stage_replace_id.sequence < current_stage_id.sequence:
                    if send_by_email:
                        if stage_replace_id.stage_id and stage_replace_id.stage_id.template_id and stage_replace_id.stage_id.template_id.is_digital_flag == True:
                            context.set_stage_now(stage_replace_id.stage_id.name)
                            context.set_url_test(survey_url)
                            template = self.env.ref('equip3_hr_recruitment_extend.mail_template_invite_test')
                            if stage_replace_id.survey_id.is_application_form:
                                template = self.env.ref('equip3_hr_recruitment_extend.mail_application_invite', raise_if_not_found=True)
                            my_context.update(context.get_context())
                            stage_replace_id.stage_id.template_id.with_context(my_context)
                        else:
                            context.set_stage_now(stage_replace_id.stage_id.name)
                            context.set_url_test(survey_url)
                            template = self.env.ref('equip3_hr_recruitment_extend.mail_template_invite_test')
                            if stage_replace_id.survey_id.is_application_form:
                                template = self.env.ref('equip3_hr_recruitment_extend.mail_application_invite', raise_if_not_found=True)
                            my_context.update(context.get_context())
                            template.send_mail(self.id, force_send=True)
                            template.with_context(my_context)
                    if send_by_wa:
                        template = self.env.ref('equip3_hr_recruitment_extend.wa_template_1')
                        if template:
                            # special_var =[{'variable':'{survey_name}',
                            # 'value':stage_replace_id.survey_id.title if stage_replace_id else ''},
                            # {'variable':'{survey_url}',
                            # 'value':survey_url if survey_url else ''},
                            # {'variable':'{stage_before_technical}',
                            # 'value':stage_before_id.stage_id.name if stage_before_id else ''},
                            # {'variable':'{next_stage}',
                            # 'value': next_stage_id.stage_id.name},
                            # {'variable':'{stage_now}',
                            # 'value': stage_replace_id.stage_id.name if stage_replace_id else ''},
                                        
                            #             ]
                            # wa_body.set_special_variable(special_var)
                            # wa_body.send_wa_qiscuss(template.message_line_ids,self,template)
                            
                            wa_string = str(template.message)
                            if "${ctx['next_stage']}" in wa_string:
                                wa_string = wa_string.replace("${ctx['next_stage']}", next_stage_id.stage_id.name)
                            if "${stage_now}" in wa_string:
                                wa_string = str(wa_string).replace("${stage_now}", str(stage_replace_id.stage_id.name))
                            wa_body.set_wa_string(wa_string,template._name,template_id=template)
                            wa_body.set_applicant_name(self.partner_name)
                            wa_body.set_survey_url(survey_url if survey_url else '')
                            wa_body.set_survey_name(stage_replace_id.survey_id.title if stage_replace_id else '')
                            wa_body.set_company(self.job_id.company_id.name)
                            wa_body.set_job(self.job_id.name)
                            wa_body.set_stage_before_technical(stage_before_id.stage_id.name if stage_before_id else '')
                            wa_body.send_wa(self.partner_mobile)
                            if stage_replace_id.stage_id.template_wa_id:
                                template = stage_replace_id.stage_id.template_wa_id
                                wa_string = str(template.message)
                                if "${ctx['next_stage']}" in wa_string:
                                    wa_string = wa_string.replace("${ctx['next_stage']}", next_stage_id.stage_id.name)
                                if "${stage_now}" in wa_string:
                                    wa_string = str(wa_string).replace("${stage_now}", str(stage_replace_id.stage_id.name))
                                wa_body.set_wa_string(wa_string,template._name,template_id=template)
                                wa_body.set_applicant_name(self.partner_name)
                                wa_body.set_survey_url(survey_url if survey_url else '')
                                wa_body.set_survey_name(stage_replace_id.survey_id.title if stage_replace_id else '')
                                wa_body.set_company(self.job_id.company_id.name)
                                wa_body.set_job(self.job_id.name)
                                wa_body.set_stage_before_technical(stage_before_id.stage_id.name if stage_before_id else '')
                                wa_body.send_wa(self.partner_mobile)
                else:
                    if not self.env.context.get('bypass_blacklist'):
                        raise ValidationError(f"You can not move this applicant to the previous stage")
            elif stage_replace_id.survey_id and stage_replace_id.survey_id.is_manual_test:
                data_pdf = {'survey':stage_replace_id.survey_id,
                            'review':False,
                            'format_datetime': lambda dt: format_datetime(self.env, dt, dt_format=False),
                            'format_date': lambda date: format_date(self.env, date)
                                        }
                template = self.env.ref('equip3_hr_recruitment_extend.wa_template_3')
                pdf =  self.env.ref('equip3_hr_recruitment_extend.technical_test_template')._render_qweb_pdf([stage_replace_id.survey_id.id],data_pdf)
                if not stage_replace_id.sequence < current_stage_id.sequence:
                    if send_by_wa:
                        if template:
                            # special_var =[{'variable':'{survey_name}',
                            # 'value':stage_replace_id.survey_id.title if stage_replace_id else ''},
                            # {'variable':'{survey_url}',
                            # 'value':survey_url if survey_url else ''},
                            # {'variable':'{stage_before_technical}',
                            # 'value':stage_before_id.stage_id.name if stage_before_id else ''},
                            # {'variable':'{next_stage}',
                            # 'value': next_stage_id.stage_id.name},
                            # {'variable':'{stage_now}',
                            # 'value': stage_replace_id.stage_id.name if stage_replace_id else ''},
                                        
                            #             ]
                            # wa_body.set_special_variable(special_var)
                            # wa_body.send_wa_qiscuss(template.message_line_ids,self,template)
                            wa_string = str(template.message)
                            if "${ctx['next_stage']}" in wa_string:
                                wa_string = wa_string.replace("${ctx['next_stage']}", next_stage_id.stage_id.name)
                            if "${stage_now}" in wa_string:
                                wa_string = str(wa_string).replace("${stage_now}", str(stage_replace_id.stage_id.name))
                            wa_body.set_wa_string(wa_string,template._name,template_id= template)
                            wa_body.set_applicant_name(self.partner_name)
                            wa_body.set_survey_name(stage_replace_id.survey_id.title if stage_replace_id else '')
                            wa_body.set_company(self.job_id.company_id.name)
                            wa_body.set_stage_before_technical(stage_before_id.stage_id.name if stage_before_id else '')
                            wa_body.set_recruiter_email(self.user_id.login if self.user_id else '')
                            wa_body.set_recruiter_name(self.user_id.name)
                            wa_body.set_job(self.job_id.name)
                            wa_body.send_wa(self.partner_mobile)
                            wa_body.send_wa_file(self.partner_mobile,pdf,self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}")
                    if send_by_email:
                        if stage_replace_id.stage_id and stage_replace_id.stage_id.template_id and stage_replace_id.stage_id.template_id.is_digital_flag == True:
                            attachment = base64.b64encode(pdf[0])
                            ir_values = {
                                'name': self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}" + '.pdf',
                                'type': 'binary',
                                'datas': attachment,
                                'store_fname': self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}",
                                'mimetype': 'application/x-pdf',
                            }
                            data_id = self.env['ir.attachment'].create(ir_values)
                            my_context.update(context.get_context())
                            template = self.env.ref('equip3_hr_recruitment_extend.mail_template_manual_test',raise_if_not_found=True)

                            template.attachment_ids = [(5, 0, 0)]
                            template.attachment_ids = [(6, 0, [data_id.id])]
                            stage_replace_id.stage_id.template_id.with_context(my_context)
                        else:
                            attachment = base64.b64encode(pdf[0])
                            ir_values = {
                                'name': self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}" + '.pdf',
                                'type': 'binary',
                                'datas': attachment,
                                'store_fname': self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}",
                                'mimetype': 'application/x-pdf',
                            }
                            data_id = self.env['ir.attachment'].create(ir_values)
                            my_context.update(context.get_context())
                            template = self.env.ref('equip3_hr_recruitment_extend.mail_template_manual_test',raise_if_not_found=True)

                            template.attachment_ids = [(5, 0, 0)]
                            template.attachment_ids = [(6, 0, [data_id.id])]
                            template.send_mail(self.id, force_send=True)
                            template.with_context(my_context)
                else:
                    if not self.env.context.get('bypass_blacklist'):
                        raise ValidationError("You can not move this applicant to the previous stage.")
            elif not stage_replace_id.survey_id:
                if not stage_replace_id.sequence < current_stage_id.sequence:
                    if send_by_email:
                        if stage_replace_id.stage_id and stage_replace_id.stage_id.template_id:
                            context.set_name(self.partner_name)
                            context.set_company_id(self.job_id.company_id.name)
                            my_context.update(context.get_context())
                    if send_by_wa:
                        if stage_replace_id.stage_id and stage_replace_id.stage_id.template_wa_id:
                            template_wa_id = stage_replace_id.stage_id.template_wa_id
                            if template_wa_id:
                                # special_var =[{'variable':'{survey_name}',
                                # 'value':stage_replace_id.survey_id.title if stage_replace_id else ''},
                                # {'variable':'{survey_url}',
                                # 'value':survey_url if survey_url else ''},
                                # {'variable':'{stage_before_technical}',
                                # 'value':stage_before_id.stage_id.name if stage_before_id else ''},
                                # {'variable':'{next_stage}',
                                # 'value': next_stage_id.stage_id.name},
                                # {'variable':'{stage_now}',
                                # 'value': stage_replace_id.stage_id.name if stage_replace_id else ''},
                                            
                                #             ]
                                # wa_body.set_special_variable(special_var)
                                # wa_body.send_wa_qiscuss(template_wa_id.message_line_ids,self,template_wa_id)
                                wa_string = str(template_wa_id.message)
                                if "${ctx['next_stage']}" in wa_string:
                                    wa_string = wa_string.replace("${ctx['next_stage']}", next_stage_id.stage_id.name)
                                if "${stage_now}" in wa_string:
                                    wa_string = str(wa_string).replace("${stage_now}", str(stage_replace_id.stage_id.name))
                                wa_body.set_wa_string(wa_string,template_wa_id._name,template_id=template_wa_id)
                                wa_body.set_applicant_name(self.partner_name)
                                wa_body.set_company(self.job_id.company_id.name)
                                wa_body.set_stage_before_technical(stage_before_id.stage_id.name if stage_before_id else '')
                                wa_body.set_recruiter_email(self.user_id.login if self.user_id else '')
                                wa_body.set_recruiter_name(self.user_id.name)
                                wa_body.set_job(self.job_id.name)
                                wa_body.send_wa(self.partner_mobile)
                else:
                    if not self.env.context.get('bypass_blacklist'):
                        raise ValidationError("You can not move this applicant to the previous stage.")

            ## create data to outsource analysis
            work_location_id = False
            if self.work_location_id:
                work_location_id = self.work_location_id.id
            outsource_id = False
            if self.outsource_id:
                outsource_id = self.outsource_id.id
            outsource_analysis_val = {
                'application_id': self.id,
                'name': self.name,
                'partner_name': self.partner_name,
                'applicant_id': self.applicant_id,
                'user_id': self.user_id.id,
                'job_id': self.job_id.id,
                'department_id': self.department_id.id,
                'work_location_id': work_location_id,
                'company_id': self.company_id.id,
                'outsource_id': outsource_id,
                'stage_id': vals['stage_id'],
                'stage_replace_id': self.stage_replace_id.id,
                'aplicant_create_date':self.aplicant_create_date,
            }
            self.env['hr.outsource.analysis'].sudo().create(outsource_analysis_val)
            self.env['hr.outsource.analysis'].get_rate()
            self.env['hr.outsource.analysis'].get_rate_by_applicant_date()

        res=super(HrApplicant, self).write(vals)
        return res

    def qualification_answer(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detailed Answers',
            'res_model': 'survey.user_input.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'domain': [('applicant_id','=', self.id)]
        }
        
    
    @api.model
    def create(self, vals):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        result = []
        if 'partner_phone' in vals:
                number = str(vals['partner_phone'])
                range = len(number)
                if number[0:3] != "+62":
                    vals['partner_phone'] = "+62"+number[1:range]          
        if 'partner_mobile' in vals:
            number = str(vals['partner_mobile'])
            range = len(number)
            if number[0:3] != "+62":
                vals['partner_mobile'] = "+62"+number[1:range]
        vals['applicant_id'] = self.env['ir.sequence'].next_by_code('applicant.sequence')
        res = super(HrApplicant, self).create(vals)
        if res.applicant_question_answer:
            for record in res.applicant_question_answer:   
                if record.question.lower() == "upload your cv":
                    file_cv = record.file
                    res.write({
                        'file_cv': file_cv
                    })
                    attachment_value = {
                        'name': record.file_name,
                        'datas': file_cv,
                        'res_model': 'hr.applicant',
                        'res_id': res.id,
                    }
                    self.env['ir.attachment'].sudo().create(attachment_value)
                elif record.question.lower() == "what is your name?":
                    partner_name = record.answer
                    res.write({
                        'partner_name': partner_name ,
                        'name':f"{res.name}/{partner_name}"
                    })

                elif record.question.lower() == "what is your phone number?":
                    partner_phone = record.answer
                    res.write({
                        'partner_phone': partner_phone
                    })

                
                elif record.question.lower() == "what is your degree?":
                    degree_check = self.env['hr.recruitment.degree'].search([('name','=',record.answer)],limit=1)
                    if degree_check:
                        degree = degree_check.id
                        res.write({
                            'type_id': degree
                        })
                elif record.question.lower() == "what is your address?":
                    res.write({
                        'address': record.answer
                    })
                elif record.question.lower() == "what is your expected salary?":
                    res.write({
                        'salary_expected': record.answer
                    })
                    
                elif record.question.lower() == "what is your id card number?":
                    res.write({
                        'identification_no': record.answer
                    })
                elif record.question.lower() == "what is your gender?":
                    res.write({
                        'gender': str(record.answer).lower()
                    })
                elif record.question.lower() == "what is your date of birth?":
                    date_of_birth = datetime.strptime(record.answer,"%Y-%m-%d")
                    res.write({
                        'date_of_birth': date_of_birth,
                        
                    })
                elif record.question.lower() == "when are you ready to start work if you are accepted in this company?":
                    avail = datetime.strptime(record.answer,"%Y-%m-%d")
                    res.write({
                        'availability': avail,
                        
                    })
                    
                elif record.question.lower() == "what is your marital status?":
                    marital_status = self.env['employee.marital.status'].search([('name','=',record.answer)],limit=1)
                    if marital_status:
                        res.write({
                            'marital_status': marital_status.id
                        })
                elif record.question.lower() == "what is your religion?":
                    employee_religion = self.env['employee.religion'].search([('name','=',record.answer)],limit=1)
                    if employee_religion:
                        res.write({
                            'religion': employee_religion.id
                        })
                elif record.question.lower() == "what is your last drawn salary?":
                    res.write({
                        'last_drawn_salary': float(record.answer)
                    })
        result.extend(self.set_stage_applicant(res.applicant_question_answer,res))  
        stage = [data.stage_id.id for data in res.job_id.stage_ids.filtered(lambda line: line.is_apply_stage)]
        not_suitable_id = self.env.ref('equip3_hr_recruitment_extend.not_suitable').id
        not_suitable = [data.stage_id.id for data in res.job_id.stage_ids.filtered(lambda line: line.stage_id.id == not_suitable_id)]
        if stage:
            if any(data == False for data in result):
                hr_app_refuse_reason = self.env['hr.applicant.refuse.reason'].search([('applicant_weightage', '=', True)], limit=1)
                if hr_app_refuse_reason:
                    res.refuse_reason_id = hr_app_refuse_reason.id
                res.active = False
                if not not_suitable:
                    all_stages = self.env['hr.recruitment.stage'].search([('id', '=', not_suitable_id)])
                    for stage_data in all_stages:
                        stage_data.is_global = True
                        if stage_data.is_global:
                            not_suitable.append(stage_data.id)
                res.stage_id = not_suitable[0]
            if stage and not res.stage_id:
                res.stage_id = stage[0]
                res.refuse_reason_id = res.stage_id.refuse_reason_id.id if res.stage_id.refuse_reason_id else False
                if res.stage_id.template_id and res.active:
                    template = res.stage_id.template_id
                    template.send_mail(res.id, force_send=True,notif_layout='mail.mail_notification_light')
            elif stage and res.stage_id:
                if not res.active and res.stage_id.refuse_template_id:
                    template = res.stage_id.refuse_template_id
                    template.send_mail(res.id, force_send=True,notif_layout='mail.mail_notification_light')
        else:
            raise ValidationError("Please configure the First Stage") 
        return res
    
    @api.constrains('job_id')
    def _constraint_job_id(self):
        for record in self:
            if not record.job_id:
                raise ValidationError("Please input Applied Job")
    
    def set_stage_applicant(self, applicant_answers,res,question_string=None):
        list_answer = []
        total_points = 1.0
        minimum_weightage = 0.0
        for line_data in applicant_answers:
            if line_data.question_id.question_type == 'quantitative':
                if str.lower(line_data.question_id.question.question) == "what is your date of birth?":
                    if float(res.birth_years) < line_data.question_id.range_from or  float(res.birth_years) > line_data.question_id.range_to:
                        total_points -= line_data.question_id.weightage_percentage

                elif line_data.question_id.range_from >= 0.0 and line_data.question_id.range_to != 0.0:
                    if float(line_data.answer) < line_data.question_id.range_from or  float(line_data.answer) > line_data.question_id.range_to:
                        total_points -= line_data.question_id.weightage_percentage
            
            if line_data.question_id.question_type == 'qualitative':
                if line_data.question_id.answers_ids.filtered(lambda line:line.is_correct):
                    check_question = line_data.question_id.answers_ids.filtered(lambda line:line.answer == line_data.answer and line.is_correct)
                    if not check_question:
                        total_points -= line_data.question_id.weightage_percentage

        total_wightage = round(total_points, 1)
        jobs = self.env['hr.job'].search([('id', '=', res.job_id.id)])
        for job in jobs:
            minimum_weightage += job.minimum_weightage / 100

        if total_wightage < minimum_weightage:
            list_answer.append(False)
        else:
            list_answer.append(True)

        return list_answer

    # @api.constrains('stage_id')
    # def _constrains_stage(self):
    #     for rec in self:
    #         view_id = self.env.ref('hr_recruitment.hr_kanban_view_applicant')
    #         all_hr_applicant_views = self.env['ir.ui.view'].search([('model', '=', self._inherit)])
    #         all_kanban_views = self.env['ir.ui.view'].search([('model', '=', self._inherit), ('type', '=', 'kanban')])
    #         self_id = self._origin.id
    #         query = """SELECT stage_id FROM hr_applicant WHERE id=%s"""
    #         self.env.cr.execute(query, [self_id])
    #         ba_stage_id = self.env.cr.fetchall()
    #         prev_stage_id = self.env['hr.recruitment.stage'].browse(ba_stage_id[0][0])
    #         print('------------ prev_stage_id -------', prev_stage_id.name, prev_stage_id.sequence, '------',
    #               rec.stage_id.name, rec.stage_id.sequence)
    #         res = {}
    #         if rec.stage_id.sequence < prev_stage_id.sequence:
    #             # res['warning'] = {
    #             #     'title': _('Warning'),
    #             #     'message': _(
    #             #         'Are you sure you want to move this applicant to the previous stage?')
    #             # }
    #             raise ValidationError("You can not move this applicant to the previous stage.")
            # return res


    def send_applicant_email_notification(self, res_id):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if self.partner_phone:
            number = str(self.partner_phone)
            range = len(number)
            if number[0:3] != "+62":
                self.partner_phone = "+62"+number[1:range]
        if self.partner_mobile:
            number = str(self.partner_mobile)
            range = len(number)
            if number[0:3] != "+62":
                self.partner_mobile = "+62"+number[1:range]
        if self.stage_id and self.active and res_id:
            my_context = self.env.context = dict(self.env.context)
            context = EmailParam()
            context.set_email(self.email_from)
            context.set_stage_now(self.job_id.name)
            context.set_name(self.partner_name)
            context.set_company_id(self.job_id.company_id.name)
            context.set_work_location(self.job_id.custom_work_location_id.name)
            context.set_job_position(self.job_id.name)
            context.set_job_url(f"{base_url}/jobs/detail/{self.job_id.id}")
            stage_replace_id = self.env['job.stage.line'].search(
                [('job_id', '=', self.job_id.id), ('stage_id', '=', self.stage_id.id)], order='sequence asc',limit=1)
            stage_before_id = self.env['job.stage.line'].search([('job_id', '=', self.job_id.id),('sequence', '<', stage_replace_id.sequence)], order='sequence desc',limit=1)
            context.set_stage_before(stage_before_id.stage_id.name if stage_before_id else '')
            next_stage_id = self.env['job.stage.line'].search([('job_id', '=', self.job_id.id),('sequence', '>', stage_replace_id.sequence)], order='sequence asc',limit=1)
            current_stage_id = self.env['job.stage.line'].search([
                ('job_id', '=', self.job_id.id),
                ('stage_id', '=', self.stage_id.id)
            ], order='sequence asc',limit=1)
            context.set_next_stage(next_stage_id.stage_id.name if next_stage_id else '')
            context.set_title(stage_replace_id.survey_id.title)
            context.set_stage_now(stage_replace_id.stage_id.name)
            context.set_recruiter_email(self.user_id.login if self.user_id else '')
            context.set_recruiter_name(self.user_id.name if self.user_id else '')
            send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
            if stage_replace_id.survey_id and not stage_replace_id.survey_id.is_manual_test:
                template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)
                survey=self.env['survey.invite'].create({'survey_id':stage_replace_id.survey_id.id,'emails':str(self.email_from),'template_id':template.id})
                survey_url = survey.survey_start_url+f"?surveyId={stage_replace_id.survey_id.id}&applicantId={res_id}&jobPosition={self.job_id.id}"
                if not stage_replace_id.sequence < current_stage_id.sequence:
                    if send_by_email:
                        if stage_replace_id.stage_id and stage_replace_id.stage_id.template_id and stage_replace_id.stage_id.template_id.is_digital_flag == True:
                            context.set_stage_now(stage_replace_id.stage_id.name)
                            context.set_url_test(survey_url)
                            template = stage_replace_id.stage_id.template_id
                            my_context.update(context.get_context())
                            if template:
                                template.send_mail(res_id, force_send=True, notif_layout='mail.mail_notification_light')
                                template.with_context(my_context)
                        else:
                            context.set_stage_now(stage_replace_id.stage_id.name)
                            context.set_url_test(survey_url)
                            template = self.env.ref('equip3_hr_recruitment_extend.mail_template_invite_test')
                            stage_template = stage_replace_id.stage_id.template_id
                            my_context.update(context.get_context())
                            if template:
                                template.send_mail(res_id, force_send=True, notif_layout='mail.mail_notification_light')
                                template.with_context(my_context)
                            if stage_template:
                                stage_template.send_mail(res_id, force_send=True, notif_layout='mail.mail_notification_light')
                                stage_template.with_context(my_context)
                else:
                    if not self.env.context.get('bypass_blacklist'):
                        raise ValidationError(f"You can not move this applicant to the previous stage")
            elif stage_replace_id.survey_id and stage_replace_id.survey_id.is_manual_test:
                data_pdf = {'survey':stage_replace_id.survey_id,
                            'review':False,
                            'format_datetime': lambda dt: format_datetime(self.env, dt, dt_format=False),
                            'format_date': lambda date: format_date(self.env, date)
                                        }
                template = self.env.ref('equip3_hr_recruitment_extend.wa_template_3')
                pdf =  self.env.ref('equip3_hr_recruitment_extend.technical_test_template')._render_qweb_pdf([stage_replace_id.survey_id.id],data_pdf)
                if not stage_replace_id.sequence < current_stage_id.sequence:
                    if send_by_email:
                        if stage_replace_id.stage_id and stage_replace_id.stage_id.template_id and stage_replace_id.stage_id.template_id.is_digital_flag == True:
                            attachment = base64.b64encode(pdf[0])
                            ir_values = {
                                'name': self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}" + '.pdf',
                                'type': 'binary',
                                'datas': attachment,
                                'store_fname': self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}",
                                'mimetype': 'application/x-pdf',
                            }
                            data_id = self.env['ir.attachment'].create(ir_values)
                            my_context.update(context.get_context())
                            template = stage_replace_id.stage_id.template_id

                            template.attachment_ids = [(5, 0, 0)]
                            template.attachment_ids = [(6, 0, [data_id.id])]
                            template.send_mail(res_id, force_send=True, notif_layout='mail.mail_notification_light')
                            template.with_context(my_context)
                        else:
                            attachment = base64.b64encode(pdf[0])
                            ir_values = {
                                'name': self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}" + '.pdf',
                                'type': 'binary',
                                'datas': attachment,
                                'store_fname': self.job_id.company_id.name+f"_{stage_replace_id.survey_id.title}",
                                'mimetype': 'application/x-pdf',
                            }
                            data_id = self.env['ir.attachment'].create(ir_values)
                            my_context.update(context.get_context())
                            template = self.env.ref('equip3_hr_recruitment_extend.mail_template_manual_test',raise_if_not_found=True)

                            template.attachment_ids = [(5, 0, 0)]
                            template.attachment_ids = [(6, 0, [data_id.id])]
                            template.send_mail(res_id, force_send=True)
                            template.with_context(my_context)
                else:
                    if not self.env.context.get('bypass_blacklist'):
                        raise ValidationError("You can not move this applicant to the previous stage.")
            elif not stage_replace_id.survey_id:
                if not stage_replace_id.sequence < current_stage_id.sequence:
                    if send_by_email:
                        if stage_replace_id.stage_id and stage_replace_id.stage_id.template_id:
                            context.set_name(self.partner_name)
                            context.set_company_id(self.job_id.company_id.name)
                            my_context.update(context.get_context())
                            template = stage_replace_id.stage_id.template_id
                            template.send_mail(res_id, force_send=True, notif_layout='mail.mail_notification_light')
                            template.with_context(my_context)
                else:
                    if not self.env.context.get('bypass_blacklist'):
                        raise ValidationError("You can not move this applicant to the previous stage.")

    @api.onchange('stage_replace_id')
    def _onchange_stage_replace_id(self):
        for record in self:
            origin_stage_id = self.env['hr.recruitment.stage'].search(
                [('id', '=', record.stage_replace_id.stage_id.id)], limit=1)
            if origin_stage_id:
                record.write({
                    'stage_id': origin_stage_id.id
                })
            if record.stage_replace_id:
                self_id = self._origin.id
                query_update = _("UPDATE hr_applicant SET stage_id=%s, shadow_stage_replace_id=%s WHERE id=%s") % (int(record.stage_replace_id.stage_id.id), int(record.stage_replace_id.id), int(self_id))
                self._cr.execute(query_update)
                record.send_applicant_email_notification(self_id)

                
    @api.depends('file_cv')
    def _compute_file_name(self):
        flag = True
        for record in self:
            # flag = True
            uploaded_file = record.cv_name
            if flag and not record.cv_type_from_job_portal:
                if uploaded_file:
                    extract_extension = uploaded_file.split('.')
                    if len(extract_extension) > 1:
                        mime_type = mimetypes.types_map['.' + extract_extension[1]]
                        record.uploaded_cv_type = mime_type
            else:
                record.uploaded_cv_type = record.cv_type_from_job_portal
            if record.file_cv:
                if record.partner_name:
                    record.cv_name = "CV_" + record.partner_name
                    flag = False
                elif record.name:
                    record.cv_name = "CV_" + record.name
                    flag = False
                else:
                    record.cv_name = False
                    flag = False


    @api.depends('job_id')
    def compute_stage_replace_id(self):
        for record in self:
            if record.stage_id and record.job_id:
                stage_replace_id = self.env['job.stage.line'].search([('job_id', '=', record.job_id.id),('stage_id','=',record.stage_id.id)], order='sequence asc',limit=1)
                if stage_replace_id:
                    record.stage_replace_id = stage_replace_id.id
                    record.shadow_stage_replace_id = stage_replace_id.id
                else:
                    record.stage_replace_id = False

            else:
                record.stage_replace_id = False


    @api.onchange('stage_replace_domain_ids')
    def _onchange_stage_replace_domain_ids(self):
        for record in self:
            if record.stage_replace_domain_ids:
                if not record.stage_id:
                    record.stage_replace_id = record.stage_replace_domain_ids.ids[0]
                    record.shadow_stage_replace_id = record.stage_replace_domain_ids.ids[0]
                    record.stage_id = record.stage_replace_id.stage_id.id
                else:
                    record.stage_replace_id = False
                    record.stage_id = False
            else:
                record.stage_replace_id = False
                record.stage_id = False


    #dont delete , it's matter function to write the base odoo stage
    @api.depends('job_id')
    def _compute_stage(self):
        pass


    @api.depends('job_id')
    def _compute_stage_domain_ids(self):
        for record in self:
            if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
                if record.job_id:
                    stage_list = []
                    stage_replace_list = []
                    stage_ids = self.env['job.stage.line'].search([('job_id','=',record.job_id.id),('user_ids','in',self.env.user.id)],order='sequence asc')
                    if stage_ids:
                        id = [data.stage_id.id for data in stage_ids]
                        second_id = [data.id for data in stage_ids]
                        stage_list.extend(id)
                        stage_replace_list.extend(second_id)
                        record.stage_domain_ids =  [(6,0, stage_list)]
                        record.stage_replace_domain_ids =  [(6,0, stage_replace_list)]
                    else:
                        record.stage_domain_ids = False
                        record.stage_replace_domain_ids = False
                else:
                    record.stage_domain_ids = False
                    record.stage_replace_domain_ids = False
            else:
                if record.job_id:
                    stage_list = []
                    stage_replace_list = []
                    stage_ids = self.env['job.stage.line'].search([('job_id','=',record.job_id.id)],order='sequence asc')
                    if stage_ids:
                        id = [data.stage_id.id for data in stage_ids]
                        second_id = [data.id for data in stage_ids]
                        stage_list.extend(id)
                        stage_replace_list.extend(second_id)
                        record.stage_domain_ids =  [(6,0, stage_list)]
                        record.stage_replace_domain_ids =  [(6,0, stage_replace_list)]
                    else:
                        record.stage_domain_ids = False
                        record.stage_replace_domain_ids = False
                else:
                    record.stage_domain_ids = False
                    record.stage_replace_domain_ids = False





    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            job_id = self._context.get('default_job_id')
            search_domain = []
            list_id = []
            if stages:
                if job_id:
                    stage_search_ids = self.env['job.stage.line'].search([('job_id', '=', job_id),('user_ids','in',self.env.user.id)], order='sequence asc')
                    if stage_search_ids:
                        id = [data.stage_id.id for data in stage_search_ids]
                        list_id.extend(id)
                search_domain = [('id', 'in', list_id)] + search_domain
            stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
            if list_id:
                return stages.browse(list_id)
            else:
                return stages.browse(stage_ids)
        else:
            job_id = self._context.get('default_job_id')
            search_domain = []
            list_id = []
            if stages:
                if job_id:
                    stage_search_ids = self.env['job.stage.line'].search([('job_id', '=', job_id)], order='sequence asc')
                    if stage_search_ids:
                        id = [data.stage_id.id for data in stage_search_ids]
                        list_id.extend(id)
                search_domain = [('id', 'in', list_id)] + search_domain
            stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
            if list_id:
                return stages.browse(list_id)
            else:
                return stages.browse(stage_ids)

    @api.model
    def send_mail_refuse(self):
        context = EmailParam()
        my_context = self.env.context = dict(self.env.context)
        applicant_refuse = self.sudo().search([('active', '=', False),('refuse_is_sent', '=', False)])
        for res in applicant_refuse:
            refuse_template = res.stage_id.refuse_template_id
            if refuse_template:
                res.write({'refuse_is_sent': True})
                context.set_email(res.email_from)
                my_context.update(context.get_context())
                refuse_template.send_mail(res.id, force_send=True)
                refuse_template.with_context(my_context)

    # The contact will save each phone number separately, into different contact object.
    def _message_post_after_hook(self, message, msg_vals):
        res = super(Applicant, self)._message_post_after_hook(message, msg_vals)
        return res


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(HrApplicant, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(HrApplicant, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

