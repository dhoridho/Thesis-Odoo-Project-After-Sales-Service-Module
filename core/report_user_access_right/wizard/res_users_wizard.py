# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo import models, fields, api
from odoo.exceptions import UserError

COLUMN_LIMIT = 15
PARAMETER_KEY = 'res.users.access.report.default'

SORT_TYPES = [
    ('create_date', 'Creation Date'),
    ('name', 'Name'),
]


class ResUsersWizard(models.TransientModel):
    _name = "res.users.access.report.wizard"

    group_ids = fields.Many2many('res.groups')
    show_login = fields.Boolean()
    sort_type = fields.Selection(SORT_TYPES, string='Sort By', default='create_date')
    sort_type_mode = fields.Selection([('asc', 'Ascending'), ('desc', 'Descending')], string='Order', default='asc')
    user_tag_ids = fields.Many2many('res.users.tag', string='Filter By Tag')
    show_archived = fields.Boolean(string='Show Archived', default=False)
    show_group_category = fields.Boolean()

    @api.model
    def default_get(self, fields):
        res = super(ResUsersWizard, self).default_get(fields)
        parameter_obj = self.env['ir.config_parameter']
        try:
            vals = literal_eval(parameter_obj.get_param(PARAMETER_KEY, False))
            if vals:
                res['group_ids'] = vals['group_ids']
                res['show_login'] = vals.get('show_login')
                res['show_group_category'] = vals.get('show_group_category')
                res['sort_type'] = vals.get('sort_type') or 'create_date'
                res['sort_type_mode'] = vals.get('sort_type_mode') or 'asc'
                res['user_tag_ids'] = vals.get('user_tag_ids') or []
                res['show_archived'] = vals.get('show_archived')
        except:
            pass
        return res

    def get_access(self, column, user_id=False):
        self.ensure_one()
        sheet = {}
        count = 0
        for g in self.group_ids.sorted(key='id'):
            count += 1
            access = bool(user_id.id in g.users.ids) if user_id else False
            g_name = g.name
            if self.show_group_category:
                g_name = '%s / %s' % (g.category_id.name or '', g.name)
            sheet['column'+str(count)] = (g_name, access)
        if column in sheet:
            return sheet[column]
        return False, False

    def update_report(self):
        record_obj = self.env['res.users.access.report.record']
        record_obj.search([]).unlink()
        view_id = self.env.ref('report_user_access_right.view_tree_res_users_access_report_record')

        arch = """
        <tree create="0" delete="0" edit="0" decoration-muted="user_active == False">
            <field name="sl_no"/>
            <field name="user_id"/>
            <field name="user_active" invisible="1"/>
        """
        if self.show_login:
            arch += "<field name='login'/>"

        for col in range(1, COLUMN_LIMIT+1):
            col_name = 'column' + str(col)
            label_column = self.get_access(col_name)[0]
            if label_column:
                arch += """<field name="%s" string="%s"/>\n""" % (col_name, label_column)
        arch += """<button name="open_user_form" type="object" string="Edit"/>"""
        arch += "\n</tree>"
        view_id.sudo().write({'arch_base': arch})
        count = 0
        order = '%s %s' % (self.sort_type, self.sort_type_mode)
        domain = ['|', ('active', '=', True), ('active', '=', False)]
        for user_id in self.env['res.users'].search(domain, order=order):
            if self.user_tag_ids and user_id.user_tag_id.id not in self.user_tag_ids.ids:
                continue

            if not self.show_archived and not user_id.active:
                continue

            count += 1
            vals = {
                'sl_no': count,
                'user_id': user_id.id,
                'login': user_id.login,
                'user_active': user_id.active,
            }
            for col in range(1, COLUMN_LIMIT + 1):
                col_name = 'column' + str(col)
                vals[col_name] = self.get_access(col_name, user_id)[1]
            record_obj.create(vals)

    def update_parameters(self):
        parameter_obj = self.env['ir.config_parameter']
        vals = {
            'group_ids': self.group_ids.ids,
            'show_login': self.show_login,
            'show_group_category': self.show_group_category,
            'sort_type': self.sort_type,
            'sort_type_mode': self.sort_type_mode,
            'user_tag_ids': self.user_tag_ids.ids,
            'show_archived': self.show_archived,
        }
        try:
            parameter_obj.set_param(PARAMETER_KEY, str(vals))
        except:
            pass

    def action_open_report(self):
        if not self.group_ids:
            raise UserError('Choose at least one group.')

        if len(self.group_ids) > COLUMN_LIMIT:
            raise UserError('Maximum column limit is 15.')

        self.sudo().update_report()
        self.sudo().update_parameters()
        return {
            'name': 'Access Rights Report',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'res.users.access.report.record',
        }

# todo activate developer mode for tag
#