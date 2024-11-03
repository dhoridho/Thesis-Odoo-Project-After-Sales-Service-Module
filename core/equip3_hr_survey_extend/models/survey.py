# -*- coding:utf-8 -*-
# from odoo import api, fields, models, tools, _,exceptions
# from odoo.tools import is_html_empty
# from odoo.http import request
# import random
# import logging


# logger = logging.getLogger(__name__)


# class Survey(models.Model):
#     _inherit ='survey.survey'

#     # name = fields.Char(string='Name', required=True)
#     survey_type = fields.Selection(selection=[('general','General'),
#                                               ('disc', 'DISC'),
#                                               ('epps','EPPS')],
#                                               string="Survey Type")
#     is_read_only_type = fields.Boolean()
#     sequence_order = fields.Selection([
#         ('normal', 'Normal'),
#         ('randomized_per_participants', 'Randomized per Participants'),
#     ], string="Sequence Order", required=True, default='normal')
#     question_and_page_ids = fields.One2many(
#         'survey.question.master', 'survey_id', string='Sections and Questions', copy=True)
#     page_ids = fields.One2many(
#         'survey.question.master', string='Pages', compute="_compute_page_and_question_ids")
#     question_ids = fields.One2many(
#         'survey.question.master', string='Questions', compute="_compute_page_and_question_ids")
#     session_question_id = fields.Many2one('survey.question.master', string="Current Question", copy=False,
#                                           help="The current question of the equip_survey_extend session.")
    
    
    
#     def action_send_survey(self):
#         print("survey send")
#         print("hereeee")
#         """ Open a window to compose an email, pre-filled with the survey message """
#     # Ensure that this survey has at least one page with at least one question.
#         if (not self.page_ids and self.questions_layout == 'page_per_section') or not self.question_ids:
#             raise exceptions.UserError(_('You cannot send an invitation for a survey that has no questions.'))

#         if self.state == 'closed':
#             raise exceptions.UserError(_("You cannot send invitations for closed surveys."))

#         template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)

#         local_context = dict(
#             self.env.context,
#             default_survey_id=self.id,
#             default_use_template=bool(template),
#             default_template_id=template and template.id or False,
#             notif_layout='mail.mail_notification_light',
#         )
#         return {
#             'type': 'ir.actions.act_window',
#             'view_mode': 'form',
#             'name':'Hashmicro',
#             'res_model': 'survey.invite',
#             'target': 'new',
#             'context': local_context,
#         }



#     @api.onchange('survey_type')
#     def _onchange_survey_type(self):
#         for record in self:
#             if record.survey_type == 'disc':
#                 master_list=[]
#                 if not record.question_and_page_ids:
#                     master_data = self.env['survey.question.master'].search([('is_primary_master_data','=',True)])
#                     data = [line.id for line in master_data]
#                     master_list.extend(data)
#                     record.question_and_page_ids = [(6,0,master_list)]


#     @api.depends('question_and_page_ids')
#     def _compute_page_and_question_ids(self):
#         for survey in self:
#             survey.page_ids = survey.question_and_page_ids.filtered(
#                 lambda question: question.is_page)
#             survey.question_ids = survey.question_and_page_ids - survey.page_ids

#     @api.depends('question_and_page_ids.is_conditional', 'users_login_required', 'access_mode')
#     def _compute_is_attempts_limited(self):
#         for survey in self:
#             if not survey.is_attempts_limited or \
#                (survey.access_mode == 'public' and not survey.users_login_required) or \
#                any(question.is_conditional for question in survey.question_and_page_ids):
#                 survey.is_attempts_limited = False

#     @api.depends('scoring_type', 'question_and_page_ids.save_as_nickname')
#     def _compute_session_show_leaderboard(self):
#         for survey in self:
#             survey.session_show_leaderboard = survey.scoring_type != 'no_scoring' and \
#                 any(question.save_as_nickname for question in survey.question_and_page_ids)

#     @api.depends('question_and_page_ids.is_conditional')
#     def _compute_has_conditional_questions(self):
#         for survey in self:
#             survey.has_conditional_questions = any(
#                 question.is_conditional for question in survey.question_and_page_ids)

#     def _prepare_user_input_predefined_questions(self):
#         self.ensure_one()

#         questions = self.env['survey.question.master']

#         # First append questions without page
#         for question in self.question_ids:
#             if not question.page_id:
#                 questions |= question

#         # Then, questions in sections

#         for page in self.page_ids:
#             if self.questions_selection == 'all':
#                 questions |= page.question_ids
#             else:
#                 if page.random_questions_count > 0 and len(page.question_ids) > page.random_questions_count:
#                     questions = questions.concat(
#                         *random.sample(page.question_ids, page.random_questions_count))
#                 else:
#                     questions |= page.question_ids

#         return questions

#     @api.model
#     def _get_pages_or_questions(self, user_input):
#         """ Returns the pages or questions (depending on the layout) that will be shown
#         to the user taking the equip_survey_extend.
#         In 'page_per_question' layout, we also want to show pages that have a description. """

#         result = self.env['survey.question.master']
#         if self.questions_layout == 'page_per_section':
#             result = self.page_ids
#         elif self.questions_layout == 'page_per_question':
#             if self.questions_selection == 'random' and not self.session_state:
#                 result = user_input.predefined_question_ids
#             else:
#                 result = self.question_and_page_ids.filtered(
#                     lambda question: not question.is_page or not is_html_empty(question.description))

#         return result

#     def _get_next_page_or_question(self, user_input, page_or_question_id, go_back=False):
#         """ Generalized logic to retrieve the next question or page to show on the equip_survey_extend.
#         It's based on the page_or_question_id parameter, that is usually the currently displayed question/page.

