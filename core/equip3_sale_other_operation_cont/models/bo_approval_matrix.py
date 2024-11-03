from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning

class BlanketApprovalMatrix(models.Model):
	_name = 'blanket.approval.matrix'
	_description = "Blanket Order Approval Matrix"
	_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
	
	name = fields.Char(string='Name', tracking=True, required=True)
	company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company, store=True, tracking=True)
	branch_id = fields.Many2one("res.branch", string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True, required=True,)
	config = fields.Selection([
		('quantity', 'Quantity'),
		('amount', 'Total Amount')
	], 'Configuration', store=True, required=True, default="amount", tracking=True)
	minimum_amt = fields.Float(string='Minimum Amount', required=True, tracking=True)
	maximum_amt = fields.Float(string='Maximum Amount', required=True, tracking=True)
	approver_matrix_line_ids = fields.One2many('blanket.approval.matrix.lines', 'approval_matrix', string="Approver Name")
	
	@api.constrains('branch_id', 'minimum_amt', 'maximum_amt')
	def _check_existing_record(self):
		for record in self:
			if record.branch_id:
				approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('config', '=', record.config),
					'|', '|',
					'&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
					'&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
					'&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)], limit=1)
				if approval_matrix_id:
					raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix [%s] in same branch. Please change the minimum and maximum range" % (approval_matrix_id.name))
	
	def _reset_sequence(self):
		for rec in self:
			current_sequence = 1
			for line in rec.approver_matrix_line_ids:
				line.sequence = current_sequence
				current_sequence += 1
	
	def copy(self, default=None):
		res = super(BlanketApprovalMatrix, self.with_context(keep_line_sequence=True)).copy(default)
		return res


class BlanketApprovalMatrixLines(models.Model):
	_name = 'blanket.approval.matrix.lines'
	_description = "Blanket Order Approval Matrix Lines"
	
	@api.model
	def default_get(self, fields):
		res = super(BlanketApprovalMatrixLines, self).default_get(fields)
		if self._context:
			context_keys = self._context.keys()
			next_sequence = 1
			if 'approver_matrix_line_ids' in context_keys:
				if len(self._context.get('approver_matrix_line_ids')) > 0:
					next_sequence = len(self._context.get('approver_matrix_line_ids')) + 1
			res.update({'sequence': next_sequence})
		return res
	
	
	approval_matrix = fields.Many2one('limit.approval.matrix', string='Approval Marix')
	user_name_ids = fields.Many2many('res.users', string="Users", required=True)
	sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence')
	sequence2 = fields.Integer(
		string="No.",
		related="sequence",
		readonly=True,
		store=True
	)
	minimum_approver = fields.Integer(string="Minimum Approver", required=True, default=1)
	order_id = fields.Many2one('sale.order', string="Sale Order")
	minimum_approver = fields.Integer(string="Minimum Approver", required=True, default=1)
	state_char = fields.Text(string='Approval Status')
	time_stamp = fields.Datetime(string='Timestamp')
	feedback = fields.Char(string='Rejected Reason')
	last_approved = fields.Many2one('res.users', string='Users')
	approved = fields.Boolean('Approved')
	approved_users = fields.Many2many('res.users', 'approved_users_bo_patner_rel', 'bo_id', 'user_id', string='Users')
	approval_type = fields.Selection([('credit_limit','Credit Limit'), ('max_invoice_overdue_days','Max Invoice Overdue (Days)')])
	
	def unlink(self):
		approval = self.approval_matrix
		res = super(BlanketApprovalMatrixLines, self).unlink()
		approval._reset_sequence()
		return res
	
	@api.model
	def create(self, vals):
		res = super(BlanketApprovalMatrixLines, self).create(vals)
		if not self.env.context.get("keep-line_sequence", False):
			res.approval_matrix._reset_sequence()
		return res