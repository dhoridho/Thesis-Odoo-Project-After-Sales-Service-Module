# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Anusha @cybrosys(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from lxml import etree
from datetime import datetime


class OrientationChecklistRequest(models.Model):
    _name = 'orientation.request'
    _description = "Employee Orientation Request"
    _rec_name = 'request_name'
    _inherit = 'mail.thread'
    
    @api.model
    def _multi_company_domain(self):
        return [('employee_company','=', self.env.company.id)]

    @api.model
    def _company_employee_domain(self):
        return [('company_id','=', self.env.company.id)]

    request_name = fields.Char(string='Name')
    request_orientation = fields.Many2one('employee.orientation', string='Employee Orientation',domain=_multi_company_domain)
    employee_company = fields.Many2one('res.company', string='Company', required=True,
                                       default=lambda self: self.env.company.id)
    partner_id = fields.Many2one('res.users', string='Responsible User')
    request_date = fields.Date(string="Date" ,default=datetime.now())
    employee_id = fields.Many2one('hr.employee', string='Employee',domain=_company_employee_domain)
    request_expected_date = fields.Date(string="Expected Date")
    attachment_id_1 = fields.Many2many('ir.attachment', 'orientation_rel_1', string="Attachment")
    note_id = fields.Text('Description')
    user_id = fields.Many2one('res.users', string='users', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company.id)
    state = fields.Selection([
        ('new', 'New'),
        ('cancel', 'Cancel'),
        ('complete', 'Completed'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='new')
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_company', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(OrientationChecklistRequest, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_company', 'in', self.env.context.get('allowed_company_ids'))])
        return super(OrientationChecklistRequest, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(OrientationChecklistRequest, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)

        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res
    
    def custom_menu(self):
        views = [(self.env.ref('employee_orientation.view_orientation_request_tree').id,'tree'),
                 (self.env.ref('employee_orientation.view_orientation_request_form').id,'form')]
        search_view_id = self.env.ref('employee_orientation.view_orientation_request_search').id
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Orientation Request',
                'res_model': 'orientation.request',
                'view_mode': 'tree,form',
                'views':views,
                'search_view_id':search_view_id,
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'help':"""<p class="o_view_nocontent_smiling_face">Create Orientation Requests.</p>
            """
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Orientation Request',
                'res_model': 'orientation.request',
                'view_mode': 'tree,form',
                'views':views,
                'search_view_id':search_view_id,
                'help':"""<p class="o_view_nocontent_smiling_face">Create Orientation Requests.</p>"""
            }

    def confirm_send_mail(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('employee_orientation', 'orientation_request_mailer')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'orientation.request',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def confirm_request(self):
        self.write({'state': "complete"})

    def cancel_request(self):
        self.write({'state': "cancel"})
