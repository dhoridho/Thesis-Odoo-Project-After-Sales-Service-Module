# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import os
from datetime import datetime, timedelta

import xlsxwriter
from odoo import api, fields, models, _
from odoo.modules import get_module_path
from odoo.exceptions import ValidationError
from lxml import etree


class HashmicroJob(models.Model):
    _inherit = "hr.job"
    applicant_question_ids = fields.One2many('question.job.position', 'job_id', "Applicant Question")
    stage_ids = fields.One2many('job.stage.line', 'job_id', "Stages")
    second_user_ids = fields.Many2many('res.users','user_list','user_id',compute="compute_second_user_ids")
    real_second_user_ids = fields.Many2many('res.users','user_list_real','user_id')
    aplicant_ids = fields.One2many('hr.applicant', 'job_id')
    user_ids = fields.Many2many('res.users', string="Recruiter")
    job_technical_ids = fields.One2many('job.technical.test.line', 'job_id', string="Recruiter")
    domain_stage_apply = fields.Many2many('hr.recruitment.stage',compute='domain_stage_apply_compute')
    default_reject_stage_id = fields.Many2one('hr.recruitment.stage', string="Initial Reject Stage")
    rejected_at_stage = fields.Char("Rejected at Stage")
    user_ids_hashgroup = fields.Many2many('res.users','user_flag','user_id',compute='hash_group_compute')
    question_job_position=fields.One2many('question.job.position','job_id','Job Position Question',readonly=False)
    global_question_job_position=fields.One2many('question.job.position','global_job_id','Job Position Question',compute='_get_global_question')
    question_job_position_ids=fields.One2many('question.job.position','hr_job_id','Job Position Question')
    is_use_mpp = fields.Boolean(compute='_is_use_mpp',store=True)
    expected_clone = fields.Integer()
    custom_work_location_id = fields.Many2one("work.location.object","Work Location")
    skill_ids = fields.Many2many('hr.skill.type', string='Skills Required')
    qualitative_question_ids = fields.One2many('qualitative.question','job_id')
    is_custom_sequence = fields.Boolean()
    minimum_weightage = fields.Integer(string='Minimum Applicant Score')
    department_id = fields.Many2one('hr.department', required=True)
    is_auto_next_stage = fields.Boolean("Auto Next Stage on Completion", default=False)
    is_setting_psychological_test = fields.Boolean(compute='_is_setting_psychological_test')
    is_use_ocr = fields.Boolean()
    participations_count = fields.Integer(compute="_get_participations_count")
    employee_to_recruit = fields.Integer('Employee TO Recruit', compute='_compute_employee_to_recruit')
    
    
    
    @api.model
    def create(self,vals):
        res = super(HashmicroJob,self).create(vals)
        if not res.question_job_position:
            res._get_global_question()
        return res
    
    
    @api.onchange('is_use_ocr')
    def _onchange_is_use_ocr(self):
        for data in self:
            if data.is_use_ocr:
                if data.question_job_position:
                    for line in data.question_job_position.filtered(lambda lines:lines.question.is_cv):
                        line.seq = 0
                        print("line.sequence")
                        print(line.seq)
    
    @api.depends('create_date')
    def _compute_employee_to_recruit(self):
        for record in self:
            employee_to_recruit = 0
            domain = [
                ('state', '=', 'approved'),
                ('job_id', '=', record.id),
                ('expected_join_date', '>=', datetime.today().date())
            ]
            manpower_plan_requisition = self.env['manpower.requisition'].search(domain)
            if manpower_plan_requisition:
                for mpr in manpower_plan_requisition:
                    employee_to_recruit += mpr.number_of_applicant
            else:
                employee_to_recruit += 0

            record.employee_to_recruit = employee_to_recruit
    
    @api.constrains('minimum_weightage')
    def _check_maximum_minimum_weightage(self):    
        if self.minimum_weightage > 100:
            raise ValidationError(_("The maximum of minimum weightage persentage must be 100%"))

    @api.onchange('question_job_position')
    def _onchange_question_job_position(self):
        # total_weightage = 0
        for record in self:
        #     if record.question_job_position:
        #         for question in record.question_job_position:
        #             total_weightage += question.weightage_percentage
        #             question.total_current_weightage = total_weightage
            total_weightage = sum(record.question_job_position.mapped('weightage_percentage'))
            record.question_job_position.update({'total_current_weightage': total_weightage})
        

    @api.constrains('question_job_position')
    def _check_maximum_weightage(self):
        total_weightage = 0
        for record in self:
            # if record.question_job_position:
            #     for question in record.question_job_position:
            #         total_weightage += question.weightage_percentage
            #         question.total_current_weightage = total_weightage
            total_weightage = sum(record.question_job_position.mapped('weightage_percentage'))
        
        if total_weightage != 1 and total_weightage != 0:
            raise ValidationError(_("The maximum of total weightage persentage must be 100%"))


    def name_get(self):
        result = []
        for record in self:
            # if self.env.context.get('requisition', False):
            #     result.append((record.id, "{} - {}".format(record.name, record.custom_work_location_id.name)))
            # else:
            result.append((record.id, record.name))
        return result

    
    def open_sequence(self):
        query_statement_order_line = """
                    SELECT id FROM question_job_position
                    WHERE job_id = %s AND show_in_job_portal IS TRUE OR hr_job_id = %s AND show_in_job_portal_specific_question IS TRUE  ORDER BY custom_seq ASC
                """
        self.env.cr.execute(query_statement_order_line, [self.id,self.id])
        question_ids = self._cr.dictfetchall()
        question_list_ids = [data['id'] for data in question_ids]
        question_to_append = self.env['question.job.position'].browse(question_list_ids)
        set_ids = []
        if question_to_append:
            for data in question_to_append:
                set_ids.append((0,0,{'sequence':data.custom_seq,'question_id':data.id}))
            
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Set Sequence',
            'res_model': 'set.sequence.job.wizard',
            # 'view_type': 'form',
            'view_mode': 'form',
            'target':'new',
            'domain': [],
            'context':{'default_question_ids':set_ids},
            
        }
        
    
    
    def ir_cron_recover_spesific_question(self):
        query_statement_question_line = """
                    UPDATE question_job_position set 
                    job_id = hr_job_id,
                    specific_question = question 
                    where job_id IS NULL
                """
        excecute = self.env.cr.execute(query_statement_question_line, [])
        print(excecute)
        
        
    def update_sequence(self,job):
        if job.question_job_position:
            seq = 0
            for data in job.question_job_position:
                seq +=1
                data.seq = seq
                
        
        
    
    def ir_cron_recover_sequence_question(self):
        job_list = self.env['hr.job'].search([])
        if job_list:
            for data in job_list:
                self.update_sequence(data)
                
    
     

            
    
    @api.depends('create_date')
    def _is_use_mpp(self):
        for record in self:
            expected = 0
            now = datetime.now()
            mpp_on = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp')   
            if mpp_on:
                record.is_use_mpp = True
                mpp_line = self.env['manpower.planning.line'].search([('job_position_id','=',record.id)])
                if mpp_line:
                    for data in mpp_line:
                        if data.manpower_id:
                            if now.date() <= data.manpower_id.mpp_period.end_period and data.manpower_id.state == 'approved':
                                expected += data.total_expected_new_employee
                record.expected_clone = expected
                record.no_of_recruitment = expected
            else:
                record.is_use_mpp = False
                
    
    
    def check_type(self,type):
        if type in ('multiple_choice_one_answer','multiple_choice_multiple_answer','drop_down_list','many2one'):
            question_type = "qualitative"
        elif type in ('round','date'):
            question_type = "quantitative"
        else:
            question_type = 'none'
        return question_type
    
        

    @api.depends('name')
    def _get_global_question(self):
        if self.name:
            questions = self.env['applicant.question'].search([('global_question','=',True)],order="sequence asc")
            questions_specific = self.env['applicant.question'].search([('global_specific_question','=',True)])
            global_question = []
            global_specific_question = []
            seq = 0
            if questions:
                for question in questions:
                    seq+=1
                    if question.is_employee_skill:
                        if question.question.lower() == "what is your expected salary?":
                            global_question.append((0,0,{'seq':seq,'question':question.id,'modify_question':question.modify_question,'mandatory':False,'show_in_job_portal':False,'remarks':'Remarks','question_type':'quantitative'}))
                        elif question.question.lower() == "what is your last drawn salary?":
                            global_question.append((0,0,{'seq':seq,'question':question.id,'modify_question':question.modify_question,'mandatory':True,'show_in_job_portal':False,'remarks':'Remarks','question_type':'quantitative'}))
                        elif question.question.lower() == "what is your date of birth?":
                            global_question.append((0,0,{'seq':seq,'question':question.id,'modify_question':question.modify_question,'mandatory':True,'show_in_job_portal':False,'remarks':'Remarks','question_type':'quantitative'}))
                        else:
                            global_question.append((0,0,{'seq':seq,'question':question.id,'modify_question':question.modify_question,'mandatory':True,'show_in_job_portal':False,'remarks':'Remarks'}))
                    
                    elif question.question == 'What is your phone number?':
                        global_question.append((0,0,{'seq':seq,'modify_question':question.modify_question,'question':question.id,'is_on_create':True,'mandatory':False,'show_in_job_portal':False,'is_on_create_job':True,'is_on_create_show':True}))
                    else:
                        global_question.append((0,0,{'seq':seq,'modify_question':question.modify_question,'question':question.id,'is_on_create':True,'mandatory':True,'show_in_job_portal':True,'is_on_create_job':True,'is_on_create_show':True}))

            self.global_question_job_position =global_question if global_question else False
            if not self.question_job_position:
                self.question_job_position = global_question
            
            elif self.question_job_position:
                question_job = [data.question.question for data in self.question_job_position]
                global_question_to_update = [data[2] for data in global_question]
                if questions:
                    if len(question_job) < len(questions):
                        for x in question_job:
                            self.write({'question_job_position': [(5, 0, 0)]})
                        
                        self.write({
                            'question_job_position': [(0, 0, values) for values in global_question_to_update]
                        })
                # for data_ques in self.question_job_position:
                #         data_ques.assign_question_type()
               
            if questions_specific:
                for question in questions_specific:
                    if question.type in ['multiple_choice_one_answer','drop_down_list','multiple_choice_multiple_answer']:
                        answer_data = []
                        if question.choices:
                            answer = str(question.choices).split(',')
                            for line_answer in answer:
                                answer_data.append((0,0,{'answer':line_answer}))
                        global_specific_question.append((0,0,{'question':question.id,'mandatory_specific_question':True,'show_in_job_portal_specific_question':True,'question_type':'qualitative','answers_ids':answer_data}))
                    elif question.type in ['many2one']:
                        degree = self.env[question.model_id.model].search([])
                        name_obj = degree._rec_name
                        answer_data = []
                        for line_answer in  degree:
                            answer_data.append((0,0,{'answer':line_answer[name_obj]}))
                        global_specific_question.append((0,0,{'question':question.id,'mandatory_specific_question':True,'show_in_job_portal_specific_question':True,'question_type':'qualitative','answers_ids':answer_data}))
                    elif question.type in ['text', 'text_area']:
                        global_specific_question.append((0,0,{'question':question.id,'mandatory_specific_question':True,'show_in_job_portal_specific_question':True,'question_type':'qualitative'}))
                    elif question.type in ['round', 'date']:
                        global_specific_question.append((0,0,{'question':question.id,'mandatory_specific_question':True,'show_in_job_portal_specific_question':True,'question_type':'quantitative'}))
                if not self.question_job_position_ids:
                    self.question_job_position_ids = global_specific_question
                    # for data in self.question_job_position_ids:
                    #     data.assign_question_type()
                    
                    
                
                
            
            if not self.stage_ids:
                stage_line = []
                not_suitable = self.env['hr.recruitment.stage'].search([('name', '=', 'Not Suitable')], limit=1)
                initial_qualification = self.env['hr.recruitment.stage'].search(
                    [('name', '=', 'Initial Qualification')], limit=1)
                shortlist_qualified_candidates = self.env['hr.recruitment.stage'].search(
                    [('name', '=', 'Shortlist Qualified Candidates')], limit=1)
                technical_test = self.env['hr.recruitment.stage'].search([('name', '=', 'Technical Test')], limit=1)
                first_interview = self.env['hr.recruitment.stage'].search([('name', '=', 'First Interview')], limit=1)
                second_interview = self.env['hr.recruitment.stage'].search([('name', '=', 'Second Interview')], limit=1)
                background_check = self.env['hr.recruitment.stage'].search([('name', '=', 'Background Check')], limit=1)
                offering_letter = self.env['hr.recruitment.stage'].search([('name', '=', 'Offering Letter')], limit=1)
                contract_signed = self.env['hr.recruitment.stage'].search([('name', '=', 'Contract Signed')], limit=1)
                rejected = self.env['hr.recruitment.stage'].search([('name', '=', 'Rejected')], limit=1)

                
                # if initial_qualification and rejected:
                #     stage_line.append((0, 0,
                #                        {'sequence': 1, 'is_apply_stage': True, 'stage_id': initial_qualification.id,
                #                         'stage_failed': rejected.id}))
                # if shortlist_qualified_candidates and rejected:
                #     stage_line.append((0, 0, {'sequence': 2, 'stage_id': shortlist_qualified_candidates.id,
                #                               'stage_failed': rejected.id}))
                # if technical_test and rejected:
                #     stage_line.append(
                #         (0, 0, {'sequence': 3, 'stage_id': technical_test.id, 'stage_failed': rejected.id}))
                # if first_interview and rejected:
                #     stage_line.append(
                #         (0, 0, {'sequence': 4, 'stage_id': first_interview.id, 'stage_failed': rejected.id}))
                # if second_interview and rejected:
                #     stage_line.append(
                #         (0, 0, {'sequence': 5, 'stage_id': second_interview.id, 'stage_failed': rejected.id}))
                # if background_check and rejected:
                #     stage_line.append(
                #         (0, 0, {'sequence': 6, 'stage_id': background_check.id, 'stage_failed': rejected.id}))
                # if offering_letter and rejected:
                #     stage_line.append(
                #         (0, 0, {'sequence': 7, 'stage_id': offering_letter.id, 'stage_failed': rejected.id}))
                # if contract_signed and rejected:
                #     stage_line.append(
                #         (0, 0, {'sequence': 8, 'stage_id': contract_signed.id, 'stage_failed': rejected.id}))
                    
                    
                # if not_suitable and rejected:
                #     self.default_reject_stage_id = not_suitable.id
                #     stage_line.append((0, 0, {'sequence': 9, 'stage_id': not_suitable.id, 'stage_failed': rejected.id}))
                    
                # if rejected:
                #     self.default_reject_stage_id = not_suitable.id
                #     stage_line.append((0, 0, {'sequence': 10, 'stage_id': rejected.id}))
                
                
                seq = 0
                stage_ids = self.env['hr.recruitment.stage'].search([('is_global','=',True)])
                if stage_ids:
                    for stage in stage_ids:
                        seq+= 1
                        stage_line.append((0,0,{'sequence':seq,'stage_id': stage.id, 'stage_failed': rejected.id}))
                    
                self.stage_ids = stage_line
                
        else:
            self.global_question_job_position = False

