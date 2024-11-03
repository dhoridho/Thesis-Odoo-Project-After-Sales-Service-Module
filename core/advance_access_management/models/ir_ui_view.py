from odoo import models, SUPERUSER_ID, _
from odoo.tools.translate import _
import ast
from odoo.addons.simplify_access_management.models.ir_ui_view import ir_ui_view
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError


def _apply_groups(self, node, name_manager, node_info):
        
        try:
            hide_view_node_obj = self.env['hide.view.nodes'].sudo()
            hide_field_obj = self.env['hide.field'].sudo()
            hide_button_obj = self.env['hide.view.nodes']
            field_conditional_obj = self.env['field.conditional.access'].sudo()
            if name_manager.Model._name == 'res.config.settings' and node.tag == 'div' and node.get('string'):
                for setting_tab in hide_button_obj.sudo().search([('access_management_id.company_ids','in',self.env.company.id),('model_id.model','=',name_manager.Model._name),('access_management_id.active','=',True),('access_management_id.user_ids','in',self._uid)]).mapped('page_store_model_nodes_ids'):
                    if node.get('data-key') == setting_tab.attribute_name:
                        node_info['modifiers']['invisible'] = True
                        node.set('invisible', '1')
            if node.tag == 'a':
                if node.text and '\n' not in node.text and 'type' in node.attrib.keys() and node.attrib['type'] and 'name' in node.attrib.keys() and node.attrib['name']:
                    if hide_view_node_obj.search([
                        ('model_id.model','=',name_manager.Model._name),
                        ('access_management_id.active','=',True),
                        ('access_management_id.company_ids','in',self.env.company.id),
                        ('access_management_id.user_ids','in',self._uid),
                        ('link_store_model_nodes_ids.node_option','=','link'),
                        ('link_store_model_nodes_ids.attribute_name','=',node.get('name')),
                        # ('link_store_model_nodes_ids.attribute_string','=',node.text),
                        ('link_store_model_nodes_ids.button_type','=',node.get('type')),
                    ]):
                        node_info['modifiers']['invisible'] = True
                        node.set('invisible', '1')
            
            if node.tag == 'field' or node.tag == 'label' or node.tag == 'div':
                for hide_field in hide_field_obj.search([('access_management_id.company_ids','in',self.env.company.id),('model_id.model','=',name_manager.Model._name),('access_management_id.active','=',True),('access_management_id.user_ids','in',self._uid)]):
                    for field_id in hide_field.field_id:
                        
                        child_field_count = 0
                        hide_child_field_count = 0
                        for field_node in node.getchildren():
                            if field_node.tag == 'field':
                                child_field_count += 1
                            if field_id.name == field_node.get('name') and hide_field.invisible:
                                hide_child_field_count+=1
                        if child_field_count == 1 and hide_child_field_count:
                            node_info['modifiers']['invisible'] = True
                            node.set('invisible', '1')

                        if (node.tag == 'field' and node.get('name') == field_id.name) or (node.tag == 'label' and 'for' in node.attrib.keys() and node.attrib['for'] == field_id.name):

                            if hide_field.external_link:
                                options_dict = {}
                                if 'widget' in node.attrib.keys():
                                    if node.attrib['widget'] == 'product_configurator' or node.attrib['widget'] == 'many2one_avatar_user':
                                        del node.attrib['widget']
                                        
                                if 'options' in node.attrib.keys():
                                    options_dict = ast.literal_eval(node.attrib['options'])
                                    # options_dict.update({"no_edit": True, "no_create": True, "no_open": True})
                                    options_dict.update({"no_open": True})
                                    node.attrib['options'] = str(options_dict)
                                else:
                                    node.attrib['options'] = str({"no_open": True})
                                # node.attrib.update({'can_create': 'false', 'can_write': 'false','no_open':'true'})
                                    
                            if hide_field.create_option:
                                options_dict = {}
                                if 'options' in node.attrib.keys():
                                    options_dict = ast.literal_eval(node.attrib['options'])
                                    options_dict.update({"no_create": True})
                                    node.attrib['options'] = str(options_dict)
                                else:
                                    node.attrib['options'] = str({"no_create": True})

                            if hide_field.edit_option:
                                options_dict = {}
                                if 'options' in node.attrib.keys():
                                    options_dict = ast.literal_eval(node.attrib['options'])
                                    options_dict.update({"no_create_edit": True})
                                    node.attrib['options'] = str(options_dict)
                                else:
                                    node.attrib['options'] = str({"no_create_edit": True})


                            if hide_field.invisible:
                                node_info['modifiers']['invisible'] = True
                                node.set('invisible', '1')
                            if hide_field.readonly:
                                node_info['modifiers']['readonly'] = True
                                node.set('readonly', '1')
                                node.set('force_save', '1')
                            if hide_field.required:
                                node_info['modifiers']['required'] = True
                                node.set('required', '1')

                for field_conditional in field_conditional_obj.search([('access_management_id.company_ids','in',self.env.company.id),('model_id.model','=',name_manager.Model._name),('access_management_id.active','=',True),('access_management_id.user_ids','in',self._uid)]):
                
                    if (node.tag == 'field' and node.get('name') == field_conditional.attrs_field_id.name) or (node.tag == 'label' and 'for' in node.attrib.keys() and node.attrib['for'] == field_conditional.attrs_field_id.name):
                        if field_conditional.apply_attrs and field_conditional.field_attrs:
                            attrs_list=[]
                            final_attrs ={}
                            field_attrs = ast.literal_eval(field_conditional.field_attrs.strip())
                            field_attrs_list = []
                            for attrs_tuple in field_attrs:
                                if isinstance(attrs_tuple, tuple) or isinstance(attrs_tuple, list):
                                    dom_list = list(attrs_tuple)
                                    field_value = dom_list[0]
                                    operator_value = dom_list[1]
                                    value = dom_list[2]
                                    model_obj = self.env[name_manager.Model._name]
                                    field_type = model_obj.fields_get()[field_value]['type']
                                    if field_type in ['many2one', 'many2many', 'one2many']:
                                        field_relation = model_obj.fields_get()[field_value]['relation']
                                        model_string = field_relation
                                        if model_string == 'res.users':
                                            if operator_value in ['in', 'not in']:
                                                if isinstance(value, list) and 0 in value:
                                                    zero_index = value.index(0)
                                                    value[zero_index] = self.env.user.id
                                        if model_string == 'res.company':
                                            if operator_value in ['in', 'not in']:
                                                if isinstance(value, list) and 0 in value:
                                                    zero_index = value.index(0)
                                                    value[zero_index] = self.env.company.id
                                                
                                    field_attrs_list.append(dom_list)

                                else:
                                    field_attrs_list.append(attrs_tuple)
                                
                            if field_attrs_list :
                                field_attrs = field_attrs_list

                            if 'attrs' in node.attrib.keys():
                                default_attrs = ast.literal_eval(node.attrib['attrs'].strip())
                                if default_attrs.get('invisible'):
                                    default_attrs_list = default_attrs.get('invisible')
                                    for attrs in default_attrs_list:
                                        if isinstance(attrs, tuple):
                                            if field_conditional.attrs_type == 'invisible':
                                                attrs_list.append('|')
                                                attrs_list += default_attrs_list + field_attrs
                                            else:
                                                attrs_list.append(attrs)
                                        else:
                                            attrs_list.append(attrs)
                                    final_attrs['invisible'] = attrs_list

                                if default_attrs.get('readonly'):
                                    default_attrs_list = default_attrs.get('readonly')
                                    for attrs in default_attrs_list:
                                        if isinstance(attrs, tuple):
                                            if field_conditional.attrs_type == 'readonly':
                                                attrs_list.append('|')
                                                attrs_list += default_attrs_list + field_attrs
                                            else:
                                                attrs_list.append(attrs)
                                        else:
                                            attrs_list.append(attrs)
                                    final_attrs['readonly'] = attrs_list

                                if default_attrs.get('required'):
                                    default_attrs_list = default_attrs.get('required')
                                    for attrs in default_attrs_list:
                                        if isinstance(attrs, tuple):
                                            if field_conditional.attrs_type == 'required':
                                                attrs_list.append('|')
                                                attrs_list += default_attrs_list + field_attrs
                                            else:
                                                attrs_list.append(attrs)
                                        else:
                                            attrs_list.append(attrs)
                                    final_attrs['required'] = attrs_list

                            else :
                                if field_conditional.attrs_type == 'invisible':
                                    final_attrs['invisible'] = field_attrs
                                
                                if field_conditional.attrs_type == 'readonly':
                                    final_attrs['readonly'] = field_attrs

                                if field_conditional.attrs_type == 'required':
                                    final_attrs['required'] = field_attrs

                            node.attrib['attrs'] = str(final_attrs)

                    if (node.tag == 'field' and node.get('name') == field_conditional.domain_field_id.name) or (node.tag == 'label' and 'for' in node.attrib.keys() and node.attrib['for'] == field_conditional.domain_field_id.name):
                        if field_conditional.apply_field_domain and field_conditional.field_domain:
                            domain = ast.literal_eval(field_conditional.field_domain.strip())
                            field_domain = []
                            model_obj = self.env[name_manager.Model._name]
                            domain_field_type = model_obj.fields_get()[field_conditional.domain_field_id.name]['type']
                            domain_field_type_relation =  model_obj.fields_get()[field_conditional.domain_field_id.name]['relation']
                            domain_field_type_relation_obj = self.env[domain_field_type_relation]
                            for dom in domain:
                                if isinstance(dom, tuple) or isinstance(dom, list):
                                    field_type = domain_field_type_relation_obj.fields_get()[dom[0]]['type']
                                    if field_type in ['many2one', 'many2many', 'one2many']:
                                        dom_list = list(dom)
                                        operator_value = dom_list[1]
                                        value = dom_list[2]
                                        field_relation = domain_field_type_relation_obj.fields_get()[dom_list[0]]['relation']
                                        model_string = field_relation
                                        if model_string == 'res.users':
                                            if operator_value in ['in', 'not in']:
                                                if isinstance(value, list) and 0 in value:
                                                    zero_index = value.index(0)
                                                    value[zero_index] = self.env.user.id
                                        if model_string == 'res.company':
                                            if operator_value in ['in', 'not in']:
                                                if isinstance(value, list) and 0 in value:
                                                    zero_index = value.index(0)
                                                    value[zero_index] = self.env.company.id

                                    field_domain.append(tuple(dom))
                                else :
                                    field_domain.append(dom)
                            if field_domain:
                                if 'domain' not in node.attrib.keys():
                                    node.attrib['domain']=str(field_domain)
                                else :
                                    default_domain = ast.literal_eval(node.attrib['domain'].strip())
                                    default_domain += field_domain
                                    node.attrib['domain'] = str(default_domain)

            if node.tag == 'filter' or node.tag == 'group':
                hide_filter_group_obj = self.env['hide.filters.groups'].sudo().search([('access_management_id.company_ids', 'in', self.env.company.id),
                     ('model_id.model', '=', name_manager.Model._name),('access_management_id.active', '=', True),
                     ('access_management_id.user_ids', 'in', self._uid)])

                for hide_field_obj in hide_filter_group_obj:
                    for hide_filter in hide_field_obj.filters_store_model_nodes_ids.mapped('attribute_name'):
                        if hide_filter == node.get('name',False):
                            node_info['modifiers']['invisible'] = True
                            node.set('invisible', '1')

                    for hide_filter in hide_field_obj.groups_store_model_nodes_ids.mapped('attribute_name'):
                        if hide_filter == node.get('name',False):
                            node_info['modifiers']['invisible'] = True
                            node.set('invisible', '1')

            if node.get('groups'):
                can_see = self.user_has_groups(groups=node.get('groups'))
                if not can_see:
                    node.set('invisible', '1')
                    node_info['modifiers']['invisible'] = True
                    if 'attrs' in node.attrib:
                        del node.attrib['attrs']    # avoid making field visible later
            del node.attrib['groups']
        except Exception:
            pass

ir_ui_view._apply_groups = _apply_groups


    