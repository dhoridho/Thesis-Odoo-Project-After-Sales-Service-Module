from odoo import models, fields, api, _
from odoo.addons.base.models.ir_ui_view import transfer_field_to_modifiers
from odoo.tools.view_validation import get_dict_asts, get_domain_identifiers
from odoo.tools import safe_eval


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def _postprocess_tag_field(self, node, name_manager, node_info):
        if node.get('name'):
            attrs = {'id': node.get('id'), 'select': node.get('select')}
            field = name_manager.Model._fields.get(node.get('name'))
            if field:
                # apply groups (no tested)
                if field.groups and not self.user_has_groups(groups=field.groups):
                    node.set('invisible', '1')
                node_info['editable'] = node_info['editable'] and field.is_editable() and (
                    node.get('readonly') not in ('1', 'True')
                    or get_dict_asts(node.get('attrs') or "{}")
                )
                if name_manager.validate:
                    name_manager.must_have_fields(
                        self._get_field_domain_variables(node, field, node_info['editable'])
                    )
                views = {}
                for child in node:
                    if child.tag in ('form', 'tree', 'graph', 'kanban', 'calendar'):
                        node.remove(child)
                        xarch, sub_name_manager = self.with_context(
                            base_model_name=name_manager.Model._name,
                        )._postprocess_view(
                            child, field.comodel_name, name_manager.validate,
                            editable=node_info['editable'],
                        )
                        name_manager.must_have_fields(sub_name_manager.mandatory_parent_fields)
                        views[child.tag] = {
                            'arch': xarch,
                            'fields': sub_name_manager.available_fields,
                        }
                attrs['views'] = views
                if field.comodel_name in self.env:
                    Comodel = self.env[field.comodel_name].sudo(False)
                    node_info['attr_model'] = Comodel
                    if field.type in ('many2one', 'many2many'):
                        can_create = Comodel.check_access_rights('create', raise_exception=False)
                        can_write = Comodel.check_access_rights('write', raise_exception=False)
                        node.set('can_create', 'true' if can_create else 'false')
                        node.set('can_write', 'true' if can_write else 'false')

            name_manager.has_field(node.get('name'), attrs)
            field = name_manager.fields_get.get(node.get('name'))
            if field:
                transfer_field_to_modifiers(field, node_info['modifiers'])

    def _postprocess_tag_label(self, node, name_manager, node_info):
        if node.get('for'):
            field = name_manager.Model._fields.get(node.get('for'))
            if field and field.groups and not self.user_has_groups(groups=field.groups):
                node.set('invisible', '1')

    def _postprocess_tag_search(self, node, name_manager, node_info):
        super(IrUiView, self)._postprocess_tag_search(node, name_manager, node_info)
        self._postprocess_tag_search_restricted_fields(node, name_manager, node_info)

    def _postprocess_tag_search_restricted_fields(self, node, name_manager, node_info):
        def _is_restricted(field_name):
            field = name_manager.Model._fields.get(field_name)
            return field.groups and not self.user_has_groups(groups=field.groups)

        def _filter(o):
            if o.tag == 'field':
                if _is_restricted(o.get('name')):
                    o.set('invisible', '1')
            
            elif o.tag == 'filter':
                date = o.get('date')
                if date and _is_restricted(date):
                    o.set('invisible', '1')
                    return

                domain = o.get('domain')
                if domain:
                    try:
                        (field_names, var_names) = get_domain_identifiers(domain)
                    except ValueError:
                        msg = _(
                            'Invalid domain format while checking %(attribute)s in %(value)s',
                            attribute=expr, value=key,
                        )
                        self.handle_view_error(msg)

                    is_valid = True
                    for name_seq in field_names:
                        if isinstance(name_seq, str):
                            if _is_restricted(name_seq.split('.')[0]):
                                is_valid = False
                                break
                    if not is_valid:
                        o.set('invisible', '1')
                        return
                
                context = safe_eval.safe_eval(o.get('context') or '{}', {'context': self._context})
                if context and 'group_by' in context and isinstance(context['group_by'], str):
                    if _is_restricted(context['group_by'].split(':')[0]):
                        o.set('invisible', '1')

        def _inspect(parent):
            for child in parent:
                if child.tag == 'separator':
                    continue
                elif child.tag == 'group':
                    _inspect(child)
                else:
                    _filter(child)

        _inspect(node)
