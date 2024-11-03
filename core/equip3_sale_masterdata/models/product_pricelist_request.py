from odoo import models, fields, api, _
from odoo.tools import format_datetime


class ProductPricelistRequest(models.Model):
    _name = 'product.pricelist.request'
    _description = 'Product Pricelist Request'
    _inherit = 'product.pricelist'

    @api.model
    def create(self, values):
        if values.get('name', _('New')) == _('New'):
            values['name'] = self.env['ir.sequence'].next_by_code('product.pricelist.request') or _('New')
        return super(ProductPricelistRequest, self).create(values)

    @api.model
    def _default_branch(self):
        if len(self.env.branches) == 1:
            return self.env.branch.id
        return False

    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.branch
        
        return self.env['product.pricelist.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id)
        ], limit=1).id

    @api.depends('approval_matrix_id')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = [(5,)]
            for line in record.approval_matrix_id.line_ids:
                lines += [(0, 0, {
                    'line_id': line.id,
                    'sequence': line.sequence,
                    'minimum_approver': line.minimum_approver,
                    'approver_ids': [(6, 0, line.approver_ids.ids)]
                })]
            record.approval_matrix_line_ids = lines

    @api.depends('approval_matrix_line_ids', 'approval_matrix_line_ids.need_action_ids', 'next_approver_ids')
    def _compute_user_is_approver(self):
        user = self.env.user
        for record in self:
            need_action_ids = record.approval_matrix_line_ids.mapped('need_action_ids')
            next_approver_ids = record.next_approver_ids
            record.user_is_approver = user in need_action_ids and user in next_approver_ids

    @api.depends('approval_matrix_line_ids', 'approval_matrix_line_ids.state')
    def _compute_next_approvers(self):
        for record in self:
            approval_lines = record.approval_matrix_line_ids.filtered(lambda o: o.state == 'to_approve')
            next_approver_ids = []
            if approval_lines:
                line = approval_lines[0]
                next_approver_ids = list(set(line.approver_ids.ids) - set(line.approved_ids.ids + line.rejected_ids.ids))
            record.next_approver_ids = [(6, 0, next_approver_ids)]

    name = fields.Char(default=lambda self: _('New'))
    pricelist_name = fields.Char()

    request_type = fields.Selection(selection=[
        ('create', 'New Pricelist'),
        ('write', 'Update Pricelist')
    ], default='create', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist to Update')
    item_request_ids = fields.One2many('product.pricelist.request.item', 'pricelist_request_id', 'Pricelist Items', copy=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=_default_branch)
    create_uid = fields.Many2one('res.users', string='Created By', required=True, default=lambda self: self.env.user)
    create_date = fields.Datetime(string='Created On', required=True, default=lambda self: fields.Datetime.now())
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('approval', 'To be Approved'),
        ('approved', 'Confirmed'),
        ('rejected', 'Rejected'),
    ], default='draft', string='Status', required=True)

    country_group_ids = fields.Many2many('res.country.group', 'res_country_group_pricelist_request_rel', 'pricelist_request_id', 'res_country_group_id', string='Country Groups')
    
    approval_matrix_id = fields.Many2one(
        comodel_name='product.pricelist.approval.matrix', 
        domain="""[
            ('branch_id', '=', branch_id),
            ('company_id', '=', company_id)
        ]""",
        string='Approval Matrix', 
        required=True,
        default=_default_approval_matrix)
    
    approval_matrix_line_ids = fields.One2many(
        comodel_name='product.pricelist.approval.entry',
        inverse_name='pricelist_request_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)
    
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)
    next_approver_ids = fields.Many2many('res.users', compute='_compute_next_approvers')

    @api.onchange('company_id', 'branch_id')
    def onchange_branch_id(self):
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)

    @api.onchange('request_type')
    def _onchange_request_type(self):
        if self.request_type != 'write':
            self.pricelist_id = False
        elif self.request_type != 'create':
            self.pricelist_name = False

    @api.onchange('pricelist_id')
    def _onchnage_pricelist_id(self):
        pricelist_item_fields = self.env['product.pricelist.item']._fields

        item_vals_list = [(5,)]
        for item in self.pricelist_id.item_ids:
            item_values = {}
            for item_field_name, item_field in pricelist_item_fields.items():
                if item_field.type == 'many2one':
                    item_values[item_field_name] = item[item_field_name].id
                elif item_field.type in ('one2many', 'many2many'):
                    item_values[item_field_name] = [(6, 0, item[item_field_name].ids)]
                else:
                    item_values[item_field_name] = item[item_field_name]

            item_values['pricelist_item_id'] = item.id
            item_vals_list += [(0, 0, item_values)]
        self.item_request_ids = item_vals_list

    def action_approval(self):
        self.ensure_one()
        now = fields.Datetime.now()
        entry_ids = self.approval_matrix_line_ids
        for entry in entry_ids:
            entry.write({
                'requested_id': self.env.user.id,
                'requested_time': now,
                'line_ids': [(0, 0, {
                    'approver_id': approver.id,
                    'state': 'to_approve'
                }) for approver in entry.approver_ids]
            })
        self.state = 'approval'
        return True

    def action_approve(self):
        self.ensure_one()
        now = fields.Datetime.now()
        now_formatted = format_datetime(self.env, now)
        entry_ids = self.approval_matrix_line_ids.filtered(lambda o: o.state == 'to_approve')

        for entry in entry_ids:
            entry_lines = entry.line_ids
            entry_line_id = entry_lines.filtered(lambda l: l.approver_id == self.env.user)
            if not entry_line_id:
                continue
            entry.write({
                'line_ids': [(1, entry_line_id.id, {
                    'state': 'approved',
                    'note': 'Approved By: %s, %s' % (self.env.user.name, now_formatted),
                    'action_time': now
                })],
            })
        if not all(o.state == 'approved' for o in self.approval_matrix_line_ids):
            return True

        pricelist_fields = self.env['product.pricelist']._fields
        pricelist_item_fields = self.env['product.pricelist.item']._fields

        if self.request_type == 'create':
            values = {}
            for field_name, field in pricelist_fields.items():
                if field_name == 'name':
                    values[field_name] = self.pricelist_name
                    continue
                elif field_name == 'item_ids':
                    continue

                if field.type == 'many2one':
                    values[field_name] = self[field_name].id
                elif field.type in ('one2many', 'many2many'):
                    values[field_name] = [(6, 0, self[field_name].ids)]
                else:
                    values[field_name] = self[field_name]

            values['item_ids'] = []
            for item in self.item_request_ids:
                item_values = {}
                for item_field_name, item_field in pricelist_item_fields.items():
                    if item_field.type == 'many2one':
                        item_values[item_field_name] = item[item_field_name].id
                    elif item_field.type in ('one2many', 'many2many'):
                        item_values[item_field_name] = [(6, 0, item[item_field_name].ids)]
                    else:
                        item_values[item_field_name] = item[item_field_name]

                values['item_ids'] += [(0, 0, item_values)]
            self.env['product.pricelist'].create(values)

        else:
            values = {}
            for field_name, field in pricelist_fields.items():
                if field_name in ('name', 'item_ids', 'pricelist_history_ids'):
                    continue
                value = self[field_name]
                if field.type == 'many2one':
                    values[field_name] = value.id
                elif field.type in ('one2many', 'many2many'):
                    values[field_name] = [(6, 0, value.ids)]
                else:
                    values[field_name] = value

            values['item_ids'] = []
            for item in self.item_request_ids:
                pricelist_item = item.pricelist_item_id
                item_values = {}
                for item_field_name, item_field in pricelist_item_fields.items():
                    if item_field.type == 'many2one':
                        item_values[item_field_name] = item[item_field_name].id
                    elif item_field.type in ('one2many', 'many2many'):
                        item_values[item_field_name] = [(6, 0, item[item_field_name].ids)]
                    else:
                        item_values[item_field_name] = item[item_field_name]

                if pricelist_item:
                    values['item_ids'] += [(1, pricelist_item.id, item_values)]
                else:
                    values['item_ids'] += [(0, 0, item_values)]

            request_items = self.item_request_ids.mapped('pricelist_item_id')
            for item in self.pricelist_id.item_ids:
                if item not in request_items:
                    values['item_ids'] += [(2, item.id)]

            if not values['item_ids']:
                del values['item_ids']

            self.pricelist_id.write(values)
        
        self.write({'state': 'approved'})

        return True

    def action_reject(self, reason=False):
        self.ensure_one()

        if not self.env.context.get('skip_reject_wizard'):
            return {
                'type': 'ir.actions.act_window',
                'name': _('Reject Reason'),
                'res_model': 'product.pricelist.approval.matrix.reject',
                'target': 'new',
                'view_mode': 'form',
                'context': {
                    'default_pricelist_request_id': self.id,
                }
            }

        now = fields.Datetime.now()
        now_formatted = format_datetime(self.env, now)
        entry_ids = self.approval_matrix_line_ids.filtered(lambda o: o.state == 'to_approve')

        for entry in entry_ids:
            entry_lines = entry.line_ids
            entry_line_id = entry_lines.filtered(lambda l: l.approver_id == self.env.user)
            if not entry_line_id:
                continue
            note = 'Rejected By: %s, %s' % (self.env.user.name, now_formatted)
            if reason:
                note += ', Reason: %s' % reason
            entry.write({
                'line_ids': [(1, entry_line_id.id, {
                    'state': 'rejected',
                    'note': note,
                    'action_time': now
                })],
            })

        if any(o.state == 'rejected' for o in self.approval_matrix_line_ids):
            self.write({'state': 'rejected'})
        
        return True


class ProductPricelistRequestItem(models.Model):
    _name = 'product.pricelist.request.item'
    _description = 'Product Pricelist Request Item'
    _inherit = 'product.pricelist.item'

    pricelist_request_id = fields.Many2one('product.pricelist.request', required=True, ondelete='cascade')
    pricelist_item_id = fields.Many2one('product.pricelist.item', string='Pricelist Item')

    @api.constrains('applied_on','pricelist_uom_id','min_quantity','date_start','date_end')
    def _check_same_pricelist_rule(self):
        pass
