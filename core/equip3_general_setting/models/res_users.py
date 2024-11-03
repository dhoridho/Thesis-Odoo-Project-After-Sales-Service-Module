from odoo import models, fields, api, _
from odoo.tools import lazy_property
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    # User can write on a few of his own fields (but not his groups for example)
    SELF_WRITEABLE_FIELDS = ['signature', 'action_id', 'company_id', 'branch_id', 'email', 'name', 'image_1920', 'lang', 'tz']
    # User can read a few of his own fields
    SELF_READABLE_FIELDS = ['signature', 'company_id', 'branch_id', 'login', 'email', 'name', 'image_1920', 'image_1024', 'image_512', 'image_256', 'image_128', 'lang', 'tz', 'tz_offset', 'groups_id', 'partner_id', '__last_update', 'action_id']


    show_branch = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch)
    branch_ids = fields.Many2many('res.branch', string='Allowed Branch', default=lambda self: self.env.branches)

    # technical fields
    is_superuser = fields.Boolean(compute='_compute_is_superuser')

    def _compute_is_superuser(self):
        for user in self:
            user.is_superuser = user._is_superuser()

    @api.model
    def default_get(self, field_list):
        defaults = super(ResUsers, self).default_get(field_list)
        context = self.env.context
        defaults['branch_id'] = context.get('default_branch_id', self.env.branch.id)
        defaults['branch_ids'] = context.get('default_branch_ids', [(6, 0, self.env.branches.ids)])
        return defaults

    @api.model
    def create(self, values):
        is_values_doesnt_contains_branch = 'branch_id' not in values or 'branch_ids' not in values
        if is_values_doesnt_contains_branch:
            self = self.with_context(bypass_constrains=True)
        
        users = super(ResUsers, self).create(values)
        for user in users:
            # if partner is global we keep it that way
            if user.partner_id.branch_id:
                user.partner_id.branch_id = user.branch_id

            if is_values_doesnt_contains_branch:
                user.company_ids._create_and_assign_branch(user)
        return users

    def write(self, values):
        if self == self.env.user:
            for key in list(values):
                if not (key in self.SELF_WRITEABLE_FIELDS or key.startswith('context_')):
                    break
            else:
                if 'branch_id' in values:
                    if values['branch_id'] not in self.env.user.branch_ids.ids:
                        del values['branch_id']
                # safe fields only, so we write as super-user to bypass access rights
                self = self.sudo().with_context(binary_field_real_user=self.env.user)

        res = super(ResUsers, self).write(values)

        if 'branch_id' in values:
            for user in self:
                # if partner is global we keep it that way
                if user.partner_id.branch_id and user.partner_id.branch_id.id != values['branch_id']:
                    user.partner_id.write({'branch_id': user.branch_id.id})

        if 'branch_id' in values or 'branch_ids' in values:
            # Reset lazy properties `branch` & `branches` on all envs
            # This is unlikely in a business code to change the company of a user and then do business stuff
            # but in case it happens this is handled.
            # e.g. `account_test_savepoint.py` `setup_company_data`, triggered by `test_account_invoice_report.py`
            for env in list(self.env.envs):
                if env.user in self:
                    lazy_property.reset_all(env)

        # clear caches linked to the users
        if self.ids and 'groups_id' in values:
            # DLE P139: Calling invalidate_cache on a new, well you lost everything as you wont be able to take it back from the cache
            # `test_00_equipment_multicompany_user`
            self.env['ir.model.access'].call_cache_clearing_methods()

        if 'branch_id' in values:
            self.clear_caches()

        return res

    @api.constrains('branch_id', 'branch_ids')
    def _check_branch(self):
        """ Add user.with_context(bypass_constrains=True) to pass this constrains """
        if self.env.context.get('bypass_constrains', False):
            return
        if any(user.branch_id not in user.branch_ids for user in self):
            raise ValidationError(_('The chosen branch is not in the allowed branches for this user'))

        for user in self:
            user_companies = user.company_ids.sudo()
            user_branches = user.branch_ids
            for company in user_companies:
                if not user_branches.filtered(lambda b: b.company_id == company):
                    raise ValidationError(_('Company %s required at least one branch active!' % company.name))

    @api.onchange('company_id', 'company_ids')
    def _onchange_companies(self):
        user_companies = self.company_ids.sudo()

        if self.company_id.id not in user_companies.ids:
            company_id = False
            if user_companies.ids:
                company_id = user_companies.ids[0]
            self.company_id = company_id

        branch_to_add = []
        for company in user_companies:
            if not self.branch_ids.filtered(lambda b: b.company_id.id in company.ids) and company.branch_ids.ids:
                branch_to_add += [(4, company.branch_ids.ids[0])]

        branch_to_remove = [(3, branch.id) for branch in self.branch_ids.filtered(
            lambda b: b.company_id.id not in user_companies.ids)]

        self.branch_ids = branch_to_add + branch_to_remove
        if self.branch_id and self.branch_id.company_id.id != self.company_id.id:
            branch = False
            company_branches = self.branch_ids.filtered(lambda b: b.company_id == self.company_id)
            if company_branches.ids:
                branch = company_branches.ids[0]
            self.branch_id = branch

    @api.onchange('branch_ids')
    def _onchange_branches(self):
        if self.branch_id.id not in self.branch_ids.ids:
            branch_ids = self.branch_ids.filtered(lambda b: b.company_id.id == self.company_id.id)
            self.branch_id = branch_ids and (branch_ids[0].id or branch_ids[0]._origin.id) or False
        
    def _check_and_assign_branch(self):
        for user in self:
            # create default branches for each company
            user_companies = user.company_ids.sudo()
            user_branches = user.branch_ids
            for company in user_companies:
                if not user_branches.filtered(lambda b: b.company_id == company):
                    if not company.branch_ids:
                        company._create_and_assign_branch(user)
                    else:
                        user.with_context(bypass_constrains=True).write({'branch_ids': [(4, company.branch_ids[0].id)]})

            # create default branch for each company
            user_branch = user.branch_id
            if not user_branch:
                company_branches = user.company_ids[0].branch_ids
                user.with_context(bypass_constrains=True).write({'branch_id': company_branches[0].id})

            if user.branch_id and user.branch_id.company_id.id != user.company_id.id:
                company_branches = user.branch_ids.filtered(lambda b: b.company_id == user.company_id)
                if company_branches:
                    user.branch_id = company_branches[0].id

    def read_company_branches(self, company_id):
        self.ensure_one()
        return [{
            'id': branch.id,
            'company_id': branch.company_id.id
        } for branch in self.branch_ids.filtered(lambda o: o.company_id.id == company_id)]


