from dataclasses import field
from datetime import datetime,timedelta
from odoo import models,api,fields,_
from lxml import etree
from odoo.exceptions import UserError, ValidationError


class HashmicroJobRecruitmentStage(models.Model):
    _name = 'hr.recruitment.stage'
    _inherit = ['hr.recruitment.stage','mail.thread','mail.activity.mixin']
    connector_id = fields.Many2one('acrux.chat.connector')
    template_wa_id = fields.Many2one('wa.template.message')
    new_template_wa_id = fields.Many2one('master.template.message')
    
    is_global = fields.Boolean()
    is_masterdata = fields.Boolean()
    is_first_stage = fields.Boolean('First Stage', default=False)
    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', 'Refuse Reason')
    refuse_template_id = fields.Many2one('mail.template', string='Refuse Template')
    is_follow_up = fields.Boolean(default=False)
    email_template_id = fields.Many2one('mail.template')
    wa_template_id = fields.Many2one('wa.template.message')
    new_wa_template_id = fields.Many2one('master.template.message')
    interval_number = fields.Integer()
    interval_type = fields.Selection([('minutes','Minutes'),('hours','Hours'),('days','Days'),('weeks','Weeks'),('months','Months')])
    number_of_repetion = fields.Integer()
    offering_letter_template_id = fields.Many2one('hr.offering.letter', string='Offering Letter Template')
    is_final_stage = fields.Boolean('Final Stage', default=False)
    
    
    
    @api.model
    def _cron_auto_follow(self):
        job_stage_line = self.env['job.stage.line'].sudo().search([('stage_id','=',self.id)])
        if job_stage_line:
            for data_stage in job_stage_line:
                if data_stage.interview_id:
                    applicant_list = self.env['hr.applicant'].sudo().search([('shadow_stage_replace_id','=',data_stage.id),('job_id','=',data_stage.job_id.id)])
                    if applicant_list:
                        for data_applicant in applicant_list:
                            data_applicant.reminder_invitation_interview(self.number_of_repetion)
    
    
    def create_auto_follow_up(self,res):
        if res.is_follow_up:
                interval = res.interval_number
                interval_type = res.interval_type
                delta_var = res.interval_type
                delta_var = 'month' if delta_var == 'months' else delta_var
                next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                model = self.env['ir.model'].search([('model','=',res._name)])
                if model:
                    cron = self.env['ir.cron'].create({'name':f"Cron Auto Follow {res.name}",
                                                    'model_id':model.id,
                                                    'user_id':1,
                                                    'interval_number': interval,
                                                    'interval_type':interval_type,
                                                    'active':True,
                                                    'code':f"model.search([('id','=',{res.id})])._cron_auto_follow()",
                                                    'nextcall':next_call,
                                                    'numbercall':-1,
                                                    'survey_id':res.id
                                                    
                                                    })
    
    
    def write_auto_follow_up(self,rec,vals):
        interval = vals['interval_number'] if 'interval_number' in vals else rec.interval_number
        interval_type = vals['interval_type'] if 'interval_type' in vals else rec.interval_type
        delta_var = vals['interval_type'] if 'interval_type' in vals else rec.interval_type
        delta_var = 'month' if delta_var == 'months' else delta_var
        if delta_var and interval:
            next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
        if 'is_follow_up' in vals:
            if vals['is_follow_up']:
                model = self.env['ir.model'].search([('model','=',self._name)])
                if model:
                    cron = self.env['ir.cron'].create({'name':f"Cron Stage Auto Follow {rec.name}",
                                                    'model_id':model.id,
                                                    'user_id':1,
                                                    'interval_number': interval,
                                                    'interval_type':interval_type,
                                                    'active':True,
                                                    'code':f"model.search([('id','=',{rec.id})])._cron_auto_follow()",
                                                    'nextcall':next_call,
                                                    'numbercall':-1,
                                                    'stage_id':rec.id

                                                    })
            if not vals['is_follow_up']:
                cron_to_delete = self.env['ir.cron'].search([('stage_id','=',rec.id)])
                if cron_to_delete:
                    cron_to_delete.unlink()
        if rec.is_follow_up:
            cron_to_update = self.env['ir.cron'].search([('stage_id','=',rec.id)])
            if cron_to_update:
                cron_to_update.write({'interval_number':interval,'interval_type':interval_type,'nextcall':next_call})
    
    def write(self, vals):
        if 'is_global' in vals:
            if vals['is_global'] == True:
                job_global = self.env['hr.job'].search([])
                if job_global:
                    for data_job in job_global:
                        job_global_updt = data_job.stage_ids.filtered(lambda line:line.stage_id.id == self.id)
                        if not job_global_updt:
                            last_seq = [data.sequence for data in data_job.stage_ids]
                            if last_seq:
                                data_job.stage_ids = [(0,0,{'stage_id':self.id,'sequence':max(last_seq)+1})]
                            else:
                                data_job.stage_ids = [(0,0,{'stage_id':self.id,'sequence':1})]
            if not vals['is_global']:
                job_global = self.env['hr.job'].search([])
                if job_global:
                    for data_job in job_global:
                        job_global_updt = data_job.stage_ids.filtered(lambda line:line.stage_id.id == self.id)
                        if job_global_updt:
                            line_to_del = []
                            for line_del in job_global_updt:
                                line_to_del.append((2,line_del.id))
                            data_job.stage_ids = line_to_del
                            applicant = self.env['hr.applicant'].search([('job_id','=',data_job.id),('stage_id','=',self.id)])
                            if applicant:
                                for applicant_to_update in applicant:
                                    applicant_to_update.stage_id = False
                                    applicant_to_update.stage_replace_id = False
               
        
        if 'job_ids' in vals:
            try:
                jobs_ids = vals['job_ids'][0][2]
                if jobs_ids:
                    for job in jobs_ids:
                        job = self.env['hr.job'].search([('id','=',job)])
                        if job:
                            job_to_update = job.stage_ids.filtered(lambda line:line.stage_id.id == self.id)
                            if not job_to_update:
                                last_seq = [data.sequence for data in job.stage_ids]
                                if last_seq:
                                    job.stage_ids = [(0,0,{'stage_id':self.id,'sequence':max(last_seq)+1})]
                                else:
                                    job.stage_ids = [(0,0,{'stage_id':self.id,'sequence':1})]
                old_job_ids = self.job_ids.ids
                for old_job in old_job_ids:
                    if old_job not in jobs_ids:
                        job_tp_delete = self.env['hr.job'].search([('id','=',old_job)])
                        stage_to_delete = job_tp_delete.stage_ids.filtered(lambda line:line.stage_id.id == self.id)
                        stage_del_ids = []
                        if stage_to_delete:
                            applicant = self.env['hr.applicant'].search([('job_id','=',old_job),('stage_id','=',self.id)])
                            if applicant:
                                for applicant_to_update in applicant:
                                    applicant_to_update.stage_id = False
                                    applicant_to_update.stage_replace_id = False
                                    
                            for data_to_del in stage_to_delete:
                                stage_del_ids.append((2,data_to_del.id))
                            job_tp_delete.stage_ids = stage_del_ids
            except IndexError:
                pass

        if 'is_first_stage' in vals and vals.get('is_first_stage') == True and self.search([('is_first_stage', '=', True), ('id', '!=', vals.get('id'))], limit=1):
            raise ValidationError(_('First stage must be in one record only!'))
        if 'is_first_stage' in vals and vals.get('is_first_stage') == True:
            stage_line = self.env['job.stage.line'].search([('is_apply_stage','=',True)])
            if stage_line:
                for data_stage in stage_line:
                    data_stage.is_apply_stage = False
            stage_line_to_update = self.env['job.stage.line'].search([('stage_id','=',self.id)])
            if stage_line_to_update:
                for data_stage_update in stage_line_to_update:
                    data_stage_update.is_apply_stage = True
        if 'is_first_stage' in vals and vals.get('is_first_stage') == False:
            stage_line_to_update = self.env['job.stage.line'].search([('stage_id','=',self.id),('is_apply_stage','=',True)])
            if stage_line_to_update:
                for data_stage_update in stage_line_to_update:
                    data_stage_update.is_apply_stage = False
        self.write_auto_follow_up(self,vals)
        res = super(HashmicroJobRecruitmentStage,self).write(vals)
        return res
    
    @api.model
    def create(self, vals_list):
        res =  super(HashmicroJobRecruitmentStage,self).create(vals_list)
        # I commented this code to make the stage_ids not updated after creating new stage
        # because it will be an undefine or false stage after creating new stage.
        # If the undfine or false stage added to the stage_ids, user will not able to create
        # new applicant, cannot set applied job.

        # if not res.is_masterdata:
        #     if res.is_global:
        #         job_global = self.env['hr.job'].search([])
        #         if job_global:
        #             for data_job in job_global:
        #                 job_global_updt = data_job.stage_ids.filtered(lambda line:line.stage_id.id == res.id)
        #                 if not job_global_updt:
        #                     last_seq = [data.sequence for data in data_job.stage_ids]
        #                     data_job.stage_ids = [(0,0,{'stage_id':self.id,'sequence':max(last_seq)+1})]
        self.create_auto_follow_up(res)  
        if res.job_ids:
            try:
                jobs_ids = res.job_ids
                if jobs_ids:
                    for job in jobs_ids:
                        job = self.env['hr.job'].search([('id','=',job.id)])
                        if job:
                            job_to_update = job.stage_ids.filtered(lambda line:line.stage_id.id == self.id)
                            if not job_to_update:
                                last_seq = [data.sequence for data in job.stage_ids]
                                job.stage_ids = [(0,0,{'stage_id':res._origin.id,'sequence':max(last_seq)})]
            except IndexError:
                pass
        if res.is_first_stage:
            if self.search([('is_first_stage', '=', True), ('id', '!=', res.id)]):
                raise ValidationError(_('First stage must be in one record only!'))
            
            stage_line = self.env['job.stage.line'].search([('is_apply_stage','=',True)])
            if stage_line:
                for data_stage in stage_line:
                    data_stage.is_apply_stage = False
            stage_line_to_update = self.env['job.stage.line'].search([('stage_id','=',self.id)])
            if stage_line_to_update:
                for data_stage_update in stage_line_to_update:
                    data_stage_update.is_apply_stage = True
            
        
        return res
    
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(HashmicroJobRecruitmentStage, self).fields_view_get(
            view_id=view_id, view_type=view_type)
        if  not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res


    @api.constrains('name')
    def _check_unique_stages(self):
        for record in self:
            count_record = self.search_count([('name', '=', record.name)])
            if count_record > 1:
                raise models.ValidationError("Stage's name must be unique!") 