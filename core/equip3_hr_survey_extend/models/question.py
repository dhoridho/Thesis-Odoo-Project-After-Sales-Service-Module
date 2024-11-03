# -*- coding:utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.http import request
import logging

logger = logging.getLogger(__name__)

class SurveyQuestionMaster(models.Model):
    _name = 'survey.question.master'
    _inherit = ["survey.question"]

    question_ids = fields.One2many(
        'survey.question.master', string='Questions', compute="_compute_question_ids")
    title = fields.Char('Title',required=False)
    page_id = fields.Many2one(
        'survey.question.master', string='Page', compute="_compute_page_id", store=True)

    question_type = fields.Selection([
        ('text_box', 'Multiple Lines Text Box'),
        ('char_box', 'Single Line Text Box'),
        ('numerical_box', 'Numerical Value'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('simple_choice', 'Multiple choice: only one answer'),
        ('multiple_choice', 'Multiple choice: multiple answers allowed'),
        ('matrix', 'Matrix'),
        ('disc', 'DISC'),
        ('epps', 'EPPS'),
        ('papikostick', 'Papikostick'),
        ('mbti', 'MBTI'),
        ('vak', 'VAK'),
        ('ist', 'IST')], string='Question Type', readonly=False, store=True)
    psychological_test_mode = fields.Boolean(default=False)
    suggested_answer1_ids = fields.One2many(
        'survey.question.master.answer', 'question_id', string='Types of answers', copy=True,
        help='Labels used for proposed choices: simple choice, multiple choice and columns of matrix')
    choice_row_ids = fields.One2many(
        'survey.question.master.answer', 'choice_question_id', string='Rows', copy=True,
        help='choice used for proposed choices: rows of matrix')
    choice_row1_ids = fields.One2many(
        'survey.question.master.answer', 'choice_question1_id', string='Rows', copy=True,
        help='choice used for proposed choices: rows of matrix')       

    make_visible = fields.Boolean(string="User", compute='get_user', default='get_user')

    # -- simple choice / multiple choice / matrix
    suggested_answer_ids = fields.One2many(
        'survey.question.master.answer', 'question_id', string='Types of answers', copy=True,
        help='Labels used for proposed choices: simple choice, multiple choice and columns of matrix')

    matrix_row_ids = fields.One2many(
        'survey.question.master.answer', 'matrix_question_id', string='Matrix Rows', copy=True,
        help='Labels used for proposed choices: rows of matrix')

    triggering_answer_id = fields.Many2one(
        'survey.question.master.answer', string="Triggering Answer", copy=False, compute="_compute_triggering_answer_id",
        store=True, readonly=False, help="Answer that will trigger the display of the current question.",
        domain="[('question_id', '=', triggering_question_id)]")


    is_primary_master_data = fields.Boolean()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        question_type = self.env.context.get('default_question_type', '')
        domain = [('id', '=', 1)]
        list = [1]
        question = self.search(domain)
        if(not question_type):
            res.update({
                'psychological_test_mode': False,
                'question_type': 'text_box'
            })
        else:
            res.update({
                'psychological_test_mode': True,
                'question_type': question_type.lower(),
                # 'question_ids':self
            })
        return res

    # def survey_type(self, survey_type):
    #     if(survey_type == "DISC"):
    #         return 'disc'
    #     if(survey_type == "EPPS"):
    #         return "epps"

    matrix_subtype = fields.Selection([
        ('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Matrix Type', default='simple')
    disc_subtype = fields.Selection([
        ('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Disc Type', default='simple')
    def _get_stats_data_answers(self, user_input_lines):
        """ Statistics for question.answer based questions (simple choice, multiple
        choice.). A corner case with a void record survey.question.answer is added
        to count comments that should be considered as valid answers. This small hack
        allow to have everything available in the same standard structure. """
        suggested_answers = [answer for answer in self.mapped('suggested_answer_ids')]
        if self.comment_count_as_answer:
            suggested_answers += [self.env['survey.question.master.answer']]

        count_data = dict.fromkeys(suggested_answers, 0)
        for line in user_input_lines:
            if line.suggested_answer_id or (line.value_char_box and self.comment_count_as_answer):
                count_data[line.suggested_answer_id] += 1

        table_data = [{
            'value': _('Other (see comments)') if not sug_answer else sug_answer.value,
            'suggested_answer': sug_answer,
            'count': count_data[sug_answer]
            }
            for sug_answer in suggested_answers]
        graph_data = [{
            'text': _('Other (see comments)') if not sug_answer else sug_answer.value,
            'count': count_data[sug_answer]
            }
            for sug_answer in suggested_answers]

        return table_data, graph_data

    @api.depends('make_visible')
    def get_user(self):
        user_crnt = self._uid
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        #logger.info("res_user.name: " + res_user.name  )
        logger.info("res_user.name: " +  self.env.user.name )
        context = self._context
        current_uid = context.get('uid')
        logger.info("current_uid: " +  str(current_uid) )

        desired_group_name = self.env['res.groups'].search([('name','in',['Human Resource Administrator', 'Human Resource Officer'])]) 
        for group in desired_group_name:
           logger.info(group.name + str(group.users.ids) + "-" + str(self._uid))
           is_desired_group = res_user.id in group.users.ids   
           self.make_visible=  is_desired_group 
           logger.info('visible' + str(is_desired_group))     
           for id in group.users.ids:
               logger.info('group.users.id' + str(id))     
        #if res_user.has_group('equip_survey_extend.survey_officer'):
        #   logger.info('invisible')
        #   self.make_visible = False
        #else:
        #   logger.info('visible')
        #   self.make_visible = True
    
    @api.constrains('question_type', 'suggested_answer1_ids', 'choice_row1_ids')
    def _check_suggested_answer1(self):
        for record in self:
            if record.question_type=='disc':
                exist_list = []
                for suggested in record.suggested_answer1_ids:
                    if suggested.value1 in exist_list:
                        raise ValidationError(_('User can only choose M or L once and can not choose the same value on different rows'))
                    exist_list.append(suggested.value1)
            if record.question_type=='epps':
                logger.info('vao2')
                exist_list = []
                for choice in record.choice_row1_ids:
                    logger.info('vao2-choice1: ' + choice.choice1)
                    if choice.choice1 in exist_list:
                        raise ValidationError(_('User can only choose A or B once and can not choose the same value on different rows'))
                    exist_list.append(choice.choice1)             
    

class SurveyQuestionMasterAnswer(models.Model):
    """
     A preconfigured answer for a question. This model stores values used
    for

      * simple choice, multiple choice: proposed values for the selection /
        radio;
      * matrix: row and column values;

    """    
    _name = 'survey.question.master.answer'
    _inherit = ["survey.question.answer"]
    _rec_name= 'result'

    question_id = fields.Many2one('survey.question.master', string='Question', ondelete='cascade')
    matrix_question_id = fields.Many2one('survey.question.master', string='Question (as matrix row)', ondelete='cascade')    
    choice_question_id = fields.Many2one('survey.question.master', string='Question (as choice row for DISC)', ondelete='cascade')
    choice_question1_id = fields.Many2one('survey.question.master', string='Question (as choice row for EPPS)', ondelete='cascade')
    value = fields.Char('Suggested value',  default='' )
    value1 = fields.Selection(selection=[('M', 'M'), ('L', 'L')])
    choice = fields.Selection(selection=[('D', 'D'), ('I', 'I'), ('S', 'S'), ('C', 'C'), ('*', '*')], string='Choice row for DISC')
    code_l = fields.Selection(selection=[('D', 'D'), ('I', 'I'), ('S', 'S'), ('C', 'C'), ('*', '*')], string='Choice row for DISC')
    CHOICES1= [('A', 'A'), ('B', 'B')]
    choice1 = fields.Selection(CHOICES1, string='Answer Label (EPPS)')
    result = fields.Char('Suggested value (for DISC or EPPS)',  compute="_compute_value")
    label = fields.Char('Rows (for EPPS)')

    @api.depends('result', 'value', 'value1')
    def _compute_value(self):
        for record in self:
            record.result = ''
            if record.choice:
                record.result = record.choice + " - " + record.label
                # record.result = record.label
            if record.choice1:
                    record.result = record.label
            if record.value1: 
                record.result = record.value1
            if record.value:
                record.result = record.value