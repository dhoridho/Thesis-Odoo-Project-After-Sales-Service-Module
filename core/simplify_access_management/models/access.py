from odoo import fields, models, api, _
from odoo.exceptions import UserError

class access_domain_ah(models.Model):
    _name = 'access.domain.ah'
    _description = 'Access Domain'


    model_id = fields.Many2one(
        'ir.model', string='Model', index=True, required=True, ondelete='cascade')
    model_name = fields.Char(string='Model Name', related='model_id.model', readonly=True, store=True)
    apply_domain = fields.Boolean('Apply Filter')
    domain = fields.Char(string='Filter', default='[]',
                         help="The create customised domain rule where we can customise rule by selecting specific fields and records")

    access_management_id = fields.Many2one('access.management','Access Management')

    read_right = fields.Boolean('Read',default=True, help="The set 'Read' access of the selected model for the specified users")
    create_right = fields.Boolean('Create', help="The set 'Create' access of the selected model for the specified users")
    write_right = fields.Boolean('Write', help="The set 'Write' access of the selected model for the specified users")
    delete_right = fields.Boolean('Delete', help="The set 'Delete' access of the selected model for the specified users")

    @api.onchange('apply_domain')
    def _check_domain(self):
        for rec in self:
            if not rec.apply_domain:
                rec.domain = False

    @api.onchange('read_right')
    def _check_read(self):
        for rec in self:
            if not rec.read_right:
                rec.create_right = False
                rec.write_right = False
                rec.delete_right = False
                rec.apply_domain = True
                rec.domain = '[["id","=",False]]'


    @api.onchange('create_right')
    def _check_create(self):
         for rec in self:
            if rec.create_right:
                rec.read_right = True
            else:
                rec.delete_right = False    

    @api.onchange('write_right')
    def _check_write(self):
         for rec in self:
            if rec.write_right:
                rec.read_right = True
            else:
                rec.delete_right = False

    @api.onchange('delete_right')
    def _check_delete(self):
         for rec in self:
            if rec.delete_right:
                rec.read_right = True
                rec.write_right = True