# fix the javascript not the python !!!
    def get_menu(self):
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            views = [(self.env.ref('hr_recruitment.view_hr_job_kanban').id, 'kanban'),
                         (self.env.ref('hr.view_hr_job_form').id, 'form')]
            return {
            'type': 'ir.actions.act_window',
            'name': 'Job Positions',
            'res_model': 'hr.job',
            'view_type': 'kanban,form',
            'view_mode': 'kanban',
            'views': views,
            'domain': [('real_second_user_ids','in',self.env.user.id)]
        }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') and not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            views = [(self.env.ref('hr_recruitment.view_hr_job_kanban').id, 'kanban'),
                         (self.env.ref('hr.view_hr_job_form').id, 'form')]
            return {
            'type': 'ir.actions.act_window',
            'name': 'Job Positions',
            'res_model': 'hr.job',
            'view_type': 'kanban,form',
            'view_id': False,
            'views': views,
             'view_mode': 'kanban,form',
           'context':{'default_user_ids':[(4,self.env.user.id)]},
            'domain': [('user_ids','in',self.env.user.id)]
        }
        elif self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            views = [(self.env.ref('hr_recruitment.view_hr_job_kanban').id, 'kanban'),
                         (self.env.ref('hr.view_hr_job_form').id, 'form')]
            return {
            'type': 'ir.actions.act_window',
            'name': 'Job Positions',
            'res_model': 'hr.job',
            'view_type': 'kanban,form',
            'view_id': False,
            'views': views,
            'view_mode': 'kanban,form',
           'context':{'default_user_ids':[(4,self.env.user.id)]},
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(HashmicroJob, self).fields_view_get(
            view_id=view_id, view_type=view_type)
        
        if self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') or self.env.user.has_group('hr.group_hr_manager') or self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_director'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_manager') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_director'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else :
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    
    def compute_second_user_ids(self):
        for record in self:
            data = []
            if record.stage_ids:
                for user_stage in record.stage_ids:
                    for user in user_stage.user_ids:
                        data.append(user.id)
                record.second_user_ids = [(6,0,data)]
                record.real_second_user_ids = [(6,0,data)]
            else:
                record.second_user_ids = False          
                record.real_second_user_ids = False          
    
    
    
    def hash_group_compute(self):
        for record in self:
            if record.name:
                user=self.env['res.users'].search([])
                if user:
                    list = []
                    data = [line.id for line in user.filtered(lambda line:line.has_group('hr_recruitment.group_hr_recruitment_user'))]
                    list.extend(data)
                    if data:
                        record.user_ids_hashgroup = [(6,0,list)]
                    else:
                        record.user_ids_hashgroup = False
                else:
                    record.user_ids_hashgroup = False
    


    def write(self, vals):
        if 'stage_ids' in vals:
            stage_ids = vals.get('stage_ids', [])
            existing_stage_ids = self.stage_ids.mapped('stage_id.id')
            new_stage_ids = [stage[2]['stage_id'] for stage in stage_ids if stage[0] == 0]
            duplicate_ids = set(new_stage_ids) & set(existing_stage_ids)
            if duplicate_ids:
                raise ValidationError("Stage's name must be unique!")

        return super(HashmicroJob, self).write(vals)

    @api.constrains('stage_ids')
    def _constraint_stage_ids(self):
        for record in self:
            if record.stage_ids:
                if len(record.stage_ids.filtered(lambda line:line.is_apply_stage)) > 1:
                    raise ValidationError("Apply stage can't more than one")
                if len(record.stage_ids.filtered(lambda line:line.is_final_stage)) > 1:
                    raise ValidationError("Final stage can't more than one")


    def domain_stage_apply_compute(self):
        for record in self:
            if record.stage_ids:
                list_stage= []
                stage = [data.stage_id.id for data in record.stage_ids]
                list_stage.extend(stage)
                record.domain_stage_apply = [(6,0,list_stage)]
            else:
                record.domain_stage_apply = False






    @api.model
    def default_get(self, fields):
        res = super(HashmicroJob, self).default_get(fields)
        stage_line = []
        initial_qualification = self.env['hr.recruitment.stage'].search([('name', '=', 'Initial Qualification')],limit=1)
        shortlist_qualified_candidates = self.env['hr.recruitment.stage'].search([('name', '=', 'Shortlist Qualified Candidates')],limit=1)
        technical_test = self.env['hr.recruitment.stage'].search([('name', '=', 'Technical Test')],limit=1)
        first_interview = self.env['hr.recruitment.stage'].search([('name', '=', 'First Interview')],limit=1)
        second_interview = self.env['hr.recruitment.stage'].search([('name', '=', 'Second Interview')],limit=1)
        background_check = self.env['hr.recruitment.stage'].search([('name', '=', 'Background Check')],limit=1)
        offering_letter = self.env['hr.recruitment.stage'].search([('name', '=', 'Offering Letter')],limit=1)
        contract_signed = self.env['hr.recruitment.stage'].search([('name', '=', 'Contract Signed')],limit=1)
        rejected = self.env['hr.recruitment.stage'].search([('name', '=', 'Rejected')],limit=1)
        not_suitable = self.env['hr.recruitment.stage'].search([('name', '=', 'Not Suitable')],limit=1)
        
        user=self.env['res.users'].search([])
        if user:
            list = []
            data = [line.id for line in user.filtered(lambda line:line.has_group('hr.group_hr_user'))]
            list.extend(data)
            if data:
                res['user_ids_hashgroup'] = [(6,0,list)]
            else:
                res['user_ids_hashgroup'] = False
        else:
            res['user_ids_hashgroup'] = False
        seq = 0
        stage_ids = self.env['hr.recruitment.stage'].search([('is_global','=',True)])
        if stage_ids:
            for stage in stage_ids:
                seq+= 1
                stage_line.append((0,0,{'sequence':seq,'stage_id': stage.id, 'stage_failed': rejected.id,'is_apply_stage':stage.is_first_stage,'is_final_stage':stage.is_final_stage}))
                

        # if initial_qualification and rejected:
        #     stage_line.append((0,0,{'sequence': 1, 'is_apply_stage':True,'stage_id': initial_qualification.id, 'stage_failed': rejected.id}))
        # if shortlist_qualified_candidates and rejected:
        #     stage_line.append((0,0,{'sequence': 2, 'stage_id': shortlist_qualified_candidates.id,'stage_failed': rejected.id}))
        # if technical_test and rejected:
        #     stage_line.append((0,0,{'sequence': 3, 'stage_id': technical_test.id,'stage_failed': rejected.id}))
        # if first_interview and rejected:
        #     stage_line.append((0,0,{'sequence': 4, 'stage_id': first_interview.id,'stage_failed': rejected.id}))
        # if second_interview and rejected:
        #     stage_line.append((0,0,{'sequence': 5, 'stage_id': second_interview.id, 'stage_failed': rejected.id}))
        # if background_check and rejected:
        #     stage_line.append((0,0,{'sequence': 6, 'stage_id': background_check.id, 'stage_failed': rejected.id}))
        # if offering_letter and rejected:
        #     stage_line.append((0,0,{'sequence': 7, 'stage_id': offering_letter.id, 'stage_failed': rejected.id}))
        # if contract_signed and rejected:
        #     stage_line.append((0,0,{'sequence': 8, 'stage_id': contract_signed.id, 'stage_failed': rejected.id}))
        # if not_suitable and rejected:
        #     res['default_reject_stage_id']  = not_suitable.id
        #     stage_line.append((0,0,{'sequence':9,'stage_id':not_suitable.id,'stage_failed':rejected.id}))
        # if rejected:
        #     stage_line.append((0, 0, {'sequence': 10, 'stage_id': rejected.id}))
        
        
        
        
        
        res['stage_ids'] = stage_line





        return res


    def select_stage(self):
        self.ensure_one()
        if self.stage_ids:
            for record in self.stage_ids:
                if record.aplicant_ids:
                    record.send_notificaion_email()





    def send_email(self):
        self.ensure_one()
        for record in self.user_ids:
            context = self.env.context = dict(self.env.context)
            context.update({
                'email_to': record.email,
                'name': record.name,
                'job_position': self.name
            })
            template = self.env.ref('equip3_hr_recruitment_extend.mail_template_applicant_list')
            module_path = get_module_path('equip3_hr_recruitment_extend')
            fpath = module_path + '/generated_files'
            if not os.path.isdir(fpath):
                os.mkdir(fpath)
            workbook = xlsxwriter.Workbook(
                module_path + '/generated_files/' + f'applicant-{self.name}' + '.xlsx')
            worksheet = workbook.add_worksheet()
            bold = workbook.add_format({
                'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            centerformmat = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
            })

            worksheet.write('A1', 'Name', bold)
            worksheet.write('B1', 'Job Position', bold)
            worksheet.write('C1', 'Email', bold)
            worksheet.write('D1', 'State', bold)
            row = 0
            col = 0
            worksheet.set_column(0, 5, 17)

            for applicant in self.aplicant_ids:
                row += 1
                worksheet.write(row, col, applicant.partner_name, centerformmat)
                worksheet.write(row, col + 1, applicant.name, centerformmat)
                worksheet.write(row, col + 2, applicant.email_from, centerformmat)
                worksheet.write(row, col + 3, applicant.stage_id.name, centerformmat)
            workbook.close()
            csv_filename = f'applicant-{self.name}' + '.xlsx'
            with open(module_path + '/generated_files/' + csv_filename, 'rb') as opened_file:
                base64_csv_file = base64.b64encode(opened_file.read())
                attachment = self.env['ir.attachment'].create({
                    'name': csv_filename,
                    'type': 'binary',
                    'datas': base64_csv_file
                })
            template.attachment_ids = [(5, 0, 0)]
            template.attachment_ids = [(4, attachment.id)]
            template.send_mail(self.id, force_send=True)
            template.with_context(context)

            notification_ids = [((0, 0, {
                'res_partner_id': record.partner_id.id,
                'notification_type': 'inbox'}))]

            self.message_post(
                body=f"Hello {record.name} \n"
                     f" You have some applicants that already have been applied to your opening Job Position {self.name} on Portal",
                message_type='notification',
                author_id=self.env.user.partner_id.id,
                partner_ids=[record.partner_id.id],
                attachment_ids=[attachment.id],
                needaction_partner_ids=[record.partner_id.id],
                notification_ids=notification_ids
            )

    def ir_cron_send_notification(self):
        query_params = []
        query_statement = """SELECT id FROM hr_job"""
        self.env.cr.execute(query_statement, query_params)
        hr_job_query = self._cr.fetchall()
        hr_job_ids = [id[0] for id in hr_job_query]
        hr_job = self.env['hr.job'].browse(hr_job_ids)
        yesterday = (datetime.today() - timedelta(days=1)).strftime('%d-%m-%Y')
        for record in hr_job:
            if record.aplicant_ids.filtered(lambda line: line.aplicant_create_date.strftime('%d-%m-%Y') == yesterday):
                record.send_email()
            record.select_stage()
    
    def _cron_delete_false_stages(self):
        jobs = self.env['hr.job'].search([])
        for job in jobs:
            stages = self.env['job.stage.line'].search([
                ('job_id', '=', job.id),
                ('stage_id', '=', False)
            ])
            stages.unlink()
    

    # @api.onchange('user_ids')
    # def onchange_user_ids(self):
    #     for stage in self.stage_ids:
    #         stage.user_ids = self.user_ids.ids

    def _is_setting_psychological_test(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.is_auto_next_stage_psychological')
            setting_by_psychological_test = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.auto_completion_on_psychological')
            if setting:
                if setting_by_psychological_test == 'by_psychological_test':
                    rec.is_setting_psychological_test = True
                else:
                    rec.is_setting_psychological_test = False
            else:
                rec.is_setting_psychological_test = True


    @api.onchange('is_auto_next_stage')
    def onchane_is_auto_next_stage(self):
        surveys_to_update = self.filtered(lambda r: r.is_auto_next_stage and any(
            survey.category_id.name == 'Personality & Emotional Inventory' for survey in r.stage_ids.survey_id))

        surveys_to_update.sudo().mapped('stage_ids.survey_id').write({'is_auto_next_stage': True})
        (self - surveys_to_update).sudo().mapped('stage_ids.survey_id').write({'is_auto_next_stage': False})

    def _get_participations_count(self):
        for rec in self:
            participations = self.env['survey.user_input'].search([('active', '=', True), ('job_id', 'in', rec.ids), ('survey_type', '!=', 'INTERVIEW')])
            for part_rec in participations:
                if rec.id == part_rec.job_id.id:
                    part_rec.is_all_test_result = True
                for stages in rec.stage_ids:
                    if stages.survey_id and stages.survey_id == part_rec.survey_id:
                        part_rec.min_qualification = stages.min_qualification
            query_update = _("UPDATE survey_user_input SET is_all_test_result=False, min_qualification = 0.0  WHERE job_id!=%s") % (int(rec.id))
            self._cr.execute(query_update)
            participation_count = len(participations)
            rec.participations_count = participation_count