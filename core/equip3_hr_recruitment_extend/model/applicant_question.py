from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from numpy import require
from odoo import models, fields, api, SUPERUSER_ID,_
from odoo.exceptions import ValidationError
from lxml import etree
from odoo.http import request
import werkzeug,requests

class ApplicantQuestion(models.Model):
    _name='applicant.question'
    _rec_name = 'question'
    _order = 'sequence asc'

    
    sequence = fields.Integer()
    question=fields.Char('Question')
    modify_question = fields.Char("Modify Question")
    type=fields.Selection([
        ('text', "Textfield"),
        ('round', "Round Number"),
        ('decimal', "Decimal Number"),
        ('drop_down_list', "Multiple choice: only one answer (dropdown)"),
        ('multiple_choice_one_answer', "Multiple choice: only one answer (radio)"),
        ('multiple_choice_multiple_answer', "Multiple choice: multiple answers allowed"),
        ('file', "File"),
        ('headline', "Headline"),
        ('many2one', "Dropdown of Other Object"),
        # ('table', "Table"),
        ('headline', "Headline"),
        ('text_area', "Text Area"),
        ('date', "Date"),
        ('description', "Description")
        ], string="Type", default="text")
    domain = fields.Char(string="Filter Domain")
    is_past_experience = fields.Boolean()
    is_employee_skill = fields.Boolean()
    choices=fields.Text('Choices')
    internal_remarks=fields.Text('Internal Remarks')
    description = fields.Text('Description')
    file_size = fields.Integer('File Size')
    test = fields.Boolean("test")
    pdf = fields.Boolean("pdf", default=True)
    xls = fields.Boolean("xls", default=True)
    rar = fields.Boolean("rar", default=True)
    doc = fields.Boolean("doc", default=True)
    xlsx = fields.Boolean("xlsx", default=True)
    docx = fields.Boolean("docx", default=True)
    jpg = fields.Boolean("jpg")
    zip = fields.Boolean("zip", default=True)
    png = fields.Boolean("png")
    mp4 = fields.Boolean("Mp4")
    applicant_question_ids = fields.One2many('question.job.position', 'question', "Applicant Question")
    model_id = fields.Many2one('ir.model',string='Model')
    global_question = fields.Boolean('Global Question', default=False)
    is_email = fields.Boolean("Email Validation")
    is_readonly = fields.Boolean(default=False)
    global_specific_question = fields.Boolean('Global Specific Question', default=False)
    job_ids = fields.Many2many('hr.job', string='Add to Specific Jobs')
    is_cv = fields.Boolean()
    is_email_question = fields.Boolean()
    is_phn_number = fields.Boolean()
    is_name = fields.Boolean()
    is_nik = fields.Boolean()
    
    @api.model
    def create(self,values):
        res = super(ApplicantQuestion, self).create(values)
        last_sequence = self.search([])
        if last_sequence:
            max_seq =  max([data.sequence for data in last_sequence]) + 1
        else:
            max_seq = 1
        res.sequence = max_seq
        if res.global_question and not res.is_readonly:
            job = self.env['hr.job'].search([])
            if job:
                for job_record in job:
                    seq = 0
                    if job_record.question_job_position.filtered(lambda line:line.question.id != res.id):
                        seq = max([data.seq for data in job_record.question_job_position])
                    job_record.question_job_position = [(0,0,{'question':res.id,'seq':seq})]
        if res.job_ids and not res.global_question:
            job_ids = self.env['hr.job'].browse(res.job_ids.ids)
            if job_ids:
                for job_record in job_ids:
                    seq = 0
                    if job_record.question_job_position.filtered(lambda line: line.question.id != res.id):
                        seq = max([data.seq for data in job_record.question_job_position])
                    job_record.question_job_position = [(0, 0, {'question': res.id, 'seq': seq})]
        return res
    
    def write(self, vals):
        if 'global_question' in vals:
            if vals['global_question'] and not self.is_readonly:
                job = self.env['hr.job'].search([])
                if job:
                    for job_record in job:
                        seq = 0
                        if job_record.question_job_position.filtered(lambda line:line.question.id != self.id):
                            seq = max([data.seq for data in job_record.question_job_position])
                        job_record.question_job_position = [(0,0,{'question':self.id,'seq':seq})]
        if 'job_ids' in vals and not self.global_question:
            job_ids = self.env['hr.job'].browse(vals.get('job_ids')[0][2])
            if job_ids:
                for job_record in job_ids:
                    seq = 0
                    existing_mapping = job_record.question_job_position.filtered(lambda line: line.question.id == self.id)
                    if not existing_mapping:
                        seq = max([data.seq for data in job_record.question_job_position])
                        job_record.question_job_position = [(0, 0, {'question': self.id, 'seq': seq})]
        return super(ApplicantQuestion,self).write(vals)

    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(ApplicantQuestion, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=True)
        if  not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    # def unlink(self):
    #     for record in self:
    #         if record.global_question:
    #             raise ValidationError("You can't delete / remove this question")
    #     res = super(ApplicantQuestion, self).unlink()
    #     return res
    
    def get_value_dropdown(self):
        list = []
        if self.choices:
            list.extend(str(self.choices).split(','))
        return list
            
            


    def get_data_model(self):
        if self.model_id and not self.domain:
            data=self.env[str(self.model_id.model)].search([])
            return data
        if self.model_id and self.domain:
            domain = self.domain
            data=self.env[str(self.model_id.model)].search([eval(domain)])
            return data

    def get_data_multiple_choice_one_answer(self):
        if self.type in ('multiple_choice_one_answer','multiple_choice_multiple_answer'):
            answer = str(self.choices).split(',')
            return answer


    
    @api.onchange('type')
    def set_fields(self):
        if self.type == 'file':
            self.write({
                'pdf': True,
                'xls': True,
                'rar': True,
                'doc': True,
                'xlsx': True,
                'docx': True,
                'zip': True,
                'file_size': 5,
            })
        else:
            self.write({
                'pdf': False,
                'xls': False,
                'rar': False,
                'doc': False,
                'xlsx': False,
                'docx': False,
                'jpg': False,
                'zip': False,
                'png': False,
                'file_size': 0,
            })


                    
