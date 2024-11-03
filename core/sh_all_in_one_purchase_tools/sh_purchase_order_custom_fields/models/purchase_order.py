# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api, _
import xml.etree.ElementTree as xee
from odoo.exceptions import UserError


class ShCustomModelPurchaseOrder(models.Model):
    _name = 'sh.custom.model.purchase.order'
    _description = 'Custom Model purchase Order'
    _inherit = 'ir.model.fields'

    @api.model
    def get_field_types(self):
        field_list = sorted((key, key) for key in fields.MetaField.by_type)
        field_list.remove(('one2many', 'one2many'))
        field_list.remove(('reference', 'reference'))
        field_list.remove(('monetary', 'monetary'))
        field_list.insert(len(field_list), ('color', 'color'))
        field_list.insert(len(field_list), ('signature', 'signature'))
        field_list.remove(('many2one_reference', 'many2one_reference'))
        return field_list

    def get_child_views(self, view, field_list):
        child_view_ids = self.env['ir.ui.view'].search(
            [('inherit_id', '=', view.id)])
        if child_view_ids:
            for child_view in child_view_ids:
                data1 = str(child_view.arch_base)
                doc = xee.fromstring(data1)
                for fields in doc.findall('.//field'):
                    field_list.append(fields.attrib['name'])
                    self.get_child_views(child_view, field_list)

    def set_domain(self):
        view_id = self.env.ref('purchase.purchase_order_form')
        data1 = str(view_id.arch_base)
        doc = xee.fromstring(data1)
        field_list = []

        for tag in doc.findall('.//field'):
            field_list.append(tag.attrib['name'])

        self.get_child_views(view_id, field_list)
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'purchase.order')])
        return [('model_id', '=', model_id.id), ('name', 'in', field_list)]

    def _set_default(self):
        model_id = self.env['ir.model'].sudo().search(
            [('model', '=', 'purchase.order')])
        if model_id:
            return model_id.id
        else:
            return

    def get_child_field_view(self, view_id):

        child_view_ids = self.env['ir.ui.view'].search(
            [('inherit_id', '=', view_id.id)])
        if child_view_ids:
            for child_view in child_view_ids:
                data1 = str(child_view.arch_base)
                doc = xee.fromstring(data1)
                for tag in doc.findall('.//field[@name=\'%s\']' % (self.sh_position_field.name)):
                    self.inherit_view_obj = child_view.id
                self.get_child_field_view(child_view)

    @api.onchange('sh_position_field')
    def onchage_sh_position_field(self):
        if self.sh_position_field:
            view_id = self.env.ref('purchase.purchase_order_form')
            data1 = str(view_id.arch_base)
            doc = xee.fromstring(data1)
            for tag in doc.findall('.//field[@name=\'%s\']' % (self.sh_position_field.name)):
                self.inherit_view_obj = view_id.id
            self.get_child_field_view(view_id)

    def unlink(self):

        if self:
            model_fields = []
            for rec in self:
                if rec.ir_ui_view_obj:
                    rec.ir_ui_view_obj.unlink()

                model_fields.append(rec.ir_model_fields_obj)

        res = super(ShCustomModelPurchaseOrder, self).unlink()

        if model_fields:
            for rec in model_fields:
                rec.unlink()
        return res

    @api.model
    def create(self, vals):
        if vals.get('field_type'):
            if vals.get('field_type') == 'color':
                vals.update({'ttype': 'char'})
            elif vals.get('field_type') == 'signature':
                vals.update({'ttype': 'binary'})
            elif vals.get('field_type') == 'many2one':
                vals.update({'on_delete':'cascade', 'ttype': vals.get('field_type')})    
            else:
                vals.update({'ttype': vals.get('field_type')})
        return super(ShCustomModelPurchaseOrder, self).create(vals)

    def write(self, vals):
        if vals.get('field_type'):
            if vals.get('field_type') == 'color':
                vals.update({'ttype': 'char'})
            elif vals.get('field_type') == 'signature':
                vals.update({'ttype': 'binary'})
            else:
                vals.update({'ttype': vals.get('field_type')})
        res = super(ShCustomModelPurchaseOrder, self).write(vals)
        if not self.tab_list and not self.sh_position_field:
            raise UserError(_("Please Select Tab or Field !"))

        if self.sh_position_field:
            if not self.sh_position:
                raise UserError(_("Please Select Position !"))
        if vals.get('sh_selection_ids'):
            field_selection_obj = self.env['ir.model.fields.selection']
            field_selection_data = field_selection_obj.search(
                [('field_id', '=', self.ir_model_fields_obj.id)])
            if field_selection_data:
                field_selection_data.unlink()
            for selection_id in self.sh_selection_ids:
                field_selection_obj.create({'field_id': self.ir_model_fields_obj.id,
                                            'value': selection_id.value,
                                            'name': selection_id.name,
                                            'sequence': selection_id.sequence})

        groups_obj = self.env['res.groups'].search([])
        grp_str = ''
        cnt = 0

        for res_grp in groups_obj:

            for fld_grp in self.groups:
                grp = fld_grp.get_external_id()

                for k, v in grp.items():
                    if res_grp.id == k:

                        if cnt == 0:
                            grp_str += v
                        else:
                            grp_str += ',' + str(v)

                        cnt += 1

        if self.ir_model_fields_obj:  # update field  if already created
            vals = {'name': self.name,
                    'field_description': self.field_description,
                    'model_id': self.model_id.id,
                    'help': self.field_help,
                    'ttype': self.field_type,
                    'relation': self.ref_model_id.model,
                    'required': self.required,
                    'copied': self.copied,
                    'domain': self.task_domain,
                    }
            if self.field_type == 'color':
                vals.update({'ttype': 'char'})
            if self.field_type == 'signature':
                vals.update({'ttype': 'binary'})
            if self.tracking_visibility:
                vals.update({'tracking': 100})
            self.ir_model_fields_obj.write(vals)

        group_str_field_arch_base = _('<?xml version="1.0"?>'
                                      '<data>'
                                      '<field name="%s" position="%s">'
                                      '<field name="%s" groups="%s" widget="%s"/>'
                                      '</field>'
                                      '</data>')

        group_str_tab_arch_base = _('<?xml version="1.0"?>'
                                    '<data>'
                                    '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                    '<group><field name="%s" groups="%s" widget="%s"/></group>'
                                    '</xpath>'
                                    '</data>')

        no_group_str_field_arch_base = _('<?xml version="1.0"?>'
                                         '<data>'
                                         '<field name="%s" position="%s">'
                                         '<field name="%s" widget="%s"/>'
                                         '</field>'
                                         '</data>')

        no_group_str_tab_arch_base = _('<?xml version="1.0"?>'
                                       '<data>'
                                       '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                       '<group><field name="%s" widget="%s"/></group>'
                                       '</xpath>'
                                       '</data>')

        if self.field_type == 'selection' and self.widget_selctn_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_selctn_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_selctn_selection)

            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_selctn_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_selctn_selection)

        elif self.field_type == 'char' and self.widget_char_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_char_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_char_selection)

            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_char_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_char_selection)
        elif self.field_type == 'float' and self.widget_float_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_float_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_float_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_float_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_float_selection)

        elif self.field_type == 'text' and self.widget_text_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_text_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_text_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_text_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_text_selection)

        elif self.field_type == 'binary' and self.widget_binary_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_binary_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_binary_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_binary_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_binary_selection)

        elif self.field_type == 'many2many' and self.widget_m2m_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_m2m_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_m2m_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_m2m_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_m2m_selection)

        elif self.field_type == 'many2one' and self.widget_m2o_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_m2o_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_m2o_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_m2o_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_m2o_selection)

        elif self.field_type == 'color':
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, 'color')
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, 'color')
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, 'color')
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, 'color')
        elif self.field_type == 'signature':
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, 'signature')
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, 'signature')
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, 'signature')
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, 'signature')

        else:  # Other Field Types  or  Without Widget

            if grp_str:
                if self.sh_position_field:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<field name="%s" position="%s">'
                                  '<field name="%s" groups="%s"/>'
                                  '</field>'
                                  '</data>') % (self.sh_position_field.name, self.sh_position, self.name, grp_str)
                else:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<xpath expr="//page[@name=\'%s\']/group" position="inside">'
                                  '<group><field name="%s" groups="%s"/></group>'
                                  '</xpath>'
                                  '</data>') % (self.tab_list, self.name, grp_str)

            else:
                if self.sh_position_field:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<field name="%s" position="%s">'
                                  '<field name="%s"/>'
                                  '</field>'
                                  '</data>') % (self.sh_position_field.name, self.sh_position, self.name)
                else:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<xpath expr="//page[@name=\'%s\']/group" position="inside">'
                                  '<group><field name="%s"/></group>'
                                  '</xpath>'
                                  '</data>') % (self.tab_list, self.name)

        inherit_id = self.env.ref('purchase.purchase_order_form')

        if self.ir_ui_view_obj:  # update view if exist
            self.ir_ui_view_obj.write({'name': 'purchase.order.dynamic.fields',
                                       'type': 'form',
                                       'model': 'purchase.order',
                                       'mode': 'extension',
                                       'inherit_id': inherit_id.id,
                                       'arch_base': arch_base,
                                       'active': True
                                       })
        return res

    def create_fields(self):
        if not self.tab_list and not self.sh_position_field:
            raise UserError(_("Please Select Tab or Field !"))
        groups_obj = self.env['res.groups'].search([])
        grp_str = ''
        cnt = 0
        pg_rld = True
        if self.sh_position_field:
            if not self.sh_position:
                raise UserError(_("Please Select Position !"))
        for res_grp in groups_obj:
            for fld_grp in self.groups:

                grp = fld_grp.get_external_id()
                for k, v in grp.items():

                    if res_grp.id == k:
                        if cnt == 0:
                            grp_str += v
                        else:
                            grp_str += ',' + str(v)

                        cnt += 1

        if self.model_id:
            if not self.ir_model_fields_obj:
                vals = {'name': self.name,
                        'field_description': self.field_description,
                        'model_id': self.model_id.id,
                        'help': self.field_help,
                        'ttype': self.field_type,
                        'relation': self.ref_model_id.model,
                        'required': self.required,
                        'copied': self.copied,
                        'domain': self.task_domain,
                        }
                if self.field_type == 'color':
                    vals.update({'ttype': 'char'})
                if self.field_type == 'signature':
                    vals.update({'ttype': 'binary'})
                if self.tracking_visibility:
                    vals.update({'tracking': 100})
                ir_mdl_flds_obj = self.env['ir.model.fields'].sudo().create(
                    vals)

                # Need to create record for ir model field selection----------
                if self.sh_selection_ids:
                    field_selection_obj = self.env['ir.model.fields.selection']
                    for selection_id in self.sh_selection_ids:
                        field_selection_obj.create({'field_id': ir_mdl_flds_obj.id,
                                                    'value': selection_id.value,
                                                    'name': selection_id.name,
                                                    'sequence': selection_id.sequence})

        if ir_mdl_flds_obj:
            self.ir_model_fields_obj = ir_mdl_flds_obj.id

        if self.inherit_view_obj:
            inherit_id = self.inherit_view_obj
        else:
            inherit_id = self.env.ref('purchase.purchase_order_form')

        group_str_field_arch_base = _('<?xml version="1.0"?>'
                                      '<data>'
                                      '<field name="%s" position="%s">'
                                      '<field name="%s" groups="%s" widget="%s"/>'
                                      '</field>'
                                      '</data>')

        group_str_tab_arch_base = _('<?xml version="1.0"?>'
                                    '<data>'
                                    '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                    '<group><field name="%s" groups="%s" widget="%s"/></group>'
                                    '</xpath>'
                                    '</data>')

        no_group_str_field_arch_base = _('<?xml version="1.0"?>'
                                         '<data>'
                                         '<field name="%s" position="%s">'
                                         '<field name="%s" widget="%s"/>'
                                         '</field>'
                                         '</data>')

        no_group_str_tab_arch_base = _('<?xml version="1.0"?>'
                                       '<data>'
                                       '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                       '<group><field name="%s" widget="%s"/></group>'
                                       '</xpath>'
                                       '</data>')

        if self.field_type == 'selection' and self.widget_selctn_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_selctn_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_selctn_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_selctn_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_selctn_selection)

        elif self.field_type == 'char' and self.widget_char_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_char_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_char_selection)

            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_char_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_char_selection)

        elif self.field_type == 'float' and self.widget_float_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_float_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_float_selection)

            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_float_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_float_selection)

        elif self.field_type == 'text' and self.widget_text_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_text_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_text_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_text_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_text_selection)

        elif self.field_type == 'binary' and self.widget_binary_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_binary_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_binary_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_binary_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_binary_selection)

        elif self.field_type == 'many2many' and self.widget_m2m_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_m2m_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_m2m_selection)
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_m2m_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_m2m_selection)

        elif self.field_type == 'many2one' and self.widget_m2o_selection:
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, self.widget_m2o_selection)
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, self.widget_m2o_selection)

            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, self.widget_m2o_selection)
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, self.widget_m2o_selection)

        elif self.field_type == 'color':
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, 'color')
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, 'color')
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, 'color')
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, 'color')
        elif self.field_type == 'signature':
            if grp_str:
                if self.sh_position_field:
                    arch_base = group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, grp_str, 'signature')
                else:
                    arch_base = group_str_tab_arch_base % (
                        self.tab_list, self.name, grp_str, 'signature')
            else:
                if self.sh_position_field:
                    arch_base = no_group_str_field_arch_base % (
                        self.sh_position_field.name, self.sh_position, self.name, 'signature')
                else:
                    arch_base = no_group_str_tab_arch_base % (
                        self.tab_list, self.name, 'signature')
        else:  # Other Field Types
            if grp_str:
                if self.sh_position_field:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<field name="%s" position="%s">'
                                  '<field name="%s" groups="%s"/>'
                                  '</field>'
                                  '</data>') % (self.sh_position_field.name, self.sh_position, self.name, grp_str)
                else:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                  '<group><field name="%s" groups="%s" /></group>'
                                  '</xpath>'
                                  '</data>') % (self.tab_list, self.name, grp_str)
            else:
                if self.sh_position_field:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<field name="%s" position="%s">'
                                  '<field name="%s"/>'
                                  '</field>'
                                  '</data>') % (self.sh_position_field.name, self.sh_position, self.name)
                else:
                    arch_base = _('<?xml version="1.0"?>'
                                  '<data>'
                                  '<xpath expr="//form/sheet/notebook/page[@name=\'%s\']/group" position="inside">'
                                  '<group><field name="%s"/></group>'
                                  '</xpath>'
                                  '</data>') % (self.tab_list, self.name)

        irui_vew_obj = self.env['ir.ui.view'].create({'name': 'purchase.order.dynamic.fields',
                                                      'type': 'form',
                                                      'model': 'purchase.order',
                                                      'mode': 'extension',
                                                      'inherit_id': inherit_id.id,
                                                      'arch_base': arch_base,
                                                      'active': True})

        if irui_vew_obj:
            self.ir_ui_view_obj = irui_vew_obj.id

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.onchange('widget_m2m_selection')
    def onchange_widget(self):
        if self.field_type == 'many2many':
            if self.widget_m2m_selection == 'many2many_binary':
                attachment_id = self.env['ir.model'].search(
                    [('name', '=', 'Attachment')])
                self.ref_model_id = attachment_id.id