#         There is a special case when the equip_survey_extend is configured with conditional questions:
#         - for "page_per_question" layout, the next question to display depends on the selected answers and
#         the questions 'hierarchy'.
#         - for "page_per_section" layout, before returning the result, we check that it contains at least a question
#         (all section questions could be disabled based on previously selected answers)

#         The whole logic is inverted if "go_back" is passed as True.

#         As pages with description are considered as potential question to display, we show the page
#         if it contains at least one active question or a description.

#         :param user_input: user's answers
#         :param page_or_question_id: current page or question id
#         :param go_back: reverse the logic and get the PREVIOUS question/page
#         :return: next or previous question/page
#         """

#         survey = user_input.survey_id
#         pages_or_questions = survey._get_pages_or_questions(user_input)
#         Question = self.env['survey.question.master']

#         # Get Next
#         if not go_back:
#             if not pages_or_questions:
#                 return Question
#             # First page
#             if page_or_question_id == 0:
#                 return pages_or_questions[0]

#         current_page_index = pages_or_questions.ids.index(page_or_question_id)

#         # Get previous and we are on first page  OR Get Next and we are on last page
#         if (go_back and current_page_index == 0) or (not go_back and current_page_index == len(pages_or_questions) - 1):
#             return Question

#         # Conditional Questions Management
#         triggering_answer_by_question, triggered_questions_by_answer, selected_answers = user_input._get_conditional_values()
#         inactive_questions = user_input._get_inactive_conditional_questions()
#         if survey.questions_layout == 'page_per_question':
#             question_candidates = pages_or_questions[0:current_page_index] if go_back \
#                 else pages_or_questions[current_page_index + 1:]
#             for question in question_candidates.sorted(reverse=go_back):
#                 # pages with description are potential questions to display (are part of question_candidates)
#                 if question.is_page:
#                     contains_active_question = any(
#                         sub_question not in inactive_questions for sub_question in question.question_ids)
#                     is_description_section = not question.question_ids and not is_html_empty(
#                         question.description)
#                     if contains_active_question or is_description_section:
#                         return question
#                 else:
#                     triggering_answer = triggering_answer_by_question.get(
#                         question)
#                     if not triggering_answer or triggering_answer in selected_answers:
#                         # question is visible because not conditioned or conditioned by a selected answer
#                         return question
#         elif survey.questions_layout == 'page_per_section':
#             section_candidates = pages_or_questions[0:current_page_index] if go_back \
#                 else pages_or_questions[current_page_index + 1:]
#             for section in section_candidates.sorted(reverse=go_back):
#                 contains_active_question = any(
#                     question not in inactive_questions for question in section.question_ids)
#                 is_description_section = not section.question_ids and not is_html_empty(
#                     section.description)
#                 if contains_active_question or is_description_section:
#                     return section
#             return Question

#     def _get_survey_questions(self, answer=None, page_id=None, question_id=None):
#         """ Returns a tuple containing: the equip_survey_extend question and the passed question_id / page_id
#         based on the question_layout and the fact that it's a session or not.

#         Breakdown of use cases:
#         - We are currently running a session
#         We return the current session question and it's id
#         - The layout is page_per_section
#         We return the questions for that page and the passed page_id
#         - The layout is page_per_question
#         We return the question for the passed question_id and the question_id
#         - The layout is one_page
#         We return all the questions of the equip_survey_extend and None

#         In addition, we cross the returned questions with the answer.predefined_question_ids,
#         that allows to handle the randomization of questions. """

#         questions, page_or_question_id = None, None

#         if answer and answer.is_session_answer:
#             return self.session_question_id, self.session_question_id.id
#         if self.questions_layout == 'page_per_section':
#             if not page_id:
#                 raise ValueError(
#                     "Page id is needed for question layout 'page_per_section'")
#             page_id = int(page_id)
#             questions = self.env['survey.question.master'].sudo().search(
#                 [('survey_id', '=', self.id), ('page_id', '=', page_id)])
#             page_or_question_id = page_id
#         elif self.questions_layout == 'page_per_question':
#             if not question_id:
#                 raise ValueError(
#                     "Question id is needed for question layout 'page_per_question'")
#             question_id = int(question_id)
#             questions = self.env['survey.question.master'].sudo().browse(
#                 question_id)
#             page_or_question_id = question_id
#         else:
#             questions = self.question_ids

#         # we need the intersection of the questions of this page AND the questions prepared for that user_input
#         # (because randomized surveys do not use all the questions of every page)
#         if answer:
#             questions = questions & answer.predefined_question_ids
#         return questions, page_or_question_id
    
#     def show_create_form(self, survey_type):
#         # self.env['ir.config_parameter'].sudo().set_param('survey.psychological_test_mode', True)
#         # if(survey_type != ''):
#         #     self.init_survey_type = survey_type
#         question_and_page_ids = []
#         domain = [('question_type', '=', survey_type)]
#         questions = self.env['survey.question.master'].search(domain)
#         for question in questions:
#             question_and_page_ids.append(question.id)
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Survey',
#             'view_type': 'form',
#             'view_mode': 'form',
#             "context": {'default_title': self.survey_type.selection, 'default_survey_type': self.survey_type.selection,'survey_type':survey_type},
#             'res_model': 'survey.survey',
#             'view_id': self.env.ref('equip_survey_extend.survey_survey_view_form').id,
#             'flags': {'initial_mode': 'view'},
#             'target': 'main'
#         }
    
#     @api.model
#     def default_get(self,fields_list):
#         res = super(Survey,self).default_get(fields_list)
#         context = self._context
#         if context and ('survey_type' in context):
#             res['survey_type'] = context['survey_type']
#         return res