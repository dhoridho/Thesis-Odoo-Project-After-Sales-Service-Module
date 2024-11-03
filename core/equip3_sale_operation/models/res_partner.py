from odoo import api, fields, models, _
from datetime import datetime, date
import json
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
       
    state_customer = fields.Selection([("draft", "Draft"),
                              ("waiting_approval", "Waiting For Approval"),
                              ("approved", "Approved"),
                              ("rejected", "Rejected"),
                              ("blacklisted", "Blacklisted"),
                              ], string='State', default="draft")
    is_approving_matrix_customer = fields.Boolean(compute="_compute_approving_matrix_customer", string="Approving Matrix Customer")
    approved_user_ids = fields.Many2many('res.users', 'approved_res_user_rel_customer', 'user_id_customer', 'line_id_customer', string="Approved User")
    approving_matrix_customer_id = fields.Many2one('approval.matrix.customer', string="Approval Matrix", compute="_compute_matrix_customer", store=True)
    approved_matrix_ids_customer = fields.One2many('approval.matrix.customer.line', 'app_matrix_id', compute="_compute_approving_matrix_lines_customer", store=True, string="Approved Matrix")
    is_approve_button_customer = fields.Boolean(string='Is Approve Button', compute='_get_approve_button_customer', store=False)
    approval_matrix_line_id_customer = fields.Many2one('approval.matrix.customer.line', string='Vendor Approval Matrix Line', compute='_get_approve_button_customer', store=False)
    
    # run this function for update state customer for exist data, just run manually oncez
    def update_state_customer(self):
        customer = self.env['res.partner'].search([('is_customer', '=', True),
                                                  ('state_customer', '=', 'draft'),
                                                  ('customer_rank', '>', 0)])
        if customer:
            for rec in customer:
                rec.state_customer = 'approved'
    
    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval = IrConfigParam.get_param('is_customer_partner_approval_matrix')
        if approval and res.is_customer:
            res.state_customer = 'draft'
        else:
            res.state_customer = 'approved'
        return res
    
    @api.depends('branch_id')
    def _compute_matrix_customer(self):
        for res in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            approval = IrConfigParam.get_param('is_customer_partner_approval_matrix')
            res.approving_matrix_customer_id = False
            if approval:
                matrix_id = self.env['approval.matrix.customer'].search([('branch_id', '=', res.branch_id.id)], limit=1)
                if matrix_id:
                    res.approving_matrix_customer_id = matrix_id
                    
    def _compute_approving_matrix_customer(self):
        is_approving_matrix = self.env['ir.config_parameter'].sudo().get_param('is_customer_partner_approval_matrix')
        for record in self:
            record.is_approving_matrix_customer = is_approving_matrix
            
    @api.depends('approving_matrix_customer_id', 'branch_id')
    def _compute_approving_matrix_lines_customer(self):
        for record in self:
            data = [(5, 0, 0)]
            counter = 1
            record.approved_matrix_ids_customer = []
            for line in record.approving_matrix_customer_id.approval_matrix_line_ids:
                data.append((0, 0, {
                    'sequence': counter,
                    'user_ids': [(6, 0, line.user_ids.ids)],
                    'minimum_approver': line.minimum_approver,
                }))
                counter += 1
            record.approved_matrix_ids_customer = data
            
    def _get_approve_button_customer(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids_customer.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button_customer = False
                record.approval_matrix_line_id_customer = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button_customer = True
                    record.approval_matrix_line_id_customer = matrix_line_id.id
                else:
                    record.is_approve_button_customer = False
                    record.approval_matrix_line_id_customer = False
            else:
                record.is_approve_button_customer = False
                record.approval_matrix_line_id_customer = False
                
    @api.onchange('branch_id')
    def _onchange_branch_customer(self):
        self._compute_approving_matrix_customer()
        self._get_approve_button_customer()
        self._compute_matrix_customer()
        
    def action_request_for_approval_customer(self):
        for record in self:
            customer_approval = self.env['approval.matrix.customer'].search([('branch_id', '=', record.branch_id.id)], limit=1)
            if not customer_approval:
                raise ValidationError(_("Please set the Customer Approval Matrix!"))
            record.write({'state_customer': 'waiting_approval'})
            
    def action_approved_customer(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for record in self:
            data = []
            user = self.env.user
            if record.is_approve_button_customer and record.approval_matrix_line_id_customer:
                approval_matrix_line_id_customer = record.approval_matrix_line_id_customer
                if user.id in approval_matrix_line_id_customer.user_ids.ids and \
                        user.id not in approval_matrix_line_id_customer.approved_users.ids:
                    name = approval_matrix_line_id_customer.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    approval_matrix_line_id_customer.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id_customer.minimum_approver == len(approval_matrix_line_id_customer.approved_users.ids):
                        approval_matrix_line_id_customer.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids_customer.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
                        approver_name = ' and '.join(approval_matrix_line_id_customer.mapped('user_ids.name'))
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': approving_matrix_line_user.partner_id.email,
                                    'user_name': approving_matrix_line_user.name,
                                    'approver_name': approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter': approver_name,
                                    'product_lines': data,
                                }
                                
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'user_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                    'approver_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter': approver_name,
                                    'product_lines': data,
                                }
                    else:
                        approval_matrix_line_id_customer.write({'approver_state': 'pending'})
            if len(record.approved_matrix_ids_customer) == len(record.approved_matrix_ids_customer.filtered(lambda r: r.approved)):
                record.write({'state_customer': 'approved'})

    def action_set_to_draft_customer(self):
        for rec in self:
            rec.write({
                'state_customer': 'draft',
                'active': True
            })
