from odoo import _, api, fields, models

class ResConfigSettings(models.TransientModel):
	_inherit = "res.config.settings"

	pdpa_consent_file = fields.Binary(string='PDPA Consent', attachment=True)
	pdpa_consent_filename = fields.Char(string='PDPA Filename')

	@api.model
	def get_values(self):
		res = super(ResConfigSettings, self).get_values()
		IrConfigParam = self.env['ir.config_parameter'].sudo()
		res.update({
			'pdpa_consent_file': IrConfigParam.get_param('pdpa_consent_file', False),
			'pdpa_consent_filename': IrConfigParam.get_param('pdpa_consent_filename', False),
		})
		return res

	def set_values(self):
		res = super(ResConfigSettings, self).set_values()
		self.env['ir.config_parameter'].sudo().set_param('pdpa_consent_file', self.pdpa_consent_file)
		self.env['ir.config_parameter'].sudo().set_param('pdpa_consent_filename', self.pdpa_consent_filename)
		return res