# -*- coding:utf-8 -*-
from odoo import models, fields
import logging

logger = logging.getLogger(__name__)

class SurveyPaticipations(models.Model):
    _name = "survey.user_input"
    _inherit = ["survey.user_input"]

    # answer description
    last_displayed_page_id = fields.Many2one('survey.question.master', string='Last displayed question/page')
    predefined_question_ids = fields.Many2many('survey.question.master', string='Predefined Questions', readonly=True) 

    def _clear_inactive_conditional_answers(self):
        """
        Clean eventual answers on conditional questions that should not have been displayed to user.
        This method is used mainly for page per question survey, a similar method does the same treatment
        at client side for the other survey layouts.
        E.g.: if depending answer was uncheck after answering conditional question, we need to clear answers
              of that conditional question, for two reasons:
              - ensure correct scoring
              - if the selected answer triggers another question later in the survey, if the answer is not cleared,
                a question that should not be displayed to the user will be.
        
        TODO DBE: Maybe this can be the only cleaning method, even for section_per_page or one_page where 
        conditional questions are, for now, cleared in JS directly. But this can be annoying if user typed a long 
        answer, changed his mind unchecking depending answer and changed again his mind by rechecking the depending 
        answer -> For now, the long answer will be lost. If we use this as the master cleaning method, 
        long answer will be cleared only during submit.
        """
        inactive_questions = self._get_inactive_conditional_questions()
        logger.info('inactive_questions' + str(inactive_questions))

        # delete user.input.line on question that should not be answered.
        answers_to_delete = self.user_input_line_ids.filtered(lambda answer: answer.question_id in inactive_questions)
        answers_to_delete.unlink()     

    def _get_inactive_conditional_questions(self):
        triggering_answer_by_question, triggered_questions_by_answer, selected_answers = self._get_conditional_values()

        # get questions that should not be answered
        inactive_questions = self.env['survey.question.master']
        for answer in triggered_questions_by_answer.keys():
            if answer not in selected_answers:
                for question in triggered_questions_by_answer[answer]:
                    inactive_questions |= question
        return inactive_questions
   
    # ------------------------------------------------------------
    # CREATE / UPDATE LINES FROM SURVEY FRONTEND INPUT
    # ------------------------------------------------------------

    def save_lines(self, question, answer, comment=None):
        """ Save answers to questions, depending on question type

            If an answer already exists for question and user_input_id, it will be
            overwritten (or deleted for 'choice' questions) (in order to maintain data consistency).
        """
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])
        logger.info('save_lines- answer' + str(answer))
        logger.info('save_lines- question.question_type' + str(question.question_type))
        if question.question_type in ['char_box', 'text_box', 'numerical_box', 'date', 'datetime']:
            self._save_line_simple_answer(question, old_answers, answer)
            if question.save_as_email and answer:
                self.write({'email': answer})
            if question.save_as_nickname and answer:
                self.write({'nickname': answer})

        elif question.question_type in ['simple_choice', 'multiple_choice', 'epps', 'papikostick']:
            self._save_line_choice(question, old_answers, answer, comment)
        elif question.question_type == 'matrix':
            self._save_line_matrix(question, old_answers, answer, comment)
        elif question.question_type == 'disc':
            self._save_line_disc(question, old_answers, answer, comment)
        else:
            raise AttributeError(question.question_type + ": This type of question has no saving function")


    def _save_line_disc(self, question, old_answers, answers, comment):
        vals_list = []

        if answers:
            for row_key, row_answer in answers.items():
                for answer in row_answer:
                    vals = self._get_line_answer_values(question, answer, 'suggestion')
                    vals['matrix_row_id'] = int(row_key)
                    vals['disc_row_id'] = int(row_key)
                    vals_list.append(vals.copy())

        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)



    def _save_line_choice(self, question, old_answers, answers, comment):
        if not (isinstance(answers, list)):
            answers = [answers]
        vals_list = []

        if question.question_type == 'simple_choice':
            if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'epps':
            vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'multiple_choice':
            vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]
        elif question.question_type == 'papikostick':
            if not question.comment_count_as_answer or not question.comments_allowed or not comment:
                vals_list = [self._get_line_answer_values(question, answer, 'suggestion') for answer in answers]

        if comment:
            vals_list.append(self._get_line_comment_values(question, comment))

        old_answers.sudo().unlink()
        logger.info('user_input_id' + str(vals_list))
        logger.info('answers' + str(answers))        
        #logger.info('question_id' + str(vals_list['question_id']))     
        #logger.info('answer_type' + str(vals_list['answer_type']))      
        #logger.info('suggested_answer_id' + str(vals_list['suggested_answer_id']))                      

        return self.env['survey.user_input.line'].create(vals_list)            

    def _get_line_answer_values(self, question, answer, answer_type):
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }

        logger.info('user_input_id' + str(self.id))
        logger.info('question_id' + str(question.id))     
        logger.info('answer_type' + str(answer_type))      
        logger.info('suggested_answer_id' + str(answer))  
        #         
        if not answer or (isinstance(answer, str) and not answer.strip()):
            vals.update(answer_type=None, skipped=True)
            return vals

        if answer_type == 'suggestion':
            vals['suggested_answer_id'] = int(answer)
        elif answer_type == 'numerical_box':
            vals['value_numerical_box'] = float(answer)
        else:
            vals['value_%s' % answer_type] = answer
        return vals        