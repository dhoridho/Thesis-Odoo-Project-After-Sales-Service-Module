from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, AccessError
from lxml import etree

class Users(models.Model):
    _inherit = "res.users"

    
    is_administrator = fields.Boolean(string='Is Administrator', default=False, help="Check this box if the user is an administrator.")
    is_member_superuser = fields.Boolean(string='Is Member Superuser', default=False, compute='_compute_is_member_superuser')
    is_from_menu = fields.Boolean(string='Is From Menu', default=False)


    @api.depends('groups_id')
    def _compute_is_member_superuser(self):
        for record in self:
            record.is_member_superuser = record.has_group('equip3_hide_administrator_user.group_superuser')


    def read(self, fields=None, load='_classic_read'):
        res = super(Users, self).read(fields=fields, load=load)
        is_external_link = self.env.context.get("default_is_external_link")
        if 'default_is_external_link' in self.env.context:
            for rec in self:
                if rec.is_administrator:
                    raise ValidationError(_('You cannot read administrator user.'))
            
        # if not self.env.user.is_administrator:
        #     for record in self:
        #         if record.is_administrator:
        #             raise AccessError(_("You are not allowed to view this user."))
        return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []

        if not self.env.user.is_administrator:
        #    domain += [('id', '!=', self.env['res.users'].search([('is_administrator', '=', True)]).id)]
            domain += [('id', 'not in', self.env['res.users'].search([('is_administrator', '=', True)]).mapped('id'))]

        else:
            domain += [('id', '!=', 1)]

        return super(Users, self).search_read(domain, fields, offset, limit, order)
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []

        if not self.env.user.is_administrator:
            # domain += [('id', '!=', self.env['res.users'].search([('is_administrator', '=', True)]).id)]
            domain += [('id', 'not in', self.env['res.users'].search([('is_administrator', '=', True)]).mapped('id'))]

        else:
            domain += [('id', '!=', 1)]

        return super(Users, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)
    

    def write(self, vals):
        res = super(Users, self).write(vals)
        if 'search_default_no_share' in self.env.context:
            for record in self:
                if record.is_administrator and not self.env.user.is_administrator:
                    raise ValidationError(_('You cannot edit administrator user.'))
        return res

    
    # def create(self, vals):
    #     res = super(Users, self).create(vals)
    #     if self.env.user.is_administrator:
    #         return res
    #     else:
    #         if 'is_administrator' in vals:
    #             raise ValidationError(_('You cannot change the administrator user.'))
    #         else:
    #             return res
            

class Groups(models.Model):
    _inherit = "res.groups"

    def get_user_count(self):
        return len(self.users)
    
    
    
    def write(self, vals):
        if self.env.context.get('install_mode'):
            # Skip validation during module installation
            return super(Groups,self).write(vals)

        if 'search_default_no_share' in self.env.context:
            for rec in self:
                group = rec.browse(rec.id)
                user_count = group.get_user_count()

                if user_count > 0 and 'users' in vals:
                    for command in vals['users']:
                        if not self.env.user.is_administrator:
                            raise ValidationError(_('You cannot remove the administrator user from this group.'))

        return super(Groups,self).write(vals)
            
