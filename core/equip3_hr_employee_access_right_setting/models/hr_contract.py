from odoo import models, fields, api, _
from odoo.osv import expression
from lxml import etree
from odoo.exceptions import ValidationError


class HrContractInheritEquip3HrEmployee(models.Model):
    _inherit = 'hr.contract'
    
    
    is_hide_details = fields.Boolean(default=False,compute='_compute_is_hide_details')
    
    
    def action_contract_email(self):
        partner_ids = []
        self.update_email_to_res_partner()
        for record in self:
            if not record.partner_id:
                raise ValidationError("Sorry, you can't send a contract letter because the employee (%s) is not mapped to related user" % record.employee_id.name)
            if not record.contract_template:
                raise ValidationError("Sorry, you can't send a contract letter. Because the Contract Template (%s) field has not been filled" % record.name)
            # if record.employee_id and record.employee_id.user_id and record.employee_id.user_id.partner_id:
            partner_ids.append(record.partner_id.id)
        return {
            'name': 'Compose Email',
            'type': 'ir.actions.act_window',
            'res_model': 'contract.batch.email.template',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_ids': [(6,0,self.ids)],
                'default_parent_ids': [(6,0,partner_ids)]
            },
        }

    
    
    
    
    
    @api.depends('create_date')
    def _compute_is_hide_details(self):
        for record in self:
            if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
                if record.employee_id.id != self.env.user.employee_id.id:
                    record.is_hide_details = True
                else:
                    record.is_hide_details = False
            else:
                record.is_hide_details = False
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrContractInheritEquip3HrEmployee, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('hr.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer') and not self.env.user.has_group('hr.group_hr_manager'):
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
            if 'state' in res['fields']:
                res['fields']['state']['readonly'] = True
            
        return res

    def custom_menu(self):
        search_view_id = self.env.ref("hr_contract.hr_contract_view_search")
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Contract',
                'res_model': 'hr.contract',
                'target':'current',
                'view_mode': 'kanban,tree,form,activity',
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                'search_view_id':search_view_id.id,
                
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Contract',
                'res_model': 'hr.contract',
                'target':'current',
                'view_mode': 'kanban,tree,form,activity',
                'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                'search_view_id':search_view_id.id,
            }


