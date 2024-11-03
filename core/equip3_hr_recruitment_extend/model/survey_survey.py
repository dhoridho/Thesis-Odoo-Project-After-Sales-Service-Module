import base64
import time
import werkzeug
from odoo import fields, models, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import requests
from odoo.tools import format_datetime, format_date, is_html_empty
from lxml import etree
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}
class hashMicroInheritSurveySurvey(models.Model):
    _inherit = 'survey.survey'
    is_application_form = fields.Boolean()
    is_follow_up = fields.Boolean(default=False)
    email_template_id = fields.Many2one('mail.template')
    wa_template_id = fields.Many2one('wa.template.message')
    interval_number = fields.Integer()
    interval_type = fields.Selection([('minutes','Minutes'),('hours','Hours'),('days','Days'),('weeks','Weeks'),('months','Months')])
    number_of_repetion = fields.Integer()
    is_manual_test = fields.Boolean()
    # refuse_reason = fields.Many2one('hr.applicant.refuse.reason', 'Refuse Reason')
    is_personality_and_emotional = fields.Boolean(compute='_compute_category', invisible=True)
    is_auto_next_stage = fields.Boolean("Auto Next Stage on Completion", default=False)
    is_setting_psychological_test = fields.Boolean(compute='_is_setting_psychological_test')

    def _is_setting_psychological_test(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.is_auto_next_stage_psychological')
            setting_by_job_position = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.auto_completion_on_psychological')
            if setting :
                if setting_by_job_position == 'by_job_position':
                    rec.is_setting_psychological_test = True
                else:
                    rec.is_setting_psychological_test = False
            else:
                rec.is_setting_psychological_test = True

    def _compute_category(self):
        for rec in self:
            if rec.category_id.name == 'Personality & Emotional Inventory':
                rec.is_personality_and_emotional = True
            else:
                rec.is_personality_and_emotional = False
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=True, submenu=True):
        res = super(hashMicroInheritSurveySurvey, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        if  self.env.context.get('default_survey_type') in ['disc'] and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            res['arch'] = etree.tostring(root)
        elif  self.env.context.get('default_survey_type') in ['disc'] and  self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            res['arch'] = etree.tostring(root)

        return res
    
    
    
    @api.model
    def default_get(self, fields):
        res = super(hashMicroInheritSurveySurvey, self).default_get(fields)
        template_email =self.env.ref('equip3_hr_recruitment_extend.mail_template_reminder_invite_test').id
        template_wa =self.env.ref('equip3_hr_recruitment_extend.wa_template_2').id
        res.update({'email_template_id': template_email,
                    'wa_template_id':template_wa,
                    'interval_type':'hours',
                    'interval_number':1,
                    'number_of_repetion':1
                    })
        return res
    
    @api.onchange('number_of_repetion')
    def _onchange_number_of_repetion(self):
        for record in self:
            if record.number_of_repetion:
                if record.number_of_repetion < 0:
                    raise ValidationError("Number of Repetitions cannot less than 0")
                
    @api.onchange('interval_number')
    def _onchange_number_of_interval_number(self):
        for record in self:
            if record.interval_number:
                if record.interval_number < 0:
                    raise ValidationError("Interval Number cannot less than 0")
    
    
    def send_email_and_wa(self,email_from,partner_name,partner_mobile,applicant_id,job_id,survey_id,applicant_object):
        wa_sender = waParam()
        email_sender = EmailParam()
        template = self.email_template_id
        data_pdf = {'survey':self,
                    'review':False,
                    # 'answer':stage_replace_id.survey_id.question_and_page_ids if stage_replace_id.survey_id.scoring_type != 'scoring_without_answers' else stage_replace_id.survey_id.question_and_page_ids.browse(),
                    'format_datetime': lambda dt: format_datetime(self.env, dt, dt_format=False),
                    'format_date': lambda date: format_date(self.env, date)
                    }
        pdf =  self.env.ref('equip3_hr_recruitment_extend.technical_test_template')._render_qweb_pdf([self.id],data_pdf)
        attachment = base64.b64encode(pdf[0])
        survey=self.env['survey.invite'].create({'survey_id':self.id,'emails':str(email_from),'template_id':template.id})
        send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment.send_by_email')
        context = self.env.context = dict(self.env.context)
        stage_before_id = self.env['job.stage.line'].search([('job_id', '=', applicant_object.job_id.id),('sequence', '<', applicant_object.stage_replace_id.sequence)], order='sequence desc',limit=1)
        survey_url = survey.survey_start_url+f"?surveyId={self.id}&applicantId={applicant_id}&jobPosition={job_id}"
        survey_latest = self.env['survey.user_input'].search([('applicant_id','=',applicant_id),('survey_id','=',survey_id)],order='id desc',limit=1)
        email_sender.set_email(email_from)
        email_sender.set_name(partner_name)
        email_sender.set_url_test(survey_url)
        email_sender.set_stage_now(applicant_object.stage_replace_id.stage_id.name)
        email_sender.set_stage_before(stage_before_id.stage_id.name if stage_before_id else False)
        email_sender.set_title(self.title)
        email_sender.set_recruiter_email(applicant_object.user_id.login if applicant_object.user_id else False)
        email_sender.set_recruiter_name(applicant_object.user_id.name if applicant_object.user_id else False)
        email_sender.set_company_id(applicant_object.job_id.company_id.name)
        email_sender.set_job_position(applicant_object.job_id.name)
        email_sender.set_work_location(applicant_object.job_id.custom_work_location_id.name)
        context.update(email_sender.get_context())
        if not survey_latest:
            if send_by_email and not self.is_manual_test:
                template.send_mail(applicant_id, force_send=True)
                template.with_context(context)
            if send_by_email and self.is_manual_test:
                    ir_values = {
                        'name': applicant_object.job_id.company_id.name+f"_{applicant_object.stage_replace_id.survey_id.title}" + '.pdf',
                        'type': 'binary',
                        'datas': attachment,
                        'store_fname': applicant_object.job_id.company_id.name+f"_{applicant_object.stage_replace_id.survey_id.title}",
                        'mimetype': 'application/x-pdf',
                    }
                    data_id = self.env['ir.attachment'].create(ir_values)
                    template = self.env.ref('equip3_hr_recruitment_extend.mail_template_manual_test',raise_if_not_found=True)
                    template.attachment_ids = [(5, 0, 0)]
                    template.attachment_ids = [(6, 0, [data_id.id])]
                    template.send_mail(applicant_object.id, force_send=True)
                    template.with_context(context)
            send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.send_by_wa')
            if send_by_wa and not self.is_manual_test:
                template = self.wa_template_id
                if template:
                    wa_sender.set_wa_string(template.message,template._name,template.id,
                                            domain = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.url'),
                                            token =self.env['ir.config_parameter'].sudo().get_param('qiscus.api.secret_key'),
                                            app_id=self.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid'),
                                            channel_id=self.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id'),
                                            name_space=self.env['ir.config_parameter'].sudo().get_param('qiscus.api.name_space'),
                                            template_name=self.env['ir.config_parameter'].sudo().get_param('qiscus.api.template_name')
                                            
                                            )
                    wa_sender.set_applicant_name(partner_name or '')
                    wa_sender.set_company(applicant_object.job_id.company_id.name)
                    wa_sender.set_survey_url(survey_url or '')
                    wa_sender.set_job(applicant_object.job_id.name)
                    wa_sender.set_stage_before_technical(stage_before_id.stage_id.name)
                    wa_sender.set_survey_name(self.title)
                    wa_sender.set_recruiter_email(applicant_object.user_id.login)
                    wa_sender.set_recruiter_name(applicant_object.user_id.name)
                    wa_sender.send_wa(partner_mobile)     
            if send_by_wa and self.is_manual_test:
                template = self.env.ref('equip3_hr_recruitment_extend.wa_template_3')
                if template:
                    wa_sender.set_wa_string(template.message,template._name,template.id,self.env['ir.config_parameter'].sudo().get_param('chat.api.url'),self.env['ir.config_parameter'].sudo().get_param('chat.api.token'))
                    wa_sender.set_applicant_name(applicant_object.partner_name)
                    wa_sender.set_survey_url(survey_url)
                    wa_sender.set_survey_name(self.title)
                    wa_sender.set_company(applicant_object.job_id.company_id.name)
                    wa_sender.set_job(applicant_object.job_id.name)
                    wa_sender.set_stage_before_technical(stage_before_id.stage_id.name)
                    wa_sender.set_recruiter_email(applicant_object.user_id.login)
                    wa_sender.set_recruiter_name(applicant_object.user_id.name)
                    wa_sender.send_wa(applicant_object.partner_mobile)
                    wa_sender.send_wa_file(applicant_object.partner_mobile,attachment,applicant_object.job_id.company_id.name+f"_{applicant_object.stage_replace_id.survey_id.title}" +'.pdf')
                    
    
    @api.model
    def _cron_auto_follow(self):
        job_stage_line = self.env['job.stage.line'].sudo().search([('survey_id','=',self.id)])
        if job_stage_line:
            for data_stage in job_stage_line:
                applicant_list = self.env['hr.applicant'].sudo().search([('shadow_stage_replace_id','=',data_stage.id),('job_id','=',data_stage.job_id.id)])
                if applicant_list:
                    for data_applicant in applicant_list:
                            if not data_applicant.is_auto_follow:
                                count = self.number_of_repetion - 1
                                query_statement = """UPDATE hr_applicant set  is_auto_follow  = TRUE, repetion_count = %s WHERE id  = %s """
                                self.sudo().env.cr.execute(query_statement, [count,data_applicant.id])
                                self.env.cr.commit()
                                email_from = data_applicant.email_from if data_applicant.email_from else False
                                partner_name = data_applicant.partner_name if data_applicant.partner_name else False
                                partner_mobile = data_applicant.partner_mobile if data_applicant.partner_mobile else False
                                applicant = data_applicant.id if data_applicant.id else False
                                job = data_applicant.job_id.id if data_applicant.job_id.id else False
                                applicant_object = data_applicant if data_applicant else False
                                self.send_email_and_wa(email_from,partner_name,partner_mobile,applicant,job,self.id,applicant_object)
                            elif data_applicant.is_auto_follow:
                                if data_applicant.repetion_count > 0:
                                    count = data_applicant.repetion_count -1
                                    applicant_object = data_applicant if data_applicant else False
                                    query_statement = """UPDATE hr_applicant set repetion_count = %s WHERE id  = %s """
                                    self.sudo().env.cr.execute(query_statement, [count,data_applicant.id])
                                    self.env.cr.commit()
                                    self.send_email_and_wa(data_applicant.email_from,data_applicant.partner_name,data_applicant.partner_mobile,data_applicant.id,data_applicant.job_id.id,self.id,applicant_object)
                                    
                           
                            
                    
    
    def unlink(self):
        for record in self:
            cron_to_delete = self.env['ir.cron'].search([('survey_id','=',record.id)])
            if cron_to_delete:
                cron_to_delete.unlink()
        res = super(hashMicroInheritSurveySurvey, self).unlink()
        return res
    
    @api.model
    def create(self, vals_list):
        res =  super(hashMicroInheritSurveySurvey,self).create(vals_list)
        if res.is_follow_up:
                interval = res.interval_number
                interval_type = res.interval_type
                delta_var = res.interval_type
                next_call = datetime.now() + eval(f'relativedelta({delta_var}={interval})')
                model = self.env['ir.model'].search([('model','=',self._name)])
                user_bot = self.env['res.users'].search([('id','=',1)])
                if model and user_bot:
                    cron = self.env['ir.cron'].create({'name':f"Cron Auto Follow {self.title}",
                                                    'model_id':model.id,
                                                    'user_id':user_bot.id,
                                                    'interval_number': interval,
                                                    'interval_type':interval_type,
                                                    'active':True,
                                                    'code':f"model.search([('id','=',{self.id})])._cron_auto_follow()",
                                                    'nextcall':next_call,
                                                    'numbercall':-1,
                                                    'survey_id':res.id
                                                    
                                                    })
        return res
    
    def write(self, vals):
        for rec in self:
            interval = vals['interval_number'] if 'interval_number' in vals else rec.interval_number
            interval_type = vals['interval_type'] if 'interval_type' in vals else rec.interval_type
            number_of_repetion =  vals['number_of_repetion'] if 'number_of_repetion' in vals else rec.number_of_repetion
            delta_var = vals['interval_type'] if 'interval_type' in vals else rec.interval_type
            if delta_var and interval:
                next_call = datetime.now() + eval(f'relativedelta({delta_var}={interval})')
            if 'is_follow_up' in vals:
                if vals['is_follow_up']:
                    ir_cron_auto_follow = self.env['ir.cron'].sudo().search([('survey_id','=',self.id)])
                    if not ir_cron_auto_follow:
                        model = self.env['ir.model'].search([('model','=',self._name)])
                        if model:
                            cron = self.env['ir.cron'].create({'name':f"Cron Auto Follow {rec.title}",
                                                            'model_id':model.id,
                                                            'user_id':1,
                                                            'interval_number': interval,
                                                            'interval_type':interval_type,
                                                            'active':True,
                                                            'code':f"model.search([('id','=',{rec.id})])._cron_auto_follow()",
                                                            'nextcall':next_call,
                                                            'numbercall':-1,
                                                            'survey_id':rec.id

                                                            })
                    if ir_cron_auto_follow:
                        ir_cron_auto_follow.write({'interval_number':interval,'interval_type':interval_type,'nextcall':next_call})
                        
                if not vals['is_follow_up']:
                    cron_to_delete = self.env['ir.cron'].search([('survey_id','=',rec.id)])
                    if cron_to_delete:
                        cron_to_delete.unlink()

            if rec.is_follow_up:
                cron_to_update = self.env['ir.cron'].search([('survey_id','=',rec.id)])
                if cron_to_update:
                    cron_to_update.write({'interval_number':interval,'interval_type':interval_type,'nextcall':next_call})
                    
        res =  super(hashMicroInheritSurveySurvey,self).write(vals)
        return res
    