class UsersView(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for values in vals_list:
            new_vals_list.append(self._remove_reified_groups(values))
        users = super(UsersView, self).create(new_vals_list)
        group_multi_branch_id = self.env['ir.model.data'].xmlid_to_res_id(
            'base.group_multi_branch', raise_if_not_found=False)
        if group_multi_branch_id:
            for user in users:
                if len(user.branch_ids) <= 1 and group_multi_branch_id in user.groups_id.ids:
                    user.write({'groups_id': [(3, group_multi_branch_id)]})
                elif len(user.branch_ids) > 1 and group_multi_branch_id not in user.groups_id.ids:
                    user.write({'groups_id': [(4, group_multi_branch_id)]})
        return users

    def write(self, values):
        values = self._remove_reified_groups(values)
        res = super(UsersView, self).write(values)
        if 'branch_ids' not in values:
            return res
        group_multi_branch = self.env.ref('base.group_multi_branch', False)
        if group_multi_branch:
            for user in self:
                if len(user.branch_ids) <= 1 and user.id in group_multi_branch.users.ids:
                    user.write({'groups_id': [(3, group_multi_branch.id)]})
                elif len(user.branch_ids) > 1 and user.id not in group_multi_branch.users.ids:
                    user.write({'groups_id': [(4, group_multi_branch.id)]})
        return res
