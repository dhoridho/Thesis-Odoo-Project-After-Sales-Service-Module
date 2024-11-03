# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, _
from odoo.exceptions import UserError

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    group_enable_purchase_multi_product_adv = fields.Boolean(
            "Enable Purchase Multi Product Advance", implied_group='sh_all_in_one_purchase_tools.group_enable_purchase_multi_product_adv')


class PurchaseModel(models.Model):
    _inherit="purchase.order"

    def sh_pmps_adv_btn(self):
        if self:
            for data in self:
                view = data.env.ref(
                    'sh_all_in_one_purchase_tools.sh_pmps_adv_wizard_form_view'
                )
                ori_arch = """
    <form string="Select Products Advance">
                <notebook>
                    <page string="List">
                        <field name="product_ids">
                            <tree create="false" editable='bottom'>
                                <button name="add_to_specific" type="object" string="Add"/>
                                <field name="product_id" readonly="1" />
                                <field name="default_code" readonly="1" />
                                <field name="standard_price" readonly="1" />
                                <field name="uom_po_id" readonly="1" />
                                <field name="qty" />
                            </tree>
                        </field>
                    </page>
                    <page string="Specific">
                        <field name="specific_product_ids">
                            <tree create="false" editable='bottom'>
                                <field name="product_id" readonly="1" />
                                <field name="default_code" readonly="1" />
                                <field name="standard_price" readonly="1" />
                                <field name="uom_po_id" readonly="1" />
                                <field name="qty" />
                            </tree>
                        </field>
                    </page>
                </notebook>
                <footer>
                    <button name="sh_pmps_adv_select_btn" string="Select List" type="object" class="oe_highlight"/>
                    <button name="sh_pmps_adv_select_specific_btn" string="Select Specific" type="object" class="oe_highlight"/>
                    <button string="Cancel" class="oe_link" special="cancel"/>
                </footer>
            </form>

                """

                sh_cid = self.env.user.company_id
                pmps_model_id = self.env[
                    'ir.model'
                    ].sudo().search([
                        ('model', '=', 'pmps.adv.wizard')
                        ], limit=1)
                int_operators = [
                    ('=', '='),
                    ('!=', '!='),
                    ('>', '>'),
                    ('<', '<'),
                    ('>=', '>='),
                    ('<=', '<=')
                    ]
                char_operators = [
                    ('=', '='),
                    ('!=', '!='),
                    ('like', 'like'),
                    ('ilike', 'ilike'),
                    ('=like', '=like'),
                    ('not like', 'not like'),
                    ('not ilike', 'not ilike')
                    ]
                if pmps_model_id and sh_cid:
                    ir_model_fields_obj = self.env['ir.model.fields']
                    str_obj = ori_arch
                    first_str = """<?xml version="1.0"?>
    <form string="Select Products Advance">
                    """

                    if sh_cid.sh_pmps_pro_field_ids:
                        for rec in sh_cid.sh_pmps_pro_field_ids:
                            #add custom selection operators fields here
                            if rec.ttype not in ['boolean', 'many2one', 'selection']:
                                search_opt_field = ir_model_fields_obj.sudo().search([
                                            ('name', '=', 'x_opt_'+ rec.name),
                                            ('model_id', '=', pmps_model_id.id),
                                            ], limit=1)
                                if not search_opt_field:
                                    opt_field_vals = {
                                        'name': 'x_opt_'+rec.name,
                                        'model': 'pmps.adv.wizard',
                                        'field_description': 'x_opt_' + rec.field_description,
                                        'model_id': pmps_model_id.id,
                                        'ttype': 'selection',
                                        }
                                    if rec.ttype in ['integer', 'float']:
                                        opt_field_vals.update({
                                            'selection': str(int_operators)
                                        })
                                    if rec.ttype == 'char':
                                        opt_field_vals.update({
                                            'selection': str(char_operators)
                                        })
                                    ir_model_fields_obj.sudo().create(opt_field_vals)

                            #create duplicate fields from product.product
                            #first search field if not found than create it.
                            search_field = ir_model_fields_obj.sudo().search([
                                        ('name', '=', 'x_'+ rec.name),
                                        ('model_id', '=', pmps_model_id.id),
                                        ], limit = 1)
                            #update selection fields key value pair each time when wizard is load
                            if search_field and search_field.ttype == 'selection':
                                selection_key_value_list = False
                                selection_key_value_list = self.env[
                                    rec.model
                                    ].sudo()._fields[
                                        rec.name
                                        ].selection
                                if selection_key_value_list:
                                    selection_field_dic = {}
                                    selection_field_dic.update({
                                        'selection': str(selection_key_value_list)
                                    })
                                    search_field.sudo().write(selection_field_dic)
                                else:
                                    raise UserError(
                                        _('Key value pair for this selection field not found - '+ search_field.name
                                        ))

                            selection_key_value_list = False
                            #crate new custome field here
                            if not search_field:
                                field_vals = {
                                    'name': 'x_'+rec.name,
                                    'model': 'pmps.adv.wizard',
                                    'field_description': rec.field_description,
                                    'model_id': pmps_model_id.id,
                                    'ttype': rec.ttype,
                                }
                                if rec.relation:
                                    field_vals.update({'relation': rec.relation})
                                if rec.ttype == 'selection':
                                    selection_key_value_list = self.env[
                                        rec.model
                                        ].sudo()._fields[
                                            rec.name
                                            ].selection
                                    if selection_key_value_list:
                                        field_vals.update({
                                            'selection': str(selection_key_value_list)
                                        })
                                    else:
                                        raise UserError(
                                            _('Key value pair for this selection field not found - '+ rec.name
                                            ))
                                ir_model_fields_obj.sudo().create(field_vals)

                    #product attributes code start here
                    #create attributes m2o fields if never exist
                    if sh_cid.sh_pmps_pro_attr_ids:
                        for rec in sh_cid.sh_pmps_pro_attr_ids:
                            search_attr_field = ir_model_fields_obj.sudo().search([
                                ('name', '=', 'x_attr_' + str(rec.id)),
                                ('model_id', '=', pmps_model_id.id),
                                ], limit = 1)
                            if not search_attr_field:
                                attr_field_vals = {
                                    'name': 'x_attr_' + str(rec.id),
                                    'model': 'pmps.adv.wizard',
                                    'field_description': rec.name,
                                    'model_id': pmps_model_id.id,
                                    'ttype': 'many2one',
                                    'relation': 'product.attribute.value'
                                }
                                ir_model_fields_obj.sudo().create(attr_field_vals)

                    no_create_str = """ options="{'no_create': True }" """
                    middle_str = ''
                    if sh_cid.sh_pmps_pro_field_ids:
                        for rec in sh_cid.sh_pmps_pro_field_ids:
                            middle_str += "<div class='row' style='border-bottom:1px solid #ccc; margin:5px 10px;margin: 9px 0px;'>"
                            middle_str += "<div class='col-sm-3 text-right' style='font-weight:bold'> <label for='x_" + rec.name + "'/></div>"
                            if rec.ttype not in ['boolean','many2one','selection']:
                                middle_str += "<div class='col-sm-3'> <field name='x_opt_" + rec.name + "'/></div>"
                            if rec.ttype == 'many2one':
                                middle_str += "<div class='col-sm-3'> <field name='x_" + rec.name + "' "+ ' ' + no_create_str+"/></div>"
                            elif rec.ttype in ['boolean','selection']:
                                middle_str += "<div class='col-sm-3'> <field name='x_" + rec.name + "'/></div>"
                            else:
                                middle_str += "<div class='col-sm-6'> <field name='x_" + rec.name + "'/></div>"
                            middle_str += "</div>"

                    #add prodduct attributes fields in wizard view
                    if sh_cid.sh_pmps_pro_attr_ids:
                        for rec in sh_cid.sh_pmps_pro_attr_ids:
                            domain_str = """ domain="[('attribute_id','=',""" +  str(rec.id) + """)]" """
                            middle_str += "<div class='row' style='border-bottom:1px solid #ccc; margin:5px 10px;margin: 9px 0px;'>"
                            middle_str += "<div class='col-sm-3 text-right' style='font-weight:bold'> <label for='x_attr_" + str(rec.id) + "'/></div>"
                            middle_str += "<div class='col-sm-3'> <field name='x_attr_" + str(rec.id) + "' "+  domain_str +' '+ no_create_str +"/></div>"
                            middle_str += "<div class='col-sm-6'> </div>"
                            middle_str += "</div>"


                    #add the many2many attribute fields here.
                    no_create_str = """ options="{'no_create': True}" """
                    middle_str += "<div class='row' style='border-bottom:1px solid #ccc; margin:5px 10px;margin: 9px 0px;'>"
                    middle_str += "<div class='col-sm-3 text-right' style='font-weight:bold'> <label for='product_attr_ids'/> </div>"
                    middle_str += "<div class='col-sm-6'> <field name='product_attr_ids' widget='many2many_tags'"+' '+ no_create_str +"/> </div>"
                    middle_str += "</div>"

                    #button start here
                    middle_str += "<div class='col-md-12 text-center'>"
                    middle_str += "<button name='filter_products' string='Filter Products' type='object'/>"
                    middle_str += "<button name='reset_filter' string='Reset Filter' type='object'/>"
                    middle_str += "<button name='reset_list' string='Reset List' type='object'/>"
                    middle_str += "<button name='reset_specific' string='Reset Specific' type='object'/>"
                    middle_str += "</div>"
                    last_str = str_obj.split(">",1)[1]
                    final_arch = first_str + middle_str + last_str

                    if view:
                        view.sudo().write({'arch': final_arch})

                context = self.env.context
                return {
                    'name': 'Select Products Advance',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'pmps.adv.wizard',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'context': context,
                    }
