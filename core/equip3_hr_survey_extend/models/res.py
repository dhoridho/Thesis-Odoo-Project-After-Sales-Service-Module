from odoo import models, fields, api, _,http
from odoo.exceptions import UserError, ValidationError
import requests
import json
import base64
from odoo.modules.module import get_module_path
from odoo.tools.mimetypes import guess_mimetype
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
import signal
from subprocess import Popen, PIPE

class ResCompany(models.Model):
    _inherit = "res.company"


    youtube_client_id = fields.Char(string="Youtube Client ID")
    youtube_client_secret = fields.Char(string="Youtube Client Secret")
    youtube_apikey = fields.Char(string="Youtube Api Key")
    youtube_access_token = fields.Char()
    youtube_redirect_url = fields.Char("Youtube Redirect URL")
    youtube_go_google = fields.Char()




class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    email_login = fields.Char(string="Email", config_parameter='equip3_hr_survey_extend.email_login')
    access_token = fields.Char(string="Email", config_parameter='equip3_hr_survey_extend.access_token')
    is_valid_youtube = fields.Boolean(string="valid", config_parameter='equip3_hr_survey_extend.is_valid_youtube')
    user_name = fields.Char(string="User Login Info", config_parameter='equip3_hr_survey_extend.user_name')
    youtube_client_id = fields.Char(string="Youtube Client ID",related="company_id.youtube_client_id",  readonly=False)
    youtube_client_secret = fields.Char(string="Youtube Client Secret",related="company_id.youtube_client_secret",  readonly=False)
    youtube_apikey = fields.Char(string="Youtube Api Key",related="company_id.youtube_apikey",  readonly=False)
    youtube_redirect_url = fields.Char(string="Youtube Redirect URL",related="company_id.youtube_redirect_url",  readonly=False)
    youtube_go_google = fields.Char(related="company_id.youtube_go_google",  readonly=False)
    client_config = fields.Char(config_parameter='equip3_hr_survey_extend.client_config')
    refresh_token = fields.Char(config_parameter='equip3_hr_survey_extend.refresh_token')
    
    def logout_google(self):
        # Revoke the access token
        revoke_url = f'https://accounts.google.com/o/oauth2/revoke?token={self.access_token}'
        requests.get(revoke_url)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.user_name",   False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.email_login", False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.is_valid_youtube", False)
        self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.refresh_token", False)
        return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }


    def youtube_test_connection(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/userinfo.profile","https://www.googleapis.com/auth/userinfo.email"]
        module_path = get_module_path('equip3_hr_survey_extend')
        fpath =  module_path + "/googletoken/"
        if not os.path.isdir(fpath):
            os.mkdir(fpath)
        creds = None
        refresh_token =  self.env['ir.config_parameter'].sudo().get_param("equip3_hr_survey_extend.refresh_token")
        if refresh_token:
            creds = Credentials.from_authorized_user_info(eval(refresh_token), YOUTUBE_UPLOAD_SCOPE)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                refresh_token =  self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.refresh_token",creds.to_json())
            else:
                flow = InstalledAppFlow.from_client_config(eval(self.client_config), scopes=YOUTUBE_UPLOAD_SCOPE)
                flow.redirect_uri = f"{base_url}/auth-token-youtube"
                creds = flow.authorization_url(access_type='offline',include_granted_scopes='true')
                self.env['ir.config_parameter'].sudo().set_param("equip3_hr_survey_extend.client_config", self.client_config)
                return { 'name': 'Open Google',
                  'res_model': 'ir.actions.act_url',
                  'type'     : 'ir.actions.act_url',
                  'target'   : 'new',
                  'url'      : creds[0]
               }


    def action_none(self):
        pass

