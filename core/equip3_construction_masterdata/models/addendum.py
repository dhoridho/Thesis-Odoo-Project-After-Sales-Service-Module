from odoo import fields, models, api, _

class AddendumLine(models.Model):
	_name = "addendum.line"
	_description = "Addendum Line"
	_order = "sequence"


	sequence = fields.Integer('Sequence', default=1)
	sr_no = fields.Integer('No.', compute="_sequence_ref")
	addendum_id = fields.Many2one('project.project', string="Project")
	project_category = fields.Char('Project Category')
	job_type = fields.Char('Job Type')
	contract_amount = fields.Float('Contract Amount')
	down_payment = fields.Float('Down Payment')
	retention_1 = fields.Float('Retention 1')
	retention_1_date = fields.Date('Retention 1 Date')
	retention_2 = fields.Float('Retention 2')
	retention_2_date = fields.Date('Retention 2 Date')
	type_ppc = fields.Selection([
        ('account_receivable', 'Account Receivable'),
        ('account_payable', 'Account Payable')
        ], string='Type of Progressive Project Claim', readonly=True)
	start_date = fields.Date('Start Date')
	end_date = fields.Date('End Date')
	payment_term = fields.Many2one('account.payment.term', 'Payment Term')
	status_progress = fields.Float('Status Progress')
	vo_payment_type = fields.Selection([
                        ('join', 'Join Payment'),
                        ('split', 'Split Payment')
                        ], string="Payment Method")

	@api.depends('addendum_id.addendum_line_ids', 'addendum_id.addendum_line_ids.sequence')
	def _sequence_ref(self):
		for line in self:
			no = 0
			line.sr_no = no
			for l in line.addendum_id.addendum_line_ids:
				no += 1
				l.sr_no = no
				