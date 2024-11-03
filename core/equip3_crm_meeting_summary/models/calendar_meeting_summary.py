
from odoo import models, fields, api, _
from odoo.tools import html2plaintext
from odoo.exceptions import ValidationError

class CalendarMeetingSummary(models.Model):
    _name = 'calendar.meeting.summary'
    _description = 'Calendar Meeting Summary'
    _rec_name = 'title'

    title = fields.Char(string="Title")
    user_id = fields.Many2one('res.users', string='Creator', default=lambda self: self.env.user)
    editor_ids = fields.Many2many('res.users', string='Editor')
    viewer_ids = fields.Many2many('res.partner', string="Viewer")
    tags_ids = fields.Many2many('calendar.event.type', string="Tags")
    calendar_events_id = fields.Many2one('calendar.event', string="Calendar Events")
    summary = fields.Html('Summary')
    summary_type = fields.Selection(string='Summary Type', selection=[('one', 'One'), ('questions', 'Questions'),], )
    question_ids = fields.One2many(comodel_name='calendar.meeting.summary.questions', inverse_name='meeting_summary_id', string='Questions')
    
    @api.constrains('question_ids','question_ids.is_invalid','summary_type')
    def _constrains_question_ids(self):
        if self.summary_type == 'questions':
            if any((question.is_invalid or (question.is_required and len(html2plaintext(question.answer).strip()) < question.min_char)) for question in self.question_ids):
                raise ValidationError(_("There are required answer and your answer is less than minimum char"))
    

    @api.onchange('calendar_events_id')
    def _onchange_tag_ids(self):
        summary_type = False
        if self.calendar_events_id and self.calendar_events_id.categ_ids:
            if self.calendar_events_id.categ_ids:
                tag_id = self.calendar_events_id.categ_ids[0]
                if not tag_id.is_hide_template and tag_id.is_meeting_summary_required:
                    question_ids = []
                    if tag_id.summary_template_id:
                        for question in tag_id.summary_template_id.line_ids:
                            vals = {
                                'questions':question.name,
                                'min_char':question.min_char,
                                'is_required':question.is_required,
                            }
                            if question.is_required and question.min_char > 0:
                                vals['is_invalid']=True
                            question_ids.append((0,0,vals))
                    self.question_ids = [(5,0,0)]
                    self.question_ids = question_ids
                    summary_type = 'questions'
                elif not tag_id.is_meeting_summary_required:
                    self.question_ids = [(5,0,0)]
                    summary_type = 'one'
        self.summary_type = summary_type
            



class MeetingSummaryQuestion(models.Model):
    _name = 'calendar.meeting.summary.questions'
    _description = 'Meeting Summary Question'

    meeting_summary_id = fields.Many2one(comodel_name='calendar.meeting.summary', string='Meeting Summary', ondelete="cascade")
    questions = fields.Text('Questions', readonly=True)
    answer = fields.Html(string='Answer')
    min_char = fields.Integer(string='Min Char', readonly=True)
    is_required = fields.Boolean(string='Is Required', readonly=True)
    is_invalid = fields.Boolean(string='Is Invalid', compute="_compute_is_invalid", store=True)
    
    
    @api.constrains('answer','meeting_summary_id','meeting_summary_id.calendar_events_id')
    def _compute_is_invalid(self):
        for i in self:
            is_invalid = False
            answer = html2plaintext(i.answer).strip()
            if i.is_required and (len(answer) < i.min_char or not i.answer):
                # raise ValidationError(_("Your answer is less than {} for question '{}'".format(i.min_char, i.questions)))
                is_invalid = True
            i.is_invalid = is_invalid