### Fields Declaration
    def get_tab_list(self):
        view_id = self.env.ref('purchase.purchase_order_form')
        view_ids = self.env['ir.ui.view'].search(
            [('inherit_id', '=', view_id.id)])

        data1 = str(view_id.arch_base)
        doc = xee.fromstring(data1)
        tab_list = []
        if view_ids:
            for view in view_ids:
                data1 = str(view.arch_base)
                doc = xee.fromstring(data1)
                for tag in doc.findall('.//page'):
                    if 'name' in tag.attrib and 'string' in tag.attrib:
                        tab_list.insert(
                            len(tab_list), (tag.attrib['name'], tag.attrib['string']))
        return tab_list

    name = fields.Char("Technical Field Name")
    field_help = fields.Text("Help")

    sh_position_field = fields.Many2one(
        'ir.model.fields', string='Position Field', domain=set_domain)
    sh_position = fields.Selection(
        [('before', 'Before'), ('after', 'After')], string='Position')

    model_id = fields.Many2one('ir.model', string='Model', required=True, index=True, ondelete='cascade',
                               help="The model this field belongs to", default=_set_default)

    ref_model_id = fields.Many2one('ir.model', string='Model', index=True)

    widget_m2o_selection = fields.Selection(
        [('selection', 'selection')], string="Widget")
    widget_m2m_selection = fields.Selection([('many2many_tags', 'Tags'), (
        'many2many_checkboxes', 'Checkboxes'), ('many2many_binary', 'Binary')], string="Widget")

    widget_selctn_selection = fields.Selection(
        [('radio', 'radio'), ('priority', 'priority')], string="Widget")
    widget_binary_selection = fields.Selection(
        [('image', 'image')], string="Widget")
    widget_char_selection = fields.Selection(
        [('email', 'email'), ('phone', 'phone'), ('url', 'url')], string="Widget")

    widget_float_selection = fields.Selection(
        [('float_time', 'Float')], string="Widget")
    widget_text_selection = fields.Selection(
        [('html', 'Html')], string="Widget")

    ir_model_fields_obj = fields.Many2one(
        'ir.model.fields', 'Models Fields Saved Object')
    ir_ui_view_obj = fields.Many2one('ir.ui.view', 'UI View Saved Object')
    inherit_view_obj = fields.Many2one(
        'ir.ui.view', 'Inherited UI View Saved Object')
    task_domain = fields.Char("Domain", default=[])
    task_model_name = fields.Char(
        related='ref_model_id.model', string='Task Model Name', readonly=True, related_sudo=True)
    field_type = fields.Selection(
        selection=get_field_types, string='Field Type', required=True)
    tracking_visibility = fields.Boolean(
        string="Tracking",
        help="If set every modification done to this field is tracked in the chatter. Value is used to order tracking values.")
    groups = fields.Many2many(
        'res.groups', 'sh_custom_group_purchase_order_rel', 'field_id', 'group_id')  # Added new field

    sh_selection_ids = fields.One2many(
        "sh.model.fields.purchase.order.selection", "sh_field_po_id", string="Selection Options", copy=True)
    tab_list = fields.Selection(selection=get_tab_list, string="Tab List")
    position_selection = fields.Selection(
        [('fields', 'Field'), ('tab', 'Tab')], string="Position Based on", default='fields')


class FieldSelection(models.Model):
    _name = 'sh.model.fields.purchase.order.selection'
    _description = 'Field Selection'

    sh_field_po_id = fields.Many2one(
        'sh.custom.model.purchase.order', string="SH Custom Task")
    value = fields.Char(required=True)
    name = fields.Char(translate=True, required=True)
    sequence = fields.Integer(default=1000)