class access_management(models.Model):
    _name = 'access.management'
    _description = "Access Management"

    name = fields.Char('Name')
    user_ids = fields.Many2many('res.users', 'access_management_users_rel_ah', 'access_management_id', 'user_id',
                                'Users')

    readonly = fields.Boolean('Read-Only')
    active = fields.Boolean('Active', default=True)

    hide_menu_ids = fields.Many2many('ir.ui.menu', 'access_management_menu_rel_ah', 'access_management_id', 'menu_id',
                                     'Hide Menu',
                                     help="The menu or submenu added on above list will be hidden from the defined users.")
    hide_field_ids = fields.One2many('hide.field', 'access_management_id', 'Hide Field', copy=True)

    remove_action_ids = fields.One2many('remove.action', 'access_management_id', 'Remove Action', copy=True)

    access_domain_ah_ids = fields.One2many('access.domain.ah', 'access_management_id', 'Access Domain', copy=True)
    hide_view_nodes_ids = fields.One2many('hide.view.nodes', 'access_management_id', 'Button/Tab Access', copy=True)

    self_module_menu_ids = fields.Many2many('ir.ui.menu', 'access_management_ir_ui_self_module_menu',
                                            'access_management_id', 'menu_id', 'Self Module Menu',
                                            compute="_get_self_module_info")
    self_model_ids = fields.Many2many('ir.model', 'access_management_ir_model_self', 'access_management_id', 'model_id',
                                      'Self Model', compute="_get_self_module_info")
    total_rules = fields.Integer('Access Rules', compute="_count_total_rules")

    # Chatter
    hide_chatter_ids = fields.One2many('hide.chatter', 'access_management_id', 'Hide Chatter', copy=True)

    hide_chatter = fields.Boolean('Hide Chatter',
                                  help="The Chatter will be hidden in all model from the specified users.")
    hide_send_mail = fields.Boolean('Hide Send Message',
                                    help="The Send Message button will be hidden in chatter of all model from the specified users.")
    hide_log_notes = fields.Boolean('Hide Log Notes',
                                    help="The Log Notes button will be hidden in chatter of all model from the specified users.")
    hide_schedule_activity = fields.Boolean('Hide Schedule Activity',
                                            help="The Schedule Activity button will be hidden in chatter of all model from the specified users.")

    hide_export = fields.Boolean(help="The Export button will be hidden in all model from the specified users.")
    hide_import = fields.Boolean(help="The Import button will be hidden in all model from the specified users.")
    disable_login = fields.Boolean('Disable Login',help="The Users can not login if this button is chek.")

    disable_debug_mode = fields.Boolean('Disable Developer Mode',
                                        help="Developer mode will be hidden from the defined users.")

    company_ids = fields.Many2many('res.company', 'access_management_comapnay_rel', 'access_management_id',
                                   'company_id', 'Companies', required=True, default=lambda self: self.env.company)

    hide_filters_groups_ids = fields.One2many('hide.filters.groups', 'access_management_id', 'Hide Filters/Group By',
                                              copy=True)
    is_all_users = fields.Boolean('Apply to all users')


    @api.onchange('is_all_users')
    def _onchange_implied_to_all_user(self):
        for rec in self:
            if rec.is_all_users:
                user_ids = self.env['res.users'].search([('share','=',False)])

                rec.user_ids = [(6, 0, [x.id for x in user_ids])]
            else:
                rec.user_ids = [(6, 0, [])]


    def _count_total_rules(self):
        for rec in self:
            rule = 0
            rule = rule + len(rec.hide_menu_ids) + len(rec.hide_field_ids) + len(rec.remove_action_ids) + len(
                rec.access_domain_ah_ids) + len(rec.hide_view_nodes_ids)
            rec.total_rules = rule

    def action_show_rules(self):
        pass

    def _get_self_module_info(self):
        access_menu_id = self.env.ref('simplify_access_management.main_menu_simplify_access_management')
        model_list = ['access.management', 'access.domain.ah', 'action.data', 'hide.field', 'hide.view.nodes',
                      'store.model.nodes', 'remove.action', 'view.data']
        models_ids = self.env['ir.model'].search([('model', 'in', model_list)])
        for rec in self:
            rec.self_module_menu_ids = False
            rec.self_model_ids = False
            if access_menu_id:
                rec.self_module_menu_ids = [(6, 0, access_menu_id.ids)]
            if models_ids:
                rec.self_model_ids = [(6, 0, models_ids.ids)]

    def toggle_active_value(self):
        for record in self:
            record.write({'active': not record.active})
        return True

    @api.model
    def create(self, vals):
        res = super(access_management, self).create(vals)
        # for user in self.env['res.users'].sudo().search([('share','=',False)]):
        # user.clear_caches()
        self.clear_caches()
        for record in res:
            if record.readonly:
                for user in record.user_ids:
                    if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
                        raise UserError(_('Admin user can not be set as a read-only..!'))
        return res

    def unlink(self):
        res = super(access_management, self).unlink()
        self.clear_caches()
        # for user in self.env['res.users'].sudo().search([('share','=',False)]):
        #     user.clear_caches()
        return res

    def write(self, vals):
        res = super(access_management, self).write(vals)

        if self.readonly:
            for user in self.user_ids:
                if user.has_group('base.group_system') or user.has_group('base.group_erp_manager'):
                    raise UserError(_('Admin user can not be set as a read-only..!'))
        # for user in self.env['res.users'].sudo().search([('share','=',False)]):
        #     user.clear_caches()
        self.clear_caches()
        return res

    def get_remove_options(self, model):
        restrict_export = self.env['access.management'].search([('company_ids', 'in', self.env.company.id),
                                                                ('active', '=', True),
                                                                ('user_ids', 'in', self.env.user.id),
                                                                ('hide_export', '=', True)], limit=1).id
        remove_action = self.env['remove.action'].sudo().search(
            [('access_management_id.company_ids', 'in', self.env.company.id),
             ('access_management_id', 'in', self.env.user.access_management_ids.ids), ('model_id.model', '=', model)])
        options = []
        added_export = False
        if restrict_export:
            options.append(_('Export'))
            added_export = True

        for action in remove_action:
            if not added_export and action.restrict_export:
                options.append(_('Export'))
            if action.restrict_archive_unarchive:
                options.append(_('Archive'))
                options.append(_('Unarchive'))
            if action.restrict_duplicate:
                options.append(_('Duplicate'))
        return options

    @api.model
    def get_chatter_hide_details(self, company_id, model=False):
        user_id = self.env.user.id
        hide_send_mail = True
        hide_log_notes = True
        hide_schedule_activity = True

        access_ids = self.search([('user_ids', 'in', user_id), ('company_ids', 'in', company_id)])
        for access in access_ids:
            if access.hide_chatter:
                hide_send_mail = False
                hide_log_notes = False
                hide_schedule_activity = False
                break

            if access.hide_send_mail:
                hide_send_mail = False

            if access.hide_log_notes:
                hide_log_notes = False

            if access.hide_schedule_activity:
                hide_schedule_activity = False

        if model and hide_send_mail or hide_log_notes or hide_schedule_activity:
            hide_ids = self.env['hide.chatter'].search([('access_management_id.company_ids', 'in', company_id),
                                                        ('access_management_id.active', '=', True),
                                                        ('access_management_id.user_ids', 'in', user_id),
                                                        ('model_id.model', '=', model)])

            if hide_ids:
                if hide_send_mail and hide_ids.filtered(lambda x: x.hide_send_mail):
                    hide_send_mail = False

                if hide_log_notes and hide_ids.filtered(lambda x: x.hide_log_notes):
                    hide_log_notes = False

                if hide_schedule_activity and hide_ids.filtered(lambda x: x.hide_schedule_activity):
                    hide_schedule_activity = False

        return {
            'hide_send_mail': hide_send_mail,
            'hide_log_notes': hide_log_notes,
            'hide_schedule_activity': hide_schedule_activity
        }

    @api.model
    def is_export_n_upload_hide(self, company_id, model=False):
        user_id = self.env.user.id
        hide_export = False
        hide_upload = False
        access_ids = self.search(
            [('user_ids', 'in', user_id), ('company_ids', 'in', company_id), ('active', '=', True)])

        for access in access_ids:
            if access.hide_export:
                hide_export = True
                break

        if not hide_export and model:
            check = self.env['remove.action'].search([('access_management_id', 'in', access_ids.ids),('model_id.model', '=', model)])
            if check.filtered(lambda x: x.restrict_export):
                hide_export = True
            if check.filtered(lambda x: x.restrict_upload_acc_move):
                hide_upload = True
                
        return [hide_export,hide_upload]
        
    def get_hidden_field(self, model=False):
        if model:
            hidden_fields = []
            hide_field_obj = self.env['hide.field'].sudo()
            for hide_field in hide_field_obj.search(
                        [('access_management_id.company_ids', 'in', self.env.company.id),
                         ('model_id.model', '=', model), ('access_management_id.active', '=', True),
                         ('access_management_id.user_ids', 'in', self._uid), ('invisible', '=', True)]):
                for field in hide_field.field_id:
                    if field.name:
                        hidden_fields.append(field.name)
            return hidden_fields
        return []