from odoo import models, fields, api, _
import google.auth.transport.requests
import requests
from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT, TIMEOUT


class ResCompany(models.Model):
	_inherit = "res.company"

	
	@api.model
	def _cron_get_credentials_google_token(self):
		ys_id = self.env['youtube.settings'].sudo().search([])
		acct_creds = {
			'client_id': ys_id.youtube_client_id,
			'refresh_token': ys_id.youtube_access_refresh_token,
			'client_secret': ys_id.youtube_client_secret,
			'grant_type': "refresh_token",
			'scope': ys_id.youtube_access_scopes_token,
		}
		headers = {"Content-type": "application/x-www-form-urlencoded"}
		req = requests.post(GOOGLE_TOKEN_ENDPOINT, data=acct_creds, headers=headers, timeout=TIMEOUT)
		new_token = req.json().get('access_token')
		if new_token:
			if len(new_token) >= 5:
				companies = self.env['res.company'].sudo().search([])
				for comp in companies:
					comp.sudo().write({'youtube_access_token':new_token})
		


