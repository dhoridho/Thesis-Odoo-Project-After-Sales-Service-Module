from odoo import models, fields, api


class Users(models.Model):
	_inherit = 'res.users'

	login_date = fields.Datetime(related=False, compute='compute_login_date_query', recursive=False)

	@api.depends('log_ids')
	def compute_login_date_query(self):
		for rec in self:
			self.env.cr.execute('''
					select create_date from res_users_log
					where create_uid=%s

					order by create_date desc
					limit 1
			''', (rec.id,))
			create_date = self.env.cr.fetchone()
			if not create_date:
				rec.login_date = False
				continue
			rec.login_date = create_date[0]

class userLog(models.Model):
	_inherit = 'res.users.log'

	create_uid = fields.Integer(index=True)