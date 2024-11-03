from odoo import models, SUPERUSER_ID, _
import ast


class ir_ui_view(models.Model):
    _inherit = 'ir.ui.view'

    def _apply_groups(self, node, name_manager, node_info):
        
        try:
            hide_view_node_obj = self.env['hide.view.nodes'].sudo()
            hide_field_obj = self.env['hide.field'].sudo()
            hide_button_obj = self.env['hide.view.nodes']
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
                                    if node.attrib['widget'] == 'product_configurator':
                                        del node.attrib['widget']
                                if 'options' in node.attrib.keys():
                                    options_dict = ast.literal_eval(node.attrib['options'])
                                    options_dict.update({"no_edit": True,"no_create": True,"no_open": True})
                                    node.attrib['options'] = str(options_dict)
                                else:
                                    node.attrib['options'] = str({"no_edit": True,"no_create": True,"no_open": True})
                                node.attrib.update({'can_create': 'false', 'can_write': 'false','no_open':'true'})
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
   

    def _postprocess_tag_button(self, node, name_manager, node_info):
        # Hide Any Button
        postprocessor = getattr(super(ir_ui_view, self), '_postprocess_tag_button', False)
        if postprocessor:
            super(ir_ui_view, self)._postprocess_tag_button(node, name_manager, node_info)

        hide = None
        hide_button_obj = self.env['hide.view.nodes']
        hide_button_ids = hide_button_obj.sudo().search([('access_management_id.company_ids','in',self.env.company.id),('model_id.model','=',name_manager.Model._name),('access_management_id.active','=',True),('access_management_id.user_ids','in',self._uid)])

        # Filtered with same env user and current model
        btn_store_model_nodes_ids = hide_button_ids.mapped('btn_store_model_nodes_ids')
        if btn_store_model_nodes_ids:
            for btn in btn_store_model_nodes_ids:
                if btn.attribute_name == node.get('name'):
                    if node.get('string'):
                        if _(btn.attribute_string) == node.get('string'):
                            hide = [btn]
                            break
                    else:
                        hide = [btn]
                        break
        if hide:
            node.set('invisible', '1')
            if 'attrs' in node.attrib.keys() and node.attrib['attrs']:
                del node.attrib['attrs']
            node_info['modifiers']['invisible'] = True


        return None


    def _postprocess_tag_page(self, node, name_manager, node_info):
        # Hide Any Notebook Page
        postprocessor = getattr(super(ir_ui_view, self), '_postprocess_tag_page', False)
        if postprocessor:
            super(ir_ui_view, self)._postprocess_tag_page(node, name_manager, node_info)

        hide = None
        hide_tab_obj = self.env['hide.view.nodes']
        hide_tab_ids = hide_tab_obj.sudo().search([('access_management_id.company_ids','in',self.env.company.id),('model_id.model','=',name_manager.Model._name),('access_management_id.active','=',True),('access_management_id.user_ids','in',self._uid)])

        # Filtered with same env user and current model
        page_store_model_nodes_ids = hide_tab_ids.mapped('page_store_model_nodes_ids')
        if page_store_model_nodes_ids:
            for tab in page_store_model_nodes_ids:
                if _(tab.attribute_string) == node.get('string'):
                    if node.get('name'):
                        if tab.attribute_name == node.get('name'):
                            hide = [tab]
                            break
                    else:
                        hide = [tab]
                        break    
        if hide:
            node.set('invisible', '1')
            if 'attrs' in node.attrib.keys() and node.attrib['attrs']:
                del node.attrib['attrs']
      
            node_info['modifiers']['invisible'] = True


        return None        
