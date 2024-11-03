from odoo.addons.auth_signup.controllers.main import AuthSignupHome

class AuthSignupHome(AuthSignupHome):


	def get_auth_signup_qcontext(self):
		res = super(AuthSignupHome, self).get_auth_signup_qcontext()
		res['not_login_form'] = True
		return res