class QuestionJobPosition(models.Model):
    _name='question.job.position'
    _order = "seq"
    _rec_name = "question"

    seq=fields.Integer('Sequence')
    custom_seq =  fields.Integer()
    modify_question = fields.Char("Modify Question")
    question=fields.Many2one('applicant.question')
    specific_question=fields.Many2one('applicant.question')
    question_string =  fields.Char(related='question.question')
    mandatory=fields.Boolean('Mandatory',default=True)
    show_in_job_portal=fields.Boolean('Show In Job Portal',default=True)
    mandatory_specific_question = fields.Boolean('Mandatory',default=True)
    show_in_job_portal_specific_question = fields.Boolean('Show In Job Portal',default=True)
    remarks=fields.Text('Remarks')
    min_qualification = fields.Float("Minimum Qualification")
    job_id=fields.Many2one('hr.job')
    hr_job_id=fields.Many2one('hr.job')
    global_job_id=fields.Many2one('hr.job')
    global_question = fields.Boolean('Global Question',related='question.global_question')
    question_type = fields.Selection([('none','None'),('qualitative','Qualitative'),('quantitative','Quantitative')],default='none',string="Validation Type")
    answers_ids = fields.One2many('qualitative.question','question_job_id')
    answers_masking_ids = fields.One2many('qualitative.question','question_job_masking_id')
    answers_m2m_ids = fields.Many2many('qualitative.question')
    range_from = fields.Float()
    range_to = fields.Float()
    is_hide = fields.Boolean()
    is_readonly_tree = fields.Boolean()
    is_on_create = fields.Boolean()
    is_on_create_job = fields.Boolean(default=False)
    is_on_create_show = fields.Boolean(default=False)
    weightage = fields.Integer(string="Weightage Score")
    weightage_percentage = fields.Float(string='Weightage Percentage', store=True)
    total_current_weightage = fields.Float(string='Total Current Weightage', store=True)
    
    
    # @api.onchange('seq')
    # def _onchange_seq(self):
    #     for data in self:
    #         if data.seq:
    #             if data.job_id.is_use_ocr:
    #                 print("hereeee")
    #                 print(data.job_id.is_use_ocr)
    #                 print(data.question.is_cv)
    #                 if data.question.is_cv:
    #                     if data.seq != 0:
    #                         raise ValidationError("CV question on ocr must at first !")
                    

    @api.onchange('weightage', 'question_type')
    def _onchange_get_weightage_percentage(self):
        for record in self:
            if record.weightage:
                if record.question_type == 'none':
                    record.weightage = 0
                    record.weightage_percentage = 0
                else:
                    if record.weightage < 0:
                        raise ValidationError("Please do not insert value lower than 0 and must not in decimals!")
                    else:
                        record.weightage_percentage = record.weightage / 100
            else:
                record.weightage_percentage = 0
    
    @api.onchange('specific_question')
    def _onchange_specific_question(self):
        for record in self:
            if record.specific_question:
                record.question = record.specific_question.id
    
    def unlink(self): 
        for record in self:
            if record.global_question:
                raise ValidationError("Cannot delete global question!")
  
        return super(QuestionJobPosition,self).unlink()
    


    @api.onchange('answers_ids','answers_masking_ids')
    def _onchange_answers_ids(self):
        for record in self:
            if record.answers_ids or record.answers_masking_ids:
                if record.question_type and record.id:
                    if record.question_type == "qualitative":
                        if record.question:
                            if record.question.type in ('multiple_choice_one_answer'):
                                if len(record.answers_ids.filtered(lambda line:line.is_correct)) > 1 or len(record.answers_masking_ids.filtered(lambda line:line.is_correct)) > 1:
                                    raise ValidationError("You only allowed  to choose one correct answer!")




    @api.onchange('question')
    def _onchange_question(self):
        for record in self:
            if record.question:
                if record.question.type == 'headline':
                    record.is_hide = True
                    record.question_type = "none"
                    record.mandatory_specific_question = False
                    record.mandatory = False
                elif record.question.type in ['many2one','multiple_choice_one_answer','drop_down_list']:
                    record.question_type = "qualitative"
                    record.is_hide = False
                elif record.question.type in ['round', 'date']:
                    record.question_type = "quantitative"
                    record.is_hide = False
                else:
                    record.is_hide = False
        
    
    def assign_question_type(self):
        for record in self:
            if record.question.type in ('round','date'):
                record.question_type = "quantitative"
            elif record.question.type in ('multiple_choice_one_answer','multiple_choice_multiple_answer','drop_down_list'):
                record.question_type = "qualitative"
                if record.question.choices:
                    answer_data = []
                    answer = str(record.question.choices).split(',')
                    for line_answer in  answer:
                        answer_data.append((0,0,{'answer':line_answer}))
                    record.answers_masking_ids = answer_data
                    
            elif record.question.type == 'many2one':
                record.question_type = "qualitative"
                degree = self.env[record.question.model_id.model].search([])
                name_obj = degree._rec_name
                answer_data = []
                for line_answer in  degree:
                    answer_data.append((0,0,{'answer':line_answer[name_obj]}))
                record.answers_masking_ids = answer_data
               
               


    @api.onchange('question_type','question')
    def _onchange_question_type(self):
        for record in self:
            if record.question_type:
                if record.question_type == "qualitative":
                    if record.question.type in ('multiple_choice_one_answer','multiple_choice_multiple_answer','drop_down_list'):
                        if record.question.choices:
                            answer_data = []
                            answer = str(record.question.choices).split(',')
                            if record.answers_ids:
                                line_remove = []
                                for line in record.answers_ids:
                                    line_remove.append((2,line.id))
                                record.answers_ids = line_remove
                            for line_answer in  answer:
                                answer_data.append((0,0,{'answer':line_answer}))
                            record.answers_ids = answer_data
                            record.is_readonly_tree = True
                    elif record.question.type == 'many2one':
                        if not record.question.domain:
                            degree = self.env[record.question.model_id.model].search([])
                        if record.question.domain:
                            domain = record.question.domain
                            degree = self.env[record.question.model_id.model].search([eval(domain)])
                        name_obj = degree._rec_name
                        answer_data = []
                        if record.answers_ids:
                            line_remove = []
                            for line in record.answers_ids:
                                line_remove.append((2,line.id))
                            record.answers_ids = line_remove
                        for line_answer in  degree:
                            answer_data.append((0,0,{'answer':line_answer[name_obj]}))
                        record.answers_ids = answer_data
                        record.is_readonly_tree = True
                    elif record.answers_ids and record.question_type not in ('multiple_choice_one_answer','multiple_choice_multiple_answer','many2one','drop_down_list'):
                        line_remove = []
                        for line in record.answers_ids:
                            line_remove.append((2, line.id))
                        record.answers_ids = line_remove
                        record.is_readonly_tree = False


    def validate_date(self,date_text):
        try:
            datetime.strptime(date_text, '%Y-%m-%d')
        except ValueError:
            return False
    
    

    def check_question(self,answers,res,question=None):
        if self.question_type == 'quantitative':
            try:      
                if str.lower(question) == "what is your date of birth?":
                    if float(res.birth_years) < self.range_from or  float(res.birth_years) > self.range_to:
                        res.sudo().message_post(body=f"Not Suitable Reason \n <br>"
                                        f"-{self.question.question} <br>"
                                        f"Answers = {res.birth_years}")
                        return False
                elif self.range_from >= 0.0 and self.range_to != 0.0:
                    if float(answers) < self.range_from or  float(answers) > self.range_to:
                        res.sudo().message_post(body=f"Not Suitable Reason \n <br>"
                                        f"-{self.question.question} <br>"
                                        f"Answers = {answers}")
                        return False
            except ValueError:
                return False
                    
        if self.question_type == 'qualitative':
            if self.answers_ids.filtered(lambda line:line.is_correct):
                check_question = self.answers_ids.filtered(lambda line:line.answer == answers and line.is_correct)
                if not check_question:
                    res.sudo().message_post(body=f"Not Suitable Reason \n <br>"
                                    f"-{self.question.question} <br>"
                                    f"Answers = {answers}")
                    return False


        return True
    




