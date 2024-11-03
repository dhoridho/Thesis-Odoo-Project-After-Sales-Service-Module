from odoo import models, fields, api, _
import google.auth.transport.requests
import requests

class YoutubeSettings(models.Model):
	_name = "youtube.settings"

	name = fields.Char('Name')
	youtube_access_refresh_token = fields.Char('Refresh Token')
	youtube_access_scopes_token = fields.Char('Scopes')
	youtube_client_id = fields.Char(string="Youtube Client ID")
	youtube_client_secret = fields.Char(string="Youtube Client Secret")
	youtube_apikey = fields.Char(string="Youtube Api Key")
	youtube_access_token = fields.Char("Token")
	youtube_redirect_url = fields.Char("Youtube Redirect URL")
	info = fields.Char(default='https://developers.google.com/oauthplayground/', help='Please access this link to generate Refresh Token')
