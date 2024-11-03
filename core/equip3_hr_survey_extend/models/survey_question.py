from odoo import models,api,_,fields
from odoo.exceptions import ValidationError, UserError
import random
import os
from googleapiclient.discovery import build
from oauth2client.client import AccessTokenCredentials
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from odoo.modules.module import get_module_path
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError


class Equip3SurveyInheritSurveyQuestion(models.Model):
    _inherit = 'survey.question'
    question_type = fields.Selection(selection_add=[
        ('disc', 'DISC'),
        ('epps','EPPS'),
        ('papikostick', 'Papikostick'),
        ('video','Video'),
        ('file','File'),
        ('mbti','MBTI'),
        ('vak','VAK'),
        ('ist', 'IST'),
        ('kraepelin', 'Kraepelin'),
        ('interview', 'Interview'),
        ])
    is_read_only = fields.Boolean(default=False)
    is_primary_master_data = fields.Boolean()
    matrix_subtype = fields.Selection([
        ('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Matrix Type', default='simple')
    disc_subtype = fields.Selection([
        ('simple', 'One choice per row'),
        ('multiple', 'Multiple choices per row')], string='Disc Type', default='simple')
    
    interview_category = fields.Selection([('skills','Skills'),('personality','Personality')],string="Category")
    is_interview = fields.Boolean(default=False)
    comment_parent_id = fields.Many2one('survey.question',string="Parent Question")
    is_question_languange =  fields.Boolean(default=False)
    youtube_url = fields.Char("Youtube URL")
    video_response_time = fields.Integer("Video Response Time",default=1)
    video_preparation_time = fields.Integer("Video Preparation Time",default=1)
    video_attempt_limit = fields.Integer("Video Attempt Limit",default=1)
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
    # IST
    ist_sub_type = fields.Selection(selection=[
        ('simple_choice', 'Multiple choice: only one answer'),
        ('char_box', 'Single Line Text Box'),
        ('numerical_box', 'Numerical Value'),
    ], default='char_box')
    code_ist = fields.Selection(selection=[
            ('se', 'SE'), 
            ('wa', 'WA'),
            ('an', 'AN'),
            ('ge', 'GE'),
            ('ra', 'RA'),
            ('zr', 'ZR'),
            ('fa', 'FA'),
            ('wu', 'WU'),
            ('me', 'ME')
    ], string='Code')

    video_type = fields.Selection([
        ('url', 'Youtube URL'),
        ('record', 'Record Video')], string='Video Type', default='url')

    kraepelin_columns = fields.Integer('Columns', default=45)
    kraepelin_rows = fields.Integer('Rows', default=45)
    kraepelin_time_per_column = fields.Integer('Time per Column (Seconds)', compute='_compute_kraepelin_actual_columns_rows_time', store=True)
    kraepelin_actual_columns = fields.Integer('Actual Columns', compute='_compute_kraepelin_actual_columns_rows_time', store=True)
    kraepelin_actual_rows = fields.Integer('Actual Rows', compute='_compute_kraepelin_actual_columns_rows_time', store=True)

    video_html = fields.Text('Add a Video')


    @api.model
    def create(self, vals_list):
        res =  super(Equip3SurveyInheritSurveyQuestion,self).create(vals_list)
        for data in res:
            if data.video_html:
                if 'media_iframe_video' in data.video_html:
                    data.start_uploading_youtube()
        return res

    def write(self, vals):
        if vals.get('video_html'):
            if 'media_iframe_video' in vals.get('video_html'):
                self.start_uploading_youtube()
                vals['video_html'] = False
        res =  super(Equip3SurveyInheritSurveyQuestion, self).write(vals)
        
        return res


    def start_uploading_youtube(self):
        YOUTUBE_API_SERVICE_NAME = "youtube"
        YOUTUBE_API_VERSION = "v3"
        YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
        ys_id = self.env['youtube.settings'].sudo().search([])
        # access_token = ys_id.youtube_access_token
        # credentials = AccessTokenCredentials(access_token, "MyAgent/1.0", None)
        creds = None
        module_path = get_module_path('equip3_hr_survey_extend')
        fpath =  module_path + "/googletoken/"
        refresh_token =  self.env['ir.config_parameter'].sudo().get_param("equip3_hr_survey_extend.refresh_token")
        if refresh_token:
            try:
                creds = Credentials.from_authorized_user_info(eval(refresh_token), YOUTUBE_UPLOAD_SCOPE)
            except ValueError as e:
                raise ValidationError(e)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError as e:
                    raise ValidationError(e)
                refresh_token =  self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.refresh_token",creds.to_json())
        try:
            service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)
        except:
            raise UserError(_('Error: Google Credentials Error, Please Contact your Administrator'))

        privacyStatus = 'unlisted'
        youtube_desc = '-'
        
        
        name_title = self.env.user.name + " (Question Interview Video)"
        # file_video = fpath + name_title + ".webm"
        listdir = os.listdir(fpath)
        listdir.sort()
        for filename in listdir:
            if filename.endswith(".webm"):
                file_path = os.path.join(fpath, filename)
                request = service.videos().insert(
                    part="snippet,status,contentDetails,statistics",
                    body={
                        "snippet": {
                            "title": name_title ,
                            "description": youtube_desc,
                        },
                        "status": {"privacyStatus": privacyStatus}
                    },
                    media_body=MediaFileUpload(file_path)
                )
                os.remove(file_path)


                try:
                    response = request.execute()
                except Exception as e:
                    error_msg = ''
                    if 'access_token is expired' in str(e):
                        error_msg = 'Youtube Access Token Expired, Please Contact your Administrator.'
                    else:
                        error_msg = str(e)
                    raise UserError(_('Error: %s' % error_msg))

                youtube_url = "https://www.youtube.com/embed/" + str(response['id'])
                youtube_watch = "http://www.youtube.com/watch?v=" + str(response['id'])
                print('youtube_watch:::::', youtube_watch)
                self.write({
                    'youtube_url': youtube_watch
                    })
                break


    @api.depends('kraepelin_columns', 'kraepelin_rows')
    def _compute_kraepelin_actual_columns_rows_time(self):
        for survey in self:
            if survey.question_type == 'kraepelin':
                survey.kraepelin_time_per_column = survey.kraepelin_rows * 2 / 3
                survey.kraepelin_actual_rows = 2 * survey.kraepelin_rows - 1
                survey.kraepelin_actual_columns = 2 * survey.kraepelin_columns

    def generate_random_number(self):
        return random.randint(1, 9)

    def add_video_wizard_action(self):
        ctx = self._context.copy()
        ctx['default_survey_question_id'] = self.id
        return {
                'name': _('Add a Video'),
                'res_model': 'add.video.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref('equip3_hr_survey_extend.add_video_wizard_view_form').id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
               }    

    @api.onchange('question_type','video_response_time')
    def _onchange_youtube_field_video(self):
        for record in self:
            if record.question_type == 'video':
                if record.video_response_time < 1:
                    raise ValidationError("Please input Video Response Time >= 1 !")


    @api.onchange('question_type','video_preparation_time')
    def _onchange_youtube_field_video1(self):
        for record in self:
            if record.question_type == 'video':

                if record.video_preparation_time < 1:
                    raise ValidationError("Please input Video Preparation Time >= 1 !")



    @api.onchange('question_type','video_attempt_limit')
    def _onchange_youtube_field_video3(self):
        for record in self:
            if record.question_type == 'video':

                if record.video_attempt_limit < 1:
                    raise ValidationError("Please input Video Attempt Limit >= 1 !")
    

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        question_type = self.env.context.get('default_question_type', False)
        is_read_only = self.env.context.get('default_is_read_only')
        if (not question_type):
            res.update({
                'question_type': 'text_box'
            })
        else:
            res.update({
                'question_type': question_type.lower() if question_type not in ['general', 'peer_review', 'tasks', 'exit_interview'] else False,
                'is_read_only': is_read_only if question_type not in ['general','interview', 'peer_review', 'tasks', 'exit_interview'] else False,
                'is_interview': True if question_type == 'interview' else False,
            })
        return res


class Equip3SurveyInheritSurveyQuestionAnswers(models.Model):
    _inherit = 'survey.question.answer'
    _rec_name = 'name_combine'

    PAPIKOSTICK_OPTIONS = [
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('d', 'D'),
        ('e', 'E'),
        ('f', 'F'),
        ('g', 'G'),
        ('h', 'H'),
        ('i', 'I'),
        ('j', 'J'),
        ('k', 'K'),
        ('l', 'L'),
        ('m', 'M'),
        ('n', 'N'),
        ('o', 'O'),
        ('p', 'P'),
        ('q', 'Q'),
        ('r', 'R'),
        ('s', 'S'),
        ('t', 'T'),
        ('u', 'U'),
        ('v', 'V'),
        ('w', 'W'),
        ('x', 'X'),
        ('y', 'Y'),
        ('z', 'Z')
    ]
    MBTI_CODE_OPTIONS = [
        ('e', 'E'),
        ('f', 'F'),
        ('i', 'I'),
        ('j', 'J'),
        ('n', 'N'),
        ('p', 'P'),
        ('s', 'S'),
        ('t', 'T')
    ]

    name_combine = fields.Char(compute='_compute_name_combine')
    code_m = fields.Selection([
        ('D', 'D'),('I','I'),('S','S'),('C','C'),('*','*')],string="Code (M)")
    code_l = fields.Selection([('D', 'D'),('I','I'),('S','S'),('C','C'),('*','*')],string="Code (L)")
    code = fields.Selection([('a','A'),('b','B')],string="Code")
    code_papikostick = fields.Selection(PAPIKOSTICK_OPTIONS)
    value_en =  fields.Char()
    epps_code = fields.Integer()
    papikostick_code = fields.Integer()
    mbti_code = fields.Selection(MBTI_CODE_OPTIONS)
    vak_selection = fields.Selection([('v','V'),('a','A'),('k','K')],string="VAK Selection")
    
    
    
    
    @api.depends('value')
    def _compute_name_combine(self):
        for record in self:
            if record.value and record.value_en:
                record.name_combine = f"{record.value} - {record.value_en}"
            else:
                record.name_combine =  record.value