class QuestionJobPositionQualitative(models.Model):
    _name = 'qualitative.question'
    answer = fields.Char()
    is_correct = fields.Boolean("Correct Anwers")
    question_job_id = fields.Many2one('question.job.position',required=False,ondelete='CASCADE')    
    question_job_masking_id = fields.Many2one('question.job.position',ondelete='CASCADE')
    job_id = fields.Many2one('hr.job',required=False,ondelete='CASCADE')    
    
    
    
    
    @api.model
    def create(self, vals_list):
        res = super(QuestionJobPositionQualitative,self).create(vals_list)
        if res.question_job_id.question.type in ('multiple_choice_one_answer','multiple_choice_multiple_answer','drop_down_list'):
            choise = str(res.question_job_id.question.choices).split(',')
            if choise:
                if res.answer not in choise:
                    raise ValidationError(f"Cannot create new line answers {res.answer} on question {res.question_job_id.question.question}")
        elif res.question_job_id.question.type == "many2one":
            degree = self.env[res.question_job_id.question.model_id.model].search([])
            name_obj = degree._rec_name
            if degree:
                data = [line[name_obj] for line in degree]
                if res.answer not in data:
                    raise ValidationError(f"Cannot create new line answers {res.answer} on question {res.question_job_id.question.question}")
        if res.question_job_masking_id:
            if res.question_job_masking_id:
                if res.question_job_masking_id.is_on_create_job:
                    res.question_job_id  = res.question_job_masking_id.id
                    res.question_job_masking_id.is_on_create_show  = False
            # if res.answer:
            #     res.answer  = res.answer
        return res


class ApplicantQuestionAnswer(models.Model):
    _name='applicant.answer'

    question_id=fields.Many2one('question.job.position')
    question=fields.Char('Question')
    answer=fields.Text('Answer')
    file=fields.Binary('File')
    file_name = fields.Char('File Name')
    applicant_id=fields.Many2one('hr.applicant')
    applicant_specific_id=fields.Many2one('hr.applicant')
    x_answer_limited = fields.Text(compute="_compute_x_description_limited", store=True)

    @api.depends('answer')
    def _compute_x_description_limited(self):
        for record in self:
            if record.answer:
                if len(record.answer) > 60:
                    record['x_answer_limited'] = f"{record.answer[:60]}..."
                else:
                    record['x_answer_limited'] = record.answer
            else:
                record['x_answer_limited'] = False

    # @api.depends('file')
    # def _compute_file_name(self):
    #     for record in self:
    #         if record.file:
    #             if record.applicant_id.partner_name:
    #                 record.file_name = "CV_" + record.applicant_id.partner_name
    #             elif record.applicant_id.name:
    #                 record.file_name = "CV_" + record.applicant_id.name
    #             else:
    #                 record.file_name = False