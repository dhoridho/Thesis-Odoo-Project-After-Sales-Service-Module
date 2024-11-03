import os
from odoo import models,api,_,fields
from odoo.exceptions import UserError
from googleapiclient.discovery import build
from oauth2client.client import AccessTokenCredentials
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from odoo.modules.module import get_module_path
from google.auth.transport.requests import Request



class AddVideoWizard(models.TransientModel):
    _name = 'add.video.wizard'
    _description = 'Add Video Wizard'

    name = fields.Char('Name')
    is_recording_start = fields.Boolean('Record Start', default=False)
    video_file = fields.Binary('Video')
    video_html = fields.Text('HTML Video')
    is_video_created = fields.Boolean('Video Created')
    survey_question_id = fields.Many2one('survey.question', 'Survey Question')


    @api.model
    def create(self, vals_list):
        res =  super(AddVideoWizard,self).create(vals_list)
        if res.video_html:
            if 'media_iframe_video' in res.video_html:
                res.is_video_created = True
                res.start_uploading_youtube()
            else:
                res.is_video_created = False
        else:
            res.is_video_created = False

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
        if not os.path.isdir(fpath):
            os.mkdir(fpath)
        refresh_token =  self.env['ir.config_parameter'].sudo().get_param("equip3_hr_survey_extend.refresh_token")
        if refresh_token:
            creds = Credentials.from_authorized_user_info(eval(refresh_token), YOUTUBE_UPLOAD_SCOPE)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                refresh_token =  self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.refresh_token",creds.to_json())
        service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)
        privacyStatus = 'unlisted'
        youtube_desc = '-'
        name_title = self.env.user.name + " (Question Interview Video)"
        file_video = fpath + name_title + ".webm"
        request = service.videos().insert(
            part="snippet,status,contentDetails,statistics",
            body={
                "snippet": {
                    "title": name_title ,
                    "description": youtube_desc,
                },
                "status": {"privacyStatus": privacyStatus}
            },
            media_body=MediaFileUpload(file_video)
        )

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
        self.survey_question_id.write({
            'youtube_url': youtube_watch
            })