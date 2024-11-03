# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
from odoo import tools
from pytz import timezone
import math
from lxml import etree

dic = {
    'to_19': ('Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve',
              'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'),
    'tens': ('Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'),
    'denom': ('', 'Thousand', 'Million', 'Billion', 'Trillion', 'Quadrillion', 'Quintillion'),
    'to_19_id': (
        'Nol', 'Satu', 'Dua', 'Tiga', 'Empat', 'Lima', 'Enam', 'Tujuh', 'Delapan', 'Sembilan', 'Sepuluh', 'Sebelas',
        'Dua Belas', 'Tiga Belas', 'Empat Belas', 'Lima Belas', 'Enam Belas', 'Tujuh Belas', 'Delapan Belas',
        'Sembilan Belas'),
    'tens_id': ('Dua Puluh', 'Tiga Puluh', 'Empat Puluh', 'Lima Puluh', 'Enam Puluh', 'Tujuh Puluh', 'Delapan Puluh',
                'Sembilan Puluh'),
    'denom_id': ('', 'Ribu', 'Juta', 'Miliar', 'Triliun', 'Biliun')
}

ESTIMATES_DICT = {
    'material_estimation_ids': 'product_id',
    'labour_estimation_ids': 'product_id',
    'subcon_estimation_ids': 'variable',
    'overhead_estimation_ids': 'product_id',
    'equipment_estimation_ids': 'product_id',
    'internal_asset_ids': 'asset_id'
}

def _convert_nn(val, bhs):
    tens = dic['tens_id']
    to_19 = dic['to_19_id']
    if bhs == 'en':
        tens = dic['tens']
        to_19 = dic['to_19']
    if val < 20 and val >= 0:
        return to_19[val]
    elif val < 0:
        minus_val = abs(val)
        return '- ' + english_number(minus_val, bhs)
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens)):
        if dval + 10 > val:
            if val % 10:
                return dcap + ' ' + to_19[val % 10]
            return dcap


def _convert_nnn(val, bhs):
    word = ''
    rat = ' Ratus'
    to_19 = dic['to_19_id']
    if bhs == 'en':
        rat = ' Hundred'
        to_19 = dic['to_19']
    (mod, rem) = (val % 100, val // 100)
    if rem == 1:
        if bhs == 'id':
            word = 'Seratus'
        else:
            word = 'One Hundred'
        if mod > 0:
            word = word + ' '
    elif rem > 1:
        word = to_19[rem] + rat
        if mod > 0:
            word = word + ' '
    if mod > 0:
        word = word + _convert_nn(mod, bhs)
    return word


def english_number(val, bhs):
    denom = dic['denom_id']
    if bhs == 'en':
        denom = dic['denom']
    if val < 100:
        return _convert_nn(val, bhs)
    if val < 1000:
        return _convert_nnn(val, bhs)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            ret = _convert_nnn(l, bhs) + ' ' + denom[didx]
            if r > 0:
                ret = ret + ' ' + english_number(r, bhs)
            if bhs == 'id':
                if val < 2000:
                    ret = ret.replace("Satu Ribu", "Seribu")
            return ret


def cur_name(cur):
    if cur == "IDR":
        cur = "IDR"
    if cur == "USD":
        return "Dollars"
    elif cur == "AUD":
        return "Dollars"
    elif cur == "IDR":
        return "Rupiah"
    elif cur == "JPY":
        return "Yen"
    elif cur == "SGD":
        return "Dollars"
    elif cur == "EUR":
        return "Euro"
    else:
        return cur


def process_words(number, currency, bhs):
    number = '%.2f' % number
    units_name = ' ' + cur_name(currency) + ' '
    lis = str(number).split('.')
    start_word = english_number(int(lis[0]), bhs)
    end_word = english_number(int(lis[1]), bhs)
    cents_number = int(lis[1])
    cents_name = (cents_number > 1) and 'Sen' or 'sen'

    final_result_sen = start_word + units_name + end_word + ' ' + cents_name

    final_result = start_word + units_name
    if end_word == 'Nol' or end_word == 'Zero':
        final_result = final_result
    else:
        final_result = final_result_sen

    return final_result[:1].upper() + final_result[1:]


def get_unique_list(data):
    unique_list = []

    # traverse for all elements
    for x in data:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)

    return unique_list


class JobEstimate(models.Model):
    _name = 'job.estimate'
    _inherit = ['job.estimate', 'portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "BOQ"
    _rec_name = "name"
    _order = 'id DESC'
    _check_company_auto = True

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group(
                'sales_team.group_sale_salesman_all_leads'):
            domain.append(('project_id.id', 'in', self.env.user.project_ids.ids))
            domain.append(('create_uid', '=', self.env.user.id))
        elif self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group(
                'sales_team.group_sale_manager'):
            domain.append(('project_id.id', 'in', self.env.user.project_ids.ids))

        return super(JobEstimate, self).search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group(
                'sales_team.group_sale_salesman_all_leads'):
            domain.append(('project_id.id', 'in', self.env.user.project_ids.ids))
            domain.append(('create_uid', '=', self.env.user.id))
        elif self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group(
                'sales_team.group_sale_manager'):
            domain.append(('project_id.id', 'in', self.env.user.project_ids.ids))

        return super(JobEstimate, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby,
                                                   lazy=lazy)

    def copy(self, default=None):
        if default is None:
            default = {}
        # Workaround for action_boq_revision, it somehow needs to be False
        # Add context conditional if this causes any conflict
        default.update({
            'project_scope_ids': False,
            'section_ids': False,
            'variable_ids': False,
            'quotation_id': False,
        })
        return super(JobEstimate, self).copy(default)

    def print_out(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Options',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'job.estimate.report',
            'context': {'job_estimate_data': self.id,
                        'default_job_estimate_id': self.id
                        },
        }

        # Remove submenu report button

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(JobEstimate, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu
        )
        if res.get('toolbar', False) and res.get('toolbar').get('print', False):
            reports = res.get('toolbar').get('print')
            for report in reports:
                res['toolbar']['print'].remove(report)

        root = etree.fromstring(res['arch'])
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group(
                'sales_team.group_sale_manager'):
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    report_project_scope_id = fields.One2many(string='Report Project Scope', comodel_name='project.scope.line',
                                              compute='_compute_report_project_scope_id')
    report_contract_category = fields.Char(string='Report Contract Category',
                                           compute='_compute_report_contract_category')

    warehouse_address = fields.Many2one('stock.warehouse', string='Warehouse')
    lead_id = fields.Many2one('crm.lead', string='Opportunity')

    @api.depends('report_contract_category')
    def _compute_report_contract_category(self):
        if self.contract_category == 'main':
            self.report_contract_category = "Main Contract"
        else:
            self.report_contract_category = "Variation Order"

    @api.depends('report_project_scope_id')
    def _compute_report_project_scope_id(self):
        temp_scope_list = list()
        for temp in self.section_ids.project_scope:
            temp_scope_list.append(temp.id)
        report_scope_list_id = get_unique_list(temp_scope_list)

        temp_report_scope = list()
        for scope in report_scope_list_id:
            temp_report_scope.append(self.env['section.estimate'].search([('project_scope', '=', scope)]))

        for scope in temp_report_scope:
            self.report_project_scope_id += scope.project_scope

    def check_scope_labour_estimation(self, data):
        if data.labour_estimation_ids:
            for labour in data.labour_estimation_ids:
                if not labour.project_scope.name:
                    return False
        return True

    def check_scope_internal_asset(self, data):
        if data.internal_asset_ids:
            for internal in data.internal_asset_ids:
                if not internal.project_scope.name:
                    return False
        return True

    def check_scope_equipment_lease(self, data):
        if data.equipment_estimation_ids:
            for equipment in data.equipment_estimation_ids:
                if not equipment.project_scope.name:
                    return False
        return True

    def quotation_button(self):
        self.ensure_one()
        return {
            'name': 'Quotation',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'sale.order.const',
            'domain': [('job_references', '=', self.id)],
        }

    def _get_quotation_count(self):
        for sale in self:
            if sale:
                try:
                    sale_ids = self.env['sale.order.const'].search([('job_references', 'in', sale.id), (
                        'state', 'not in', ['reject', 'over_limit_reject', 'cancel'])])
                    sale.internal_quotation_count = len(sale_ids)

                except:
                    sale.internal_quotation_count = 0
        return True

    def reset_draft(self):
        res = self.write({
            'state': 'draft',
            'state_new': 'draft'
        })
        return res

    def approve_job_estimate(self):
        res = self.write({
            'state': 'approved',
            'state_new': 'approved'
        })
        return res

    def reject_job_estimate(self):
        res = self.write({
            'state': 'rejected',
            'state_new': 'rejected',
            'state_1': 'rejected'
        })
        return res

    def action_quotation_send(self):
        self.ensure_one()
        self.write({
            'estimation_sent': True
        })
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = \
                ir_model_data.get_object_reference('bi_job_cost_estimate_customer', 'job_estimate_email_template')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        ctx = {
            'default_model': 'job.estimate',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        }
        return {
            'name': 'Compose Email',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


    def create_quotation(self):
        if self.contract_category == 'main':
            # main_contract = self.env['sale.order.const'].search(
            #     [('project_id', '=', self.project_id.id), ('contract_category', '=', 'main'),
            #      ('state', 'in', ['sale', 'done'])], limit=1)
            # convert above code to query
            self.env.cr.execute(
                "SELECT id FROM sale_order_const WHERE project_id = %s AND contract_category = 'main' AND state IN ('sale', 'done') LIMIT 1",
                (self.project_id.id,)
            )
            main_contract = self.env.cr.fetchone()
            # quotation = self.env['sale.order.const'].search(
            #     [('project_id', '=', self.project_id.id), ('contract_category', '=', 'main'),
            #      ('state', 'not in', ['reject', 'over_limit_reject', 'sale', 'done', 'cancel', 'block'])])
            # convert above code to query
            self.env.cr.execute(
                "SELECT id FROM sale_order_const WHERE project_id = %s AND contract_category = 'main' AND state NOT IN ('reject', 'over_limit_reject', 'sale', 'done', 'cancel', 'block')",
                (self.project_id.id,)
            )
            quotation = self.env.cr.fetchone()
            context = {
                'default_job_estimate_id': self.id,
                'default_customer_id': self.partner_id.id,
                'default_project_id': self.project_id.id,
                'default_branch_id': self.branch_id.id,
            }

            if main_contract:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Change to Variation Order',
                    'res_model': 'job.estimate.variation.const',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }
            elif not main_contract and quotation:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Create Quotation',
                    'res_model': 'job.estimate.existing.quotation.const',
                    'context': context,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }

            elif not main_contract and not quotation:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Create Quotation',
                    'res_model': 'job.estimate.existing.quotation.const',
                    'context': context,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }

    def approve_new_job_estimate(self):
        for rec in self:
            rec.approve_job_estimate()

    def create_variation_order(self):
        pass

    def action_cancel(self):
        if self.quotation_id:
            for sale in self.quotation_id:
                if sale.state in ('sale', 'done'):
                    raise ValidationError(
                        _('You can not cancel this BOQ because contract (%s) for this BOQ has been confirmed.' % (
                        (sale.name))))

            return {
                'type': 'ir.actions.act_window',
                'name': 'Cancel Confirmation',
                'res_model': 'job.estimate.cancel.const',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            res = self.write({
                'state': 'cancel',
                'state_new': 'cancel',
                'sale_state': 'draft',
                'is_cancelled': True
            })
            return res

    @api.onchange('project_scope_ids')
    def _onchange_project_scope(self):
        """
        If changed scope doesn't exist in any estimate tab, then delete the lines
        This method has two approach:
        1. If the record is saved to database, then use _origin
        2. If the record is new, then use id
        """
        for rec in self:
            changed_scope = list()
            scope_list = list()
            if len(rec.project_scope_ids) > 0 or len(rec._origin.section_ids._origin) > 0:
                for scope in rec.project_scope_ids:
                    # If BOQ record saved to database, use origin
                    # If new, then use id
                    scope_list.append(scope.project_scope.id)
                    if scope._origin.project_scope._origin.id:
                        if scope.project_scope.id != scope._origin.project_scope._origin.id:
                            changed_scope.append(scope._origin.project_scope._origin.id)
                    else:
                        changed_scope.append(scope.project_scope.id)
            if len(rec.section_ids) > 0:
                for section in rec.section_ids:
                    if section.project_scope.id in changed_scope:
                        rec.section_ids = [(2, section._origin.id, 0)]
                    elif section.project_scope.id not in scope_list:
                        rec.section_ids = [(2, section.id, 0)]
            if len(rec.variable_ids) > 0:
                for variable in rec.variable_ids._origin:
                    if variable.project_scope.id in changed_scope:
                        rec.variable_ids = [(2, variable._origin.id, 0)]
                    elif variable.project_scope.id not in scope_list:
                        rec.variable_ids = [(2, variable.id, 0)]

    @api.onchange('section_ids')
    def _onchange_section(self):
        """
        If changed section doesn't exist in any estimate tab, then delete the lines
        This method has two approach:
        1. If the record is saved to database, then use _origin
        2. If the record is new, then use id
        """
        for rec in self:
            changed_section = list()
            section_list = list()
            if len(rec.section_ids) > 0 or len(rec._origin.section_ids._origin):
                for section in rec.section_ids:
                    # same logic as _onchange_project_scope
                    section_list.append(section.section_name.id)
                    if section._origin.section_name._origin.id:
                        if section.section_name.id != section._origin.section_name._origin.id:
                            changed_section.append(section._origin.section_name._origin.id)
                    else:
                        changed_section.append(section.section_name.id)
            if len(rec.variable_ids) > 0:
                for variable in rec.variable_ids:
                    if variable.section_name.id in changed_section:
                        rec.variable_ids = [(2, variable._origin.id, 0)]
                    elif variable.section_name.id not in section_list:
                        rec.variable_ids = [(2, variable.id, 0)]
            else:
                for material in rec.material_estimation_ids:
                    if material.section_name.id in changed_section:
                        rec.material_estimation_ids = [(2, material._origin.id, 0)]
                    elif material.section_name.id not in section_list:
                        rec.material_estimation_ids = [(2, material.id, 0)]
                for labour in rec.labour_estimation_ids:
                    if labour.section_name.id in changed_section:
                        rec.labour_estimation_ids = [(2, labour._origin.id, 0)]
                    elif labour.section_name.id not in section_list:
                        rec.labour_estimation_ids = [(2, labour.id, 0)]
                for overhead in rec.overhead_estimation_ids:
                    if overhead.section_name.id in changed_section:
                        rec.overhead_estimation_ids = [(2, overhead._origin.id, 0)]
                    elif overhead.section_name.id not in section_list:
                        rec.overhead_estimation_ids = [(2, overhead.id, 0)]
                for internal in rec.internal_asset_ids:
                    if internal.section_name.id in changed_section:
                        rec.internal_asset_ids = [(2, internal._origin.id, 0)]
                    elif internal.section_name.id not in section_list:
                        rec.internal_asset_ids = [(2, internal.id, 0)]
                for equipment in rec.equipment_estimation_ids:
                    if equipment.section_name.id in changed_section:
                        rec.equipment_estimation_ids = [(2, equipment._origin.id, 0)]
                    elif equipment.section_name.id not in section_list:
                        rec.equipment_estimation_ids = [(2, equipment.id, 0)]
                for subcon in rec.subcon_estimation_ids:
                    if subcon.section_name.id in changed_section:
                        rec.subcon_estimation_ids = [(2, subcon._origin.id, 0)]
                    elif subcon.section_name.id not in section_list:
                        rec.subcon_estimation_ids = [(2, subcon.id, 0)]

    @api.onchange('variable_ids')
    def update_material(self):
        if self.contract_category == "main":
            variable_list = []

            for rec in self.variable_ids:
                material = []
                labour = []
                subcon = []
                overhead = []
                equip = []
                asset = []

                scope = rec.project_scope
                section = rec.section_name
                variable = rec.variable_name
                var_quantity = 1

                if scope and section and variable:
                    if var_quantity > 0:
                        if rec.onchange_pass == False:
                            rec.write({'onchange_pass': True})

                            # for material
                            if variable.material_variable_ids:
                                for mater in self.material_estimation_ids:
                                    if mater.project_scope != False and mater.section_name != False and len(
                                            mater.variable_ref) != 0:
                                        if mater.project_scope == scope and mater.section_name == section and mater.variable_ref == variable:
                                            self.material_estimation_ids = [(2, mater.id)]
                                for mat in variable.material_variable_ids:
                                    matx = (0, 0, {
                                        'product_id': mat.product_id.id,
                                        'quantity': var_quantity * mat.quantity,
                                        'subtotal': mat.unit_price * (var_quantity * mat.quantity),
                                        'unit_price': mat.unit_price,
                                        'uom_id': mat.uom_id.id,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id,
                                        'description': mat.description,
                                        'group_of_product': mat.group_of_product.id
                                    })
                                    material.append(matx)
                                self.material_estimation_ids = material

                            # for labor
                            if variable.labour_variable_ids:
                                for labo in self.labour_estimation_ids:
                                    if labo.project_scope != False and labo.section_name != False and len(
                                            labo.variable_ref) != 0:
                                        if labo.project_scope == scope and labo.section_name == section and labo.variable_ref == variable:
                                            self.labour_estimation_ids = [(2, labo.id)]
                                for lab in variable.labour_variable_ids:
                                    labx = (0, 0, {
                                        'product_id': lab.product_id.id,
                                        'subtotal': lab.unit_price * (lab.contractors * (var_quantity * lab.time)),
                                        'unit_price': lab.unit_price,
                                        'uom_id': lab.uom_id.id,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id,
                                        'description': lab.description,
                                        'group_of_product': lab.group_of_product.id,
                                        'contractors': lab.contractors,
                                        'time': var_quantity * lab.time,
                                        'quantity': lab.contractors * (var_quantity * lab.time),
                                    })
                                    labour.append(labx)
                                self.labour_estimation_ids = labour

                            # for subcon
                            if variable.subcon_variable_ids:
                                for subc in self.subcon_estimation_ids:
                                    if subc.project_scope != False and subc.section_name != False and len(
                                            subc.variable_ref) != 0:
                                        if subc.project_scope == scope and subc.section_name == section and subc.variable_ref == variable:
                                            self.subcon_estimation_ids = [(2, subc.id)]
                                for sub in variable.subcon_variable_ids:
                                    subx = (0, 0, {
                                        'variable': sub.variable.id,
                                        'quantity': var_quantity * sub.quantity,
                                        'subtotal': sub.unit_price * (var_quantity * sub.quantity),
                                        'unit_price': sub.unit_price,
                                        'uom_id': sub.uom_id.id,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id,
                                        'description': sub.description,
                                    })
                                    subcon.append(subx)
                                self.subcon_estimation_ids = subcon

                            # for over
                            if variable.overhead_variable_ids:
                                for overh in self.overhead_estimation_ids:
                                    if overh.project_scope != False and overh.section_name != False and len(
                                            overh.variable_ref) != 0:
                                        if overh.project_scope == scope and overh.section_name == section and overh.variable_ref == variable:
                                            self.overhead_estimation_ids = [(2, overh.id)]
                                for over in variable.overhead_variable_ids:
                                    overx = (0, 0, {
                                        'overhead_catagory': over.overhead_catagory,
                                        'product_id': over.product_id.id,
                                        'quantity': var_quantity * over.quantity,
                                        'subtotal': over.unit_price * (var_quantity * over.quantity),
                                        'unit_price': over.unit_price,
                                        'uom_id': over.uom_id.id,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id,
                                        'description': over.description,
                                        'group_of_product': over.group_of_product.id
                                    })
                                    overhead.append(overx)
                                self.overhead_estimation_ids = overhead

                            # for equip
                            if variable.equipment_variable_ids:
                                for equi in self.equipment_estimation_ids:
                                    if equi.project_scope != False and equi.section_name != False and len(
                                            equi.variable_ref) != 0:
                                        if equi.project_scope == scope and equi.section_name == section and equi.variable_ref == variable:
                                            self.equipment_estimation_ids = [(2, equi.id)]
                                for eqp in variable.equipment_variable_ids:
                                    eqpx = (0, 0, {
                                        'product_id': eqp.product_id.id,
                                        'quantity': var_quantity * eqp.quantity,
                                        'subtotal': eqp.unit_price * (var_quantity * eqp.quantity),
                                        'unit_price': eqp.unit_price,
                                        'uom_id': eqp.uom_id.id,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id,
                                        'description': eqp.description,
                                        'group_of_product': eqp.group_of_product.id
                                    })
                                    equip.append(eqpx)
                                self.equipment_estimation_ids = equip

                            # for asset
                            if variable.asset_variable_ids:
                                for asse in self.internal_asset_ids:
                                    if asse.project_scope != False and asse.section_name != False and len(
                                            asse.variable_ref) != 0:
                                        if asse.project_scope == scope and asse.section_name == section and asse.variable_ref == variable:
                                            self.internal_asset_ids = [(2, asse.id)]
                                for ass in variable.asset_variable_ids:
                                    assx = (0, 0, {
                                        'asset_category_id': ass.asset_category_id.id,
                                        'asset_id': ass.asset_id.id,
                                        'quantity': var_quantity * ass.quantity,
                                        'subtotal': ass.unit_price * (var_quantity * ass.quantity),
                                        'unit_price': ass.unit_price,
                                        'uom_id': ass.uom_id.id,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id,
                                        'description': ass.description,
                                    })
                                    asset.append(assx)
                                self.internal_asset_ids = asset
                        variable_list.append((scope.name, section.name, variable.name))

            for mat in self.material_estimation_ids:
                if mat.project_scope != False and mat.section_name != False and len(mat.variable_ref) != 0:
                    if (mat.project_scope.name, mat.section_name.name, mat.variable_ref.name) not in variable_list:
                        self.material_estimation_ids = [(2, mat.id)]
            for lab in self.labour_estimation_ids:
                if lab.project_scope != False and lab.section_name != False and len(lab.variable_ref) != 0:
                    if (lab.project_scope.name, lab.section_name.name, lab.variable_ref.name) not in variable_list:
                        self.labour_estimation_ids = [(2, lab.id)]
            for ov in self.overhead_estimation_ids:
                if ov.project_scope != False and ov.section_name != False and len(ov.variable_ref) != 0:
                    if (ov.project_scope.name, ov.section_name.name, ov.variable_ref.name) not in variable_list:
                        self.overhead_estimation_ids = [(2, ov.id)]
            for asset in self.internal_asset_ids:
                if asset.project_scope != False and asset.section_name != False and len(asset.variable_ref) != 0:
                    if (asset.project_scope.name, asset.section_name.name, asset.variable_ref.name) not in variable_list:
                        self.internal_asset_ids = [(2, asset.id)]
            for eq in self.equipment_estimation_ids:
                if eq.project_scope != False and eq.section_name != False and len(eq.variable_ref) != 0:
                    if (eq.project_scope.name, eq.section_name.name, eq.variable_ref.name) not in variable_list:
                        self.equipment_estimation_ids = [(2, eq.id)]
            for sub in self.subcon_estimation_ids:
                if sub.project_scope != False and sub.section_name != False and len(sub.variable_ref) != 0:
                    if (sub.project_scope.name, sub.section_name.name, sub.variable_ref.name) not in variable_list:
                        self.subcon_estimation_ids = [(2, sub.id)]

    @api.depends('material_estimation_ids.subtotal', 'labour_estimation_ids.subtotal', 'subcon_estimation_ids.subtotal',
                 'overhead_estimation_ids.subtotal', 'equipment_estimation_ids.subtotal', 'internal_asset_ids.subtotal')
    def _onchange_calculate_total(self):
        for rec in self:
            rec.total_material_estimate = sum([item.subtotal for item in rec.material_estimation_ids])
            rec.total_labour_estimate = sum([item.subtotal for item in rec.labour_estimation_ids])
            rec.total_subcon_estimate = sum([item.subtotal for item in rec.subcon_estimation_ids])
            rec.total_overhead_estimate = sum([item.subtotal for item in rec.overhead_estimation_ids])
            rec.total_equipment_estimate = sum([item.subtotal for item in rec.equipment_estimation_ids])
            rec.total_internal_assets_estimate = sum([item.subtotal for item in rec.internal_asset_ids])
            rec.total_assets_estimate = sum([
                rec.total_equipment_estimate,
                rec.total_internal_assets_estimate
            ])
            rec.total_job_estimate = sum([
                rec.total_material_estimate,
                rec.total_labour_estimate,
                rec.total_subcon_estimate,
                rec.total_overhead_estimate,
                rec.total_equipment_estimate,
                rec.total_internal_assets_estimate
            ])

    @api.constrains('start_date', 'end_date')
    def constrains_date(self):
        for rec in self:
            if rec.start_date != False and rec.end_date != False:
                if rec.start_date > rec.end_date:
                    raise UserError(_('End date should be after start date.'))

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id
            line.company_id = res_user_id.company_id

    def exist_main_contract(self, is_from_create=False):
        for rec in self:
            if rec.project_id:
                main_contract = self.env['sale.order.const'].search(
                    [('project_id', '=', rec.project_id.id), ('contract_category', '=', 'main'),
                     ('state', 'in', ['sale', 'done'])], limit=1)
                job_estimate = self.env['job.estimate'].search(
                    [('project_id', '=', rec.project_id.id), ('contract_category', '=', 'main'),
                     ('state_new', '=', 'approved')], limit=1)

                if rec.department_type == 'project':
                    sale_count = self.env['sale.order.const'].search_count(
                        [('project_id', '=', rec.project_id.id), ('contract_category', '=', 'main'),
                         ('state', 'in', ['sale', 'done'])])
                    if sale_count > 0:
                        rec.write({'contract_category': 'var',
                                   'main_contract_ref': main_contract,
                                   'customer_ref': main_contract.client_order_ref})
                    else:
                        rec.write({'contract_category': 'main',
                                   'main_contract_ref': False,
                                   'customer_ref': False})
                else:
                    job_count = self.env['job.estimate'].search_count(
                        [('project_id', '=', rec.project_id.id), ('contract_category', '=', 'main'),
                         ('state_new', '=', 'approved')])
                    if job_count > 0:
                        rec.write({'contract_category': 'var',
                                   'job_contract_ref': job_estimate,
                                   'customer_ref': job_estimate.customer_ref})
                    else:
                        rec.write({'contract_category': 'main',
                                   'job_contract_ref': False,
                                   'customer_ref': False})

    @api.onchange('project_id')
    def onchange_project_id(self):
        for rec in self:
            if rec.project_id:
                project = rec.project_id
                rec.partner_id = project.partner_id
                rec.branch_id = project.branch_id
                rec.start_date = project.start_date
                rec.end_date = project.end_date

                rec.customer_ref = project.customer_ref
                rec.analytic_idz = [(6, 0, [v.id for v in project.analytic_idz])]
                rec.sales_person_id = [(6, 0, [v.id for v in project.sales_person_id])]
                rec.sales_team_id = project.sales_team
                rec.lead_id = project.lead_id

                rec.job_estimate_template = False

                self.exist_main_contract()

                if rec.contract_category == 'main':
                    rec.project_scope_ids = [(6, 0, [])]
                    rec.section_ids = [(6, 0, [])]
                    for scope in project.project_scope_ids:
                        rec.project_scope_ids = [(0, 0, {
                            'project_scope': scope.project_scope.id,
                            'description': scope.description,
                        })]

                    for section in project.project_section_ids:
                        rec.section_ids = [(0, 0, {
                            'project_scope': section.project_scope.id,
                            'section_name': section.section.id,
                            'description': section.description,
                            'quantity': section.quantity,
                            'uom_id': section.uom_id.id,
                        })]

                    if rec.job_estimate_template:
                        rec._onchange_job_estimate_template()

    # when import boq
    def onchange_project_id_when_import(self):
        for rec in self:
            if rec.project_id:
                project = rec.project_id
                rec.partner_id = project.partner_id
                rec.branch_id = project.branch_id
                rec.start_date = project.start_date
                rec.end_date = project.end_date

                rec.customer_ref = project.customer_ref
                rec.analytic_idz = [(6, 0, [v.id for v in project.analytic_idz])]
                rec.sales_person_id = [(6, 0, [v.id for v in project.sales_person_id])]
                rec.sales_team_id = project.sales_team
                rec.lead_id = project.lead_id

                rec.job_estimate_template = False

                self.exist_main_contract()

    @api.onchange('section_ids')
    def _onchange_check_quentity_section(self):
        for rec in self:
            if len(rec.section_ids) > 0:
                for line in rec.section_ids:
                    if line.quantity == 0:
                        raise ValidationError(
                            _('In tab section, the quantity of section "%s" should be greater than 0.' % (
                                (line.section_name.name))))

    def job_confirm(self):
        if len(self.project_scope_ids) == 0:
            raise ValidationError(
                _('The Project Scope table is empty. Please add at least 1 item to the Project Scope table.'))
        if len(self.section_ids) == 0:
            raise ValidationError(
                _('The Section table is empty. Please add at least 1 item to the Section table.'))

        for tabs in self:
            if len(tabs.material_estimation_ids) == len(tabs.labour_estimation_ids) == len(
                    tabs.overhead_estimation_ids) == len(tabs.internal_asset_ids) == len(
                tabs.equipment_estimation_ids) == len(tabs.subcon_estimation_ids) == 0:
                raise ValidationError(
                    _('The Estimation tables are empty. Please add at least 1 product for estimation.'))

        for rec in self:
            if len(rec.material_estimation_ids) > 0:
                for material in rec.material_estimation_ids:
                    if material.unit_price <= 0:
                        raise ValidationError(
                            _('In tab material estimation, the unit price of product "%s" should be greater than 0.' % (
                                (material.product_id.name))))
            if len(rec.labour_estimation_ids) > 0:
                for labour in rec.labour_estimation_ids:
                    if labour.unit_price <= 0:
                        raise ValidationError(
                            _('In tab labour estimation, the unit price of product "%s" should be greater than 0.' % (
                                (labour.product_id.name))))
            if len(rec.overhead_estimation_ids) > 0:
                for overhead in rec.overhead_estimation_ids:
                    if overhead.unit_price <= 0:
                        raise ValidationError(
                            _('In tab overhead estimation, the unit price of product "%s" should be greater than 0.' % (
                                (overhead.product_id.name))))
            if len(rec.equipment_estimation_ids) > 0:
                for equipment in rec.equipment_estimation_ids:
                    if equipment.unit_price <= 0:
                        raise ValidationError(
                            _('In tab equipment estimation, the unit price of product "%s" should be greater than 0.' % (
                                (equipment.product_id.name))))
            if len(rec.internal_asset_ids) > 0:
                for internal_asset in rec.internal_asset_ids:
                    if internal_asset.unit_price <= 0:
                        raise ValidationError(
                            _('In tab internal asset estimation, the unit price of asset "%s" should be greater than 0.' % (
                                (internal_asset.asset_id.name))))
            if len(rec.subcon_estimation_ids) > 0:
                for subcon in rec.subcon_estimation_ids:
                    if subcon.unit_price <= 0:
                        raise ValidationError(
                            _('In tab subcon estimation, the unit price of job subcon "%s" should be greater than 0.' % (
                                (subcon.variable.name))))

        # res = self.write({'state': 'confirmed',
        #                   'state_new': 'confirmed'
        #                   })
        # convert above code to query
        self.env.cr.execute(
            "UPDATE job_estimate SET state = 'confirmed', state_new = 'confirmed' WHERE id = %s", (self.id,)
        )

        self.project_id.write({'start_date': self.start_date,
                               'end_date': self.end_date,
                               'partner_id': self.partner_id.id
                               })

        contract_list_var = []
        if self.department_type == 'department':
            contract_list_var.append(
                (0, 0, {'name': self.id,
                        'contract_amount': self.total_job_estimate,
                        'approved_date': datetime.now()
                        }

                 ))

            if self.contract_category == 'main':

                self.project_id.project_scope_ids = [(5, 0, 0)]
                self.project_id.project_section_ids = [(5, 0, 0)]
                scope_list = []
                section_list = []
                for scope in self.project_scope_ids:
                    scope_list.append((0, 0, {
                        'project_scope': scope.project_scope.id,
                        'description': scope.description,
                    })
                                      )

                for section in self.section_ids:
                    section_list.append((0, 0, {
                        'project_scope': section.project_scope.id,
                        'section': section.section_name.id,
                        'description': section.description,
                        'quantity': section.quantity,
                        'uom_id': section.uom_id.id,
                    })
                                        )

                self.project_id.write({
                    'main_job_estimate': self.id,
                    'main_contract_amount': self.total_job_estimate,
                    'main_approved_date': datetime.now(),
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'warehouse_address': self.warehouse_address.id,
                    # 'branch_id': self.branch_id.id,
                    'analytic_idz': [(6, 0, [v.id for v in self.analytic_idz])],
                    'primary_states': 'progress',
                    'project_scope_ids': scope_list,
                    'project_section_ids': section_list,
                })

            else:

                exist_scope = []
                scope_list = []
                for sco_pro in self.project_id.project_scope_ids:
                    exist_scope.append(sco_pro.project_scope.id)

                for sco_con in self.project_scope_ids:
                    if sco_con.project_scope.id not in exist_scope:
                        scope_list.append((0, 0, {
                            'project_scope': sco_con.project_scope.id,
                            'description': sco_con.description,
                        })
                                          )
                    else:
                        pass

                exist_section = []
                section_list = []
                for sec_pro in self.project_id.project_section_ids:
                    same_pro = str(sec_pro.project_scope.id) + ' - ' + str(sec_pro.section.id)
                    exist_section.append(same_pro)

                for sec_con in self.section_ids:
                    same_con = str(sec_con.project_scope.id) + ' - ' + str(sec_con.section.id)
                    if same_con not in exist_section:
                        section_list.append((0, 0, {
                            'project_scope': sec_con.project_scope.id,
                            'section': sec_con.section.id,
                            'description': sec_con.description,
                            'quantity': sec_con.quantity,
                            'uom_id': sec_con.uom_id.id,
                        })
                                            )
                    else:
                        pass

                self.project_id.write({
                    'variation_order_internal_ids': contract_list_var,
                    'project_scope_ids': scope_list,
                    'project_section_ids': section_list,
                })

        return self

    def job_confirm_2(self):
        for rec in self:
            rec.job_confirm()

    @api.model
    def create(self, vals):
        vals['name'] = _('New')

        res = super(JobEstimate, self).create(vals)
        if self.external_id:
            id_exist = self.env['job.estimate'].search(
                [('external_id', '=', self.external_id)])
            if len(id_exist) > 1:
                for res in id_exist:
                    raise ValidationError((
                                              _("The external id already exists with BOQ '{}', so please change the external.".format(
                                                  res.name))))
        res.exist_main_contract(is_from_create=True)
        if res.contract_category:
            if res.contract_category == 'var':
                res.name = self.env['ir.sequence'].next_by_code('job.sequence.vo')
            elif res.contract_category == 'main':
                res.name = self.env['ir.sequence'].next_by_code('job.sequence.new')

        return res

    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', True)]}, index=True, default=lambda self: _('New'))
    external_id = fields.Char(string='External ID', copy=False, )
    state = fields.Selection(selection_add=[
        ('rejected', 'Rejected'),
        ('sale', 'Sale Order Created'),
        ('to_approve', 'Waiting For Approval'),
        ('quotation_reject', 'Quotation Rejected'),
        ('quotation_cancel', 'Quotation Canceled'),
        ('revised', 'Revised')
    ], string='Status', default='draft')
    state_new = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Estimation Sent'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Canceled'),
        ('revised', 'Revised'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    sale_state = fields.Selection([
        ('draft', 'Quotation Draft'),
        ('quotation', 'Quotation Created'),
        ('rejected', 'Quotation Rejected'),
        ('sale', 'Sale Order Created'),
        ('canceled', 'Sale Order Canceled')
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    sale_state_1 = fields.Selection(related='sale_state', string='Status', readonly=True, copy=False, index=True)
    sale_state_2 = fields.Selection(related='sale_state', string='Status', readonly=True, copy=False, index=True)
    state_1 = fields.Selection(related='state_new', tracking=False)
    state_2 = fields.Selection(related='state_new', tracking=False)

    start_date = fields.Date(string="Planned Start Date", tracking=True, readonly=True,
                             states={'draft': [('readonly', False)], 'approved': [('readonly', False)],
                                     'sent': [('readonly', False)],
                                     'to_approve': [('readonly', False)]})
    end_date = fields.Date(string="Planned End Date", tracking=True, readonly=True,
                           states={'draft': [('readonly', False)], 'approved': [('readonly', False)],
                                   'sent': [('readonly', False)],
                                   'to_approve': [('readonly', False)]})
    project_id = fields.Many2one('project.project', string='Project', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(related='project_id.partner_id', string='Customer',
                                 change_default=True, index=True, tracking=1)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    analytic_idz = fields.Many2many('account.analytic.tag', string='Analytic Group',
                                    domain="[('company_id', '=', company_id)]", readonly=True,
                                    states={'draft': [('readonly', False)], 'approved': [('readonly', False)],
                                            'sent': [('readonly', False)],
                                            'to_approve': [('readonly', False)]})
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch",
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    add_note = fields.Text('Additional Notes')

    project_scope_ids = fields.One2many('project.scope.estimate', 'scope_id', 'Project Scope Estimation')
    section_ids = fields.One2many('section.estimate', 'section_id', 'Section Estimation')
    variable_ids = fields.One2many('variable.estimate', 'variable_id', 'Variable Estimation')
    # estimates
    subcon_estimation_ids = fields.One2many('subcon.estimate', 'subcon_id', 'Subcon Estimation')
    equipment_estimation_ids = fields.One2many('equipment.estimate', 'equipment_id', 'Equipment Estimation')
    internal_asset_ids = fields.One2many('internal.assets', 'asset_job_id', string='Internal Asset')

    description = fields.Text('Description')
    total_material_estimate = fields.Monetary(string='Total Material Estimate', default=0.0,
                                               compute="_onchange_calculate_total")
    total_labour_estimate = fields.Monetary(string='Total Labour Estimate', default=0.0,
                                             compute="_onchange_calculate_total")
    total_subcon_estimate = fields.Monetary(string='Total Subcon Estimate', default=0.0,
                                             compute="_onchange_calculate_total")
    total_overhead_estimate = fields.Monetary(string='Total Overhead Estimate', default=0.0,
                                               compute="_onchange_calculate_total")
    total_equipment_estimate = fields.Monetary(string='Total Equipment Lease Estimate', default=0.0,
                                                compute="_onchange_calculate_total")
    total_internal_assets_estimate = fields.Monetary(string='Total Internal Asset Estimate',
                                                     default=0.0,  compute="_onchange_calculate_total")
    total_assets_estimate = fields.Monetary(string='Total Assets Estimate',
                                            default=0.0,  compute="_onchange_calculate_total")
    total_job_estimate = fields.Monetary(string='Total BOQ',  compute="_onchange_calculate_total")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    contract_category = fields.Selection([
        ('main', 'Main Contract'),
        ('var', 'Variation Order')
    ], string="Contract Category", tracking=True)
    main_contract_ref = fields.Many2one('sale.order.const', 'Main Contract', tracking=True,
                                        domain="[('state', '=', 'sale')]")
    job_contract_ref = fields.Many2one('job.estimate', 'Main Contract', tracking=True,
                                       domain="[('state_new', '=', 'approved')]")
    combine_to_existing_quotation = fields.Boolean(string="Combine")

    active = fields.Boolean(string='Active', default=True)

    # Other Info
    sales_person_id = fields.Many2many('res.users', 'sales_employee_id', string='Salesperson')
    sales_team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        change_default=True, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    quotation_id = fields.Many2many('sale.order.const', string="Sales Quotation",
                                    domain="[('project_id', '=', project_id)]")
    contract_state = fields.Selection(related='quotation_id.state', string='Contract Status')

    estimation_sent = fields.Boolean(string="Sent", default=False)
    said = fields.Char(compute="_said", string="Say", help="Say (English)", store=True)
    job_estimate_template = fields.Many2many('job.estimate.template', string='BOQ Template', readonly=True,
                                             states={'draft': [('readonly', False)], 'approved': [('readonly', False)],
                                                     'sent': [('readonly', False)],
                                                     'to_approve': [('readonly', False)]})
    save_as_template = fields.Boolean(string="Save as a Template")
    name_template = fields.Char(string="Template Name")
    duration = fields.Text(string='Duration', compute='_compute_duration')
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    is_department = fields.Boolean()
    is_rejected = fields.Boolean(default=False)
    is_cancelled = fields.Boolean(default=False)
    lead_id = fields.Many2one('crm.lead', string='Opportunity')
    customer_exist = fields.Boolean(string="Customer Exist", compute="_compute_customer_exist")

    # __field
    is_revision_created = fields.Boolean(string='Revision Created', copy=False)
    is_revision_je = fields.Boolean(string="Revision JE")
    main_revision_je_id = fields.Many2one(comodel_name='job.estimate', string='Main Revision BOQ')
    revision_je_id = fields.Many2one('job.estimate', string='Revision BOQ')
    revision_history_id = fields.Many2many("job.estimate",
                                           relation="je_revision_order_history",
                                           column1="je_id",
                                           column2="revision_id",
                                           string="")

    # __field
    approval_matrix_state = fields.Selection(related='state_new', tracking=False)
    approval_matrix_state_1 = fields.Selection(related='state_new', tracking=False)
    approval_matrix_state_2 = fields.Selection(related='state_new', tracking=False)
    approval_matrix_state_3 = fields.Selection(related='state_new', tracking=False)
    approval_matrix_state_4 = fields.Selection(related='state_new', tracking=False)
    approving_matrix_sale_id = fields.Many2one('approval.matrix.job.estimates', string="Approval Matrix", store=True)
    approved_matrix_ids = fields.One2many('approval.matrix.job.estimates.line', 'order_id', store=True)
    is_job_estimate_approval_matrix = fields.Boolean(string="Custome Matrix",
                                                     compute='_compute_is_customer_approval_matrix', store=False)
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.job.estimates.line', string='Sale Approval Matrix Line',
                                              store=False)

    approving_matrix_job_id = fields.Many2one('approval.matrix.job.estimates', string="Approval Matrix",
                                              compute='_compute_approving_customer_matrix', store=True)
    job_estimate_user_ids = fields.One2many('job.estimate.approver.user', 'job_estimate_approver_id',
                                            string='Approver')
    approvers_ids = fields.Many2many('res.users', 'job_estimate_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')

    # __field
    section_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    section_computed = fields.Many2many('section.line', string="computed section lines")

    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')
    revision_count = fields.Integer(string='BOQ Revision Count', compute="get_revision_count")
    total_variation_order_material = fields.Monetary(string='Total Variation Order Material', compute="_compute_total_variation_order",
                                                     store=True)
    total_variation_order_labour = fields.Monetary(string='Total Variation Order Labour',
                                                     compute="_compute_total_variation_order",
                                                     store=True)
    total_variation_order_overhead = fields.Monetary(string='Total Variation Order Overhead',
                                                     compute="_compute_total_variation_order",
                                                     store=True)
    total_variation_order_asset = fields.Monetary(string='Total Variation Order Internal Asset',
                                                     compute="_compute_total_variation_order",
                                                     store=True)
    total_variation_order_equipment = fields.Monetary(string='Total Variation Order Equipment',
                                                     compute="_compute_total_variation_order",
                                                     store=True)
    total_variation_order_subcon = fields.Monetary(string='Total Variation Order Subcon',
                                                     compute="_compute_total_variation_order",
                                                     store=True)
    total_variation_order = fields.Monetary(string='Total Variation Order', compute="_compute_total_variation_order",
                                            store=True)
    is_over_budget_ratio = fields.Boolean(string="Over Budget Ratio")
    ratio_value = fields.Float(string="Ratio Value(%)")

    @api.depends('material_estimation_ids', 'labour_estimation_ids', 'subcon_estimation_ids', 'overhead_estimation_ids',
                 'equipment_estimation_ids', 'internal_asset_ids')
    def _compute_total_variation_order(self):
        for rec in self:
            total = 0
            total_material = 0
            total_labour = 0
            total_subcon = 0
            total_overhead = 0
            total_equipment = 0
            total_internal_assets = 0
            if rec.contract_category == 'var':
                total_material = sum([(item.unit_price * item.quantity) for item in rec.material_estimation_ids])
                for labour in rec.labour_estimation_ids:
                    if labour.contractors == 0:
                        total_labour += labour.unit_price * labour.time
                    elif labour.time == 0:
                        total_labour += labour.unit_price * labour.contractors
                    else:
                        total_labour += labour.unit_price * labour.time * labour.contractors

                total_subcon = sum([(item.unit_price * item.quantity) for item in rec.subcon_estimation_ids])
                total_overhead = sum([(item.unit_price * item.quantity) for item in rec.overhead_estimation_ids])
                total_equipment = sum([(item.unit_price * item.quantity) for item in rec.equipment_estimation_ids])
                total_internal_assets = sum([(item.unit_price * item.quantity) for item in rec.internal_asset_ids])

                total = total_material + total_labour + total_subcon + total_overhead + total_equipment + total_internal_assets
            rec.total_variation_order = total
            rec.total_variation_order_material = total_material
            rec.total_variation_order_labour = total_labour
            rec.total_variation_order_subcon = total_subcon
            rec.total_variation_order_overhead = total_overhead
            rec.total_variation_order_equipment = total_equipment
            rec.total_variation_order_asset = total_internal_assets
    
    @api.depends('project_id')
    def _compute_customer_exist(self):
        for record in self:
            if record.project_id.partner_id:
                record.customer_exist = True
            else:
                record.customer_exist = False

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group(
                    'sales_team.group_sale_manager'):
                if rec.department_type == 'project':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'project'),
                                           ('primary_states', 'in', ('draft', 'progress')),
                                           ('company_id', '=', rec.company_id.id),
                                           ('id', 'in', self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'),
                                                  ('primary_states', 'in', ('draft', 'progress')),
                                                  ('company_id', '=', rec.company_id.id),
                                                  ('id', 'in', self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {
                            'project_id': [('department_type', '=', 'project'),
                                           ('primary_states', 'in', ('draft', 'progress')),
                                           ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'),
                                                  ('primary_states', 'in', ('draft', 'progress')),
                                                  ('company_id', '=', rec.company_id.id)]}
                    }

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                difference_days = (record.end_date - record.start_date).days
                record.duration = f'{str(difference_days)} days'
            else:
                record.duration = False

    def save_as_a_template(self):
        for job in self:
            search_template = self.env['job.estimate.template'].search([('name', '=', job.name_template)])
            if len(search_template) > 0:
                raise ValidationError(
                    _('Template name already exists in BOQ template, please change the template name.'))

            if not job.project_scope_ids:
                raise ValidationError(_('Please add at least 1 project scope.'))

            scope = []
            section = []
            material = []
            labour = []
            overhead = []
            equipment = []
            asset = []
            subcon = []

            for sco in job.project_scope_ids:
                scope.append(
                    (0, 0, {'project_scope': sco.project_scope.id,
                            'subtotal': sco.subtotal,
                            }
                     ))
            for sec in job.section_ids:
                section.append(
                    (0, 0, {'project_scope': sec.project_scope.id,
                            'section_name': sec.section_name.id,
                            'quantity': sec.quantity,
                            'uom_id': sec.uom_id.id,
                            'subtotal': sec.subtotal,
                            }
                     ))
            for mat in job.material_estimation_ids:
                material.append(
                    (0, 0, {'project_scope': mat.project_scope.id,
                            'section_name': mat.section_name.id,
                            'variable_ref': mat.variable_ref.id,
                            'group_of_product': mat.group_of_product.id,
                            'type': mat.type,
                            'product_id': mat.product_id.id,
                            'description': mat.description,
                            'coefficient': mat.coefficient,
                            'quantity': mat.quantity,
                            'uom_id': mat.uom_id.id,
                            'unit_price': mat.unit_price,
                            'subtotal': mat.subtotal,
                            }
                     ))
            for lab in job.labour_estimation_ids:
                labour.append(
                    (0, 0, {'project_scope': lab.project_scope.id,
                            'section_name': lab.section_name.id,
                            'variable_ref': lab.variable_ref.id,
                            'group_of_product': lab.group_of_product.id,
                            'type': lab.type,
                            'product_id': lab.product_id.id,
                            'description': lab.description,
                            'contractors': lab.contractors,
                            'coefficient': lab.coefficient,
                            'time': lab.time,
                            'quantity': lab.quantity,
                            'uom_id': lab.uom_id.id,
                            'unit_price': lab.unit_price,
                            'subtotal': lab.subtotal,
                            }
                     ))
            for over in job.overhead_estimation_ids:
                overhead.append(
                    (0, 0, {'project_scope': over.project_scope.id,
                            'section_name': over.section_name.id,
                            'variable_ref': over.variable_ref.id,
                            'group_of_product': over.group_of_product.id,
                            'type': over.type,
                            'product_id': over.product_id.id,
                            'description': over.description,
                            'coefficient': over.coefficient,
                            'quantity': over.quantity,
                            'uom_id': over.uom_id.id,
                            'unit_price': over.unit_price,
                            'subtotal': over.subtotal,
                            'overhead_catagory': over.overhead_catagory,
                            }
                     ))
            for equip in job.equipment_estimation_ids:
                equipment.append(
                    (0, 0, {'project_scope': equip.project_scope.id,
                            'section_name': equip.section_name.id,
                            'variable_ref': equip.variable_ref.id,
                            'group_of_product': equip.group_of_product.id,
                            'type': equip.type,
                            'product_id': equip.product_id.id,
                            'description': equip.description,
                            'coefficient': equip.coefficient,
                            'quantity': equip.quantity,
                            'uom_id': equip.uom_id.id,
                            'unit_price': equip.unit_price,
                            'subtotal': equip.subtotal,
                            }
                     ))
            for ass in job.internal_asset_ids:
                asset.append(
                    (0, 0, {'project_scope': ass.project_scope.id,
                            'section_name': ass.section_name.id,
                            'variable_ref': ass.variable_ref.id,
                            'asset_category_id': ass.asset_category_id.id,
                            'type': ass.type,
                            'asset_id': ass.asset_id.id,
                            'description': ass.description,
                            'coefficient': ass.coefficient,
                            'quantity': ass.quantity,
                            'uom_id': ass.uom_id.id,
                            'unit_price': ass.unit_price,
                            'subtotal': ass.subtotal,
                            }
                     ))
            for sub in job.subcon_estimation_ids:
                subcon.append(
                    (0, 0, {'project_scope': sub.project_scope.id,
                            'section_name': sub.section_name.id,
                            'variable_ref': sub.variable_ref.id,
                            'variable': sub.variable.id,
                            'type': sub.type,
                            'description': sub.description,
                            'coefficient': sub.coefficient,
                            'quantity': sub.quantity,
                            'uom_id': sub.uom_id.id,
                            'unit_price': sub.unit_price,
                            'subtotal': sub.subtotal,
                            }
                     ))

            self.env['job.estimate.template'].create({
                'name': job.name_template,
                'company_id': job.company_id.id,
                'company_currency_id': job.company_currency_id.id,
                'project_scope_ids': scope,
                'section_ids': section,
                'material_estimation_ids': material,
                'labour_estimation_ids': labour,
                'overhead_estimation_ids': overhead,
                'equipment_estimation_ids': equipment,
                'asset_estimation_ids': asset,
                'subcon_estimation_ids': subcon,
            })

            self.write({'save_as_template': False,
                        'name_template': False})

    @api.onchange('job_estimate_template')
    def _onchange_job_estimate_template(self):
        project = self.project_id
        if self.contract_category == 'main':
            if project:
                for scope in project.project_scope_ids:
                    self.project_scope_ids = [(0, 0, {
                        'project_scope': scope.project_scope.id,
                        'description': scope.description,
                    })]

                for section in project.project_section_ids:
                    self.section_ids = [(0, 0, {
                        'project_scope': section.project_scope.id,
                        'section_name': section.section.id,
                        'description': section.description,
                        'quantity': section.quantity,
                        'uom_id': section.uom_id.id,
                    })]
            self.project_scope_ids = [(6, 0, [])]
            self.section_ids = [(6, 0, [])]
            self.material_estimation_ids = [(5, 0, 0)]
            self.labour_estimation_ids = [(5, 0, 0)]
            self.overhead_estimation_ids = [(5, 0, 0)]
            self.equipment_estimation_ids = [(5, 0, 0)]
            self.internal_asset_ids = [(5, 0, 0)]
            self.subcon_estimation_ids = [(5, 0, 0)]
        if self.job_estimate_template:
            job = self.job_estimate_template
            for sco in job.project_scope_ids:
                same_scope = self.project_scope_ids.filtered(lambda line: line.project_scope.id == sco.project_scope.id)
                if same_scope:
                    same_scope.subtotal = sum([data.subtotal for data in job.project_scope_ids.filtered(
                        lambda line: line.project_scope.id == same_scope.project_scope.id)])
                else:
                    self.project_scope_ids = [(0, 0, {
                        'project_scope': sco.project_scope.id,
                        'subtotal': sum([data.subtotal for data in job.project_scope_ids.filtered(
                            lambda line: line.project_scope.id == sco.project_scope.id)])
                    })]

            for sec in job.section_ids:
                same_section = self.section_ids.filtered(lambda
                                                             line: line.project_scope.id == sec.project_scope.id and line.section_name.id == sec.section_name.id)
                if same_section:
                    if same_section.uom_id.id != sec.uom_id.id:
                        raise ValidationError(
                            f"{sec.section_id.name} Section line cannot merge different UOM ({sec.uom_id.name} | {same_section.uom_id.name} ) ")
                    if same_section.quantity < sec.quantity:
                        same_section.quantity = sec.quantity
                    same_section.subtotal = sum([data.subtotal for data in job.section_ids.filtered(lambda
                                                                                                        line: line.project_scope.id == same_section.project_scope.id and line.section_name.id == same_section.section_name.id)])
                else:
                    self.section_ids = [(0, 0, {
                        'project_scope': sec.project_scope.id,
                        'section_name': sec.section_name.id,
                        'quantity': sec.quantity,
                        'uom_id': sec.uom_id.id})]
                    same_section = self.section_ids.filtered(lambda
                                                                 line: line.project_scope.id == sec.project_scope.id and line.section_name.id == sec.section_name.id)
                    if same_section:
                        same_section.subtotal = sum([data.subtotal for data in job.section_ids.filtered(lambda
                                                                                                            line: line.project_scope.id == same_section.project_scope.id and line.section_name.id == same_section.section_name.id)])

            variable_vals = []
            for variable in job.variable_ids:

                same_variable = self.variable_ids.filtered(lambda
                                                           line: line.project_scope.id == variable.project_scope.id and line.section_name.id == variable.section_name.id and line.variable_name.id == variable.variable_name.id)
                if same_variable:
                    same_variable.subtotal = sum([data.subtotal for data in job.variable_ids.filtered(lambda
                                                                                                        line: line.project_scope.id == same_variable.project_scope.id and line.section_name.id == same_variable.section_name.id and line.variable_name.id == same_variable.variable_name.id)])
                else:
                    variable_vals.append((0, 0, {
                        'project_scope': variable.project_scope.id,
                        'section_name': variable.section_name.id,
                        'variable_name': variable.variable_name.id,
                        'variable_quantity': variable.variable_quantity,
                        'variable_uom': variable.variable_uom.id,
                        'subtotal': sum([data.subtotal for data in job.variable_ids.filtered(lambda
                                                                                             line: line.project_scope.id == variable.project_scope.id and line.section_name.id == variable.section_name.id and line.variable_name.id == variable.variable_name.id)])
                    }))
            if len(variable_vals) > 0:
                self.variable_ids = variable_vals

            for mat in job.material_estimation_ids.filtered(lambda line: len(line.variable_ref) <= 0):
                same_material = self.material_estimation_ids.filtered(lambda
                                                                          line: line.project_scope.id == mat.project_scope.id and line.section_name.id == mat.section_name.id and line.group_of_product.id == mat.group_of_product.id and line.product_id.id == mat.product_id.id)
                if same_material:
                    if same_material.uom_id.id != mat.uom_id.id:
                        raise ValidationError(
                            f"{mat.material_id.name} Material line cannot merge different UOM ({mat.uom_id.name} | {same_material.uom_id.name} ) ")
                    same_material.quantity = sum([data.quantity for data in job.material_estimation_ids.filtered(lambda
                                                                                                                     line: line.project_scope.id == mat.project_scope.id and line.section_name.id == mat.section_name.id and line.group_of_product.id == mat.group_of_product.id and line.product_id.id == mat.product_id.id)])
                    if same_material.unit_price < mat.unit_price:
                        same_material.unit_price = mat.unit_price
                    same_material.onchange_quantity()
                else:
                    self.material_estimation_ids = [(0, 0, {
                        'project_scope': mat.project_scope.id,
                        'section_name': mat.section_name.id,
                        # 'variable_ref': mat.variable_ref.id,
                        'group_of_product': mat.group_of_product.id,
                        'type': mat.type,
                        'product_id': mat.product_id.id,
                        'description': mat.description,
                        'uom_id': mat.uom_id.id,
                        'unit_price': mat.unit_price,
                    })]
                    same_material = self.material_estimation_ids.filtered(lambda
                                                                              line: line.project_scope.id == mat.project_scope.id and line.section_name.id == mat.section_name.id and line.group_of_product.id == mat.group_of_product.id and line.product_id.id == mat.product_id.id)
                    if same_material:
                        same_material.quantity = sum([data.quantity for data in job.material_estimation_ids.filtered(
                            lambda
                                line: line.project_scope.id == same_material.project_scope.id and line.section_name.id == same_material.section_name.id and line.group_of_product.id == same_material.group_of_product.id and line.product_id.id == same_material.product_id.id)])
                        same_material.onchange_quantity()

            for lab in job.labour_estimation_ids.filtered(lambda line: len(line.variable_ref) <= 0):
                same_labor = self.labour_estimation_ids.filtered(lambda
                                                                     line: line.project_scope.id == lab.project_scope.id and line.section_name.id == lab.section_name.id and line.group_of_product.id == lab.group_of_product.id and line.product_id.id == lab.product_id.id)
                if same_labor:
                    if same_labor.uom_id.id != lab.uom_id.id:
                        raise ValidationError(
                            f"{lab.labour_id.name} Labour line cannot merge different UOM ({lab.uom_id.name} | {same_labor.uom_id.name} ) ")
                    same_labor.time = sum([data.time for data in job.labour_estimation_ids.filtered(lambda
                                                                                                        line: line.project_scope.id == lab.project_scope.id and line.section_name.id == lab.section_name.id and line.group_of_product.id == lab.group_of_product.id and line.product_id.id == lab.product_id.id)])
                    same_labor.contractors = sum([data.contractors for data in job.labour_estimation_ids.filtered(lambda
                                                                                                                      line: line.project_scope.id == lab.project_scope.id and line.section_name.id == lab.section_name.id and line.group_of_product.id == lab.group_of_product.id and line.product_id.id == lab.product_id.id)])
                    if same_labor.unit_price < lab.unit_price:
                        same_labor.unit_price = lab.unit_price
                    same_labor.onchange_quantity()
                else:
                    self.labour_estimation_ids = [(0, 0, {
                        'project_scope': lab.project_scope.id,
                        'section_name': lab.section_name.id,
                        # 'variable_ref': lab.variable_ref.id,
                        'group_of_product': lab.group_of_product.id,
                        'type': lab.type,
                        'product_id': lab.product_id.id,
                        'description': lab.description,
                        'quantity': lab.quantity,
                        'uom_id': lab.uom_id.id,
                        'unit_price': lab.unit_price,
                    })]
                    same_labor = self.labour_estimation_ids.filtered(lambda
                                                                         line: line.project_scope.id == lab.project_scope.id and line.section_name.id == lab.section_name.id and line.group_of_product.id == lab.group_of_product.id and line.product_id.id == lab.product_id.id)
                    if same_labor:
                        same_labor.time = sum([data.time for data in job.labour_estimation_ids.filtered(lambda
                                                                                                            line: line.project_scope.id == same_labor.project_scope.id and line.section_name.id == same_labor.section_name.id and line.group_of_product.id == same_labor.group_of_product.id and line.product_id.id == same_labor.product_id.id)])
                        same_labor.contractors = sum([data.contractors for data in job.labour_estimation_ids.filtered(
                            lambda
                                line: line.project_scope.id == same_labor.project_scope.id and line.section_name.id == same_labor.section_name.id and line.group_of_product.id == same_labor.group_of_product.id and line.product_id.id == same_labor.product_id.id)])
                        same_labor.onchange_quantity()

            for over in job.overhead_estimation_ids.filtered(lambda line: len(line.variable_ref) <= 0):
                same_over = self.overhead_estimation_ids.filtered(lambda
                                                                      line: line.project_scope.id == over.project_scope.id and line.section_name.id == over.section_name.id and line.overhead_catagory == over.overhead_catagory and line.group_of_product.id == over.group_of_product.id and line.product_id.id == over.product_id.id)
                if same_over:
                    if same_over.uom_id.id != over.uom_id.id:
                        raise ValidationError(
                            f"{over.overhead_id.name} Overhead line cannot merge different UOM ({over.uom_id.name} | {same_over.uom_id.name} ) ")
                    same_over.quantity = sum([data.quantity for data in job.overhead_estimation_ids.filtered(lambda
                                                                                                                 line: line.project_scope.id == over.project_scope.id and line.section_name.id == over.section_name.id and line.overhead_catagory == over.overhead_catagory and line.group_of_product.id == over.group_of_product.id and line.product_id.id == over.product_id.id)])
                    if same_over.unit_price < over.unit_price:
                        same_over.unit_price = over.unit_price
                    same_over.onchange_quantity()
                else:
                    self.overhead_estimation_ids = [(0, 0, {
                        'project_scope': over.project_scope.id,
                        'section_name': over.section_name.id,
                        # 'variable_ref': over.variable_ref.id,
                        'group_of_product': over.group_of_product.id,
                        'type': over.type,
                        'product_id': over.product_id.id,
                        'description': over.description,
                        'uom_id': over.uom_id.id,
                        'unit_price': over.unit_price,
                        'overhead_catagory': over.overhead_catagory,
                    })]
                    same_over = self.overhead_estimation_ids.filtered(lambda
                                                                          line: line.project_scope.id == over.project_scope.id and line.section_name.id == over.section_name.id and line.overhead_catagory == over.overhead_catagory and line.group_of_product.id == over.group_of_product.id and line.product_id.id == over.product_id.id)
                    if same_over:
                        same_over.quantity = sum([data.quantity for data in job.overhead_estimation_ids.filtered(lambda
                                                                                                                     line: line.project_scope.id == same_over.project_scope.id and line.section_name.id == same_over.section_name.id and line.overhead_catagory == same_over.overhead_catagory and line.group_of_product.id == same_over.group_of_product.id and line.product_id.id == same_over.product_id.id)])
                        same_over.onchange_quantity()

            for equip in job.equipment_estimation_ids.filtered(lambda line: len(line.variable_ref) <= 0):
                same_equip = self.equipment_estimation_ids.filtered(lambda
                                                                        line: line.project_scope.id == equip.project_scope.id and line.section_name.id == equip.section_name.id and line.group_of_product.id == equip.group_of_product.id and line.product_id.id == equip.product_id.id)
                if same_equip:
                    if same_equip.uom_id.id != equip.uom_id.id:
                        raise ValidationError(
                            f"{equip.equipment_id.name} Equipment line cannot merge different UOM ({equip.uom_id.name} | {same_equip.uom_id.name} ) ")
                    same_equip.quantity = sum([data.quantity for data in job.equipment_estimation_ids.filtered(lambda
                                                                                                                   line: line.project_scope.id == equip.project_scope.id and line.section_name.id == equip.section_name.id and line.group_of_product.id == equip.group_of_product.id and line.product_id.id == equip.product_id.id)])
                    if same_equip.unit_price < equip.unit_price:
                        same_equip.unit_price = equip.unit_price
                    same_equip.onchange_quantity()
                else:
                    self.equipment_estimation_ids = [(0, 0, {
                        'project_scope': equip.project_scope.id,
                        'section_name': equip.section_name.id,
                        # 'variable_ref': equip.variable_ref.id,
                        'group_of_product': equip.group_of_product.id,
                        'type': equip.type,
                        'product_id': equip.product_id.id,
                        'description': equip.description,
                        'uom_id': equip.uom_id.id,
                        'unit_price': equip.unit_price,
                    })]
                    same_equip = self.equipment_estimation_ids.filtered(lambda
                                                                            line: line.project_scope.id == equip.project_scope.id and line.section_name.id == equip.section_name.id and line.group_of_product.id == equip.group_of_product.id and line.product_id.id == equip.product_id.id)
                    if same_equip:
                        same_equip.quantity = sum([data.quantity for data in job.equipment_estimation_ids.filtered(
                            lambda
                                line: line.project_scope.id == same_equip.project_scope.id and line.section_name.id == same_equip.section_name.id and line.group_of_product.id == same_equip.group_of_product.id and line.product_id.id == same_equip.product_id.id)])
                        same_equip.onchange_quantity()

            for asset in job.asset_estimation_ids.filtered(lambda line: len(line.variable_ref) <= 0):
                same_asset = self.internal_asset_ids.filtered(lambda
                                                                  line: line.project_scope.id == asset.project_scope.id and line.section_name.id == asset.section_name.id and line.asset_category_id.id == asset.asset_category_id.id and line.asset_id.id == asset.asset_id.id)
                if same_asset:
                    if same_asset.uom_id.id != asset.uom_id.id:
                        raise ValidationError(
                            f"{asset.asset_job_id.name} Internal Asset line cannot merge different UOM ({asset.uom_id.name} | {same_asset.uom_id.name} ) ")
                    same_asset.quantity = sum([data.quantity for data in job.asset_estimation_ids.filtered(lambda
                                                                                                             line: line.project_scope.id == asset.project_scope.id and line.section_name.id == asset.section_name.id and line.asset_category_id.id == asset.asset_category_id.id and line.asset_id.id == asset.asset_id.id)])
                    if same_asset.unit_price < asset.unit_price:
                        same_asset.unit_price = asset.unit_price
                    same_asset.onchange_quantity()
                else:
                    self.internal_asset_ids = [(0, 0, {
                        'project_scope': asset.project_scope.id,
                        'section_name': asset.section_name.id,
                        # 'variable_ref': asset.variable_ref.id,
                        'asset_category_id': asset.asset_category_id.id,
                        'type': asset.type,
                        'asset_id': asset.asset_id.id,
                        'description': asset.description,
                        'quantity': asset.quantity,
                        'uom_id': asset.uom_id.id,
                        'unit_price': asset.unit_price,
                    })]
                    same_asset = self.internal_asset_ids.filtered(lambda
                                                                      line: line.project_scope.id == asset.project_scope.id and line.section_name.id == asset.section_name.id and line.asset_category_id.id == asset.asset_category_id.id and line.asset_id.id == asset.asset_id.id)
                    if same_asset:
                        same_asset.quantity = sum([data.quantity for data in job.asset_estimation_ids.filtered(lambda
                                                                                                                   line: line.project_scope.id == same_asset.project_scope.id and line.section_name.id == same_asset.section_name.id and line.asset_category_id.id == same_asset.asset_category_id.id and line.asset_id.id == same_asset.asset_id.id)])
                        same_asset.onchange_quantity()

            for sub in job.subcon_estimation_ids.filtered(lambda line: len(line.variable_ref) <= 0):
                same_subcon = self.subcon_estimation_ids.filtered(lambda
                                                                      line: line.project_scope.id == sub.project_scope.id and line.section_name.id == sub.section_name.id and line.variable.id == sub.variable.id)
                if same_subcon:
                    if same_subcon.uom_id.id != sub.uom_id.id:
                        raise ValidationError(
                            f"{sub.subcon_id.name} Subcon line cannot merge different UOM ({sub.uom_id.name} | {same_subcon.uom_id.name} ) ")
                    same_subcon.quantity = sum([data.quantity for data in job.subcon_estimation_ids.filtered(lambda
                                                                                                                 line: line.project_scope.id == sub.project_scope.id and line.section_name.id == sub.section_name.id and line.variable.id == sub.variable.id)])
                    if same_subcon.unit_price < sub.unit_price:
                        same_subcon.unit_price = sub.unit_price
                    same_subcon.onchange_quantity()
                else:
                    self.subcon_estimation_ids = [(0, 0, {
                        'project_scope': sub.project_scope.id,
                        'section_name': sub.section_name.id,
                        # 'variable_ref': sub.variable_ref.id,
                        'variable': sub.variable.id,
                        'type': sub.type,
                        'description': sub.description,
                        'quantity': sub.quantity,
                        'uom_id': sub.uom_id.id,
                        'unit_price': sub.unit_price,
                    })]
                    same_subcon = self.subcon_estimation_ids.filtered(lambda
                                                                          line: line.project_scope.id == sub.project_scope.id and line.section_name.id == sub.section_name.id and line.variable.id == sub.variable.id)
                    if same_subcon:
                        same_subcon.quantity = sum([data.quantity for data in job.subcon_estimation_ids.filtered(lambda
                                                                                                                     line: line.project_scope.id == same_subcon.project_scope.id and line.section_name.id == same_subcon.section_name.id and line.variable.id == same_subcon.variable.id)])
                        same_subcon.onchange_quantity()

        elif not self.job_estimate_template:
            project = self.project_id
            if self.contract_category == 'main':
                self.project_scope_ids = [(6, 0, [])]
                self.section_ids = [(6, 0, [])]

                for scope in project.project_scope_ids:
                    self.project_scope_ids = [(0, 0, {
                        'project_scope': scope.project_scope.id,
                        'description': scope.description,
                    })]

                for section in project.project_section_ids:
                    self.section_ids = [(0, 0, {
                        'project_scope': section.project_scope.id,
                        'section_name': section.section.id,
                        'description': section.description,
                        'quantity': section.quantity,
                        'uom_id': section.uom_id.id,
                    })]

    @api.depends('total_job_estimate')
    def _said(self):
        for line in self:
            frac, whole = math.modf(round(line.total_job_estimate))
            amount = whole if line.company_currency_id.name == 'IDR' else line.total_job_estimate
            line.said = process_words(amount, line.company_currency_id.name, 'en')

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def getRoman(self, number):
        num = [1, 4, 5, 9, 10, 40, 50, 90,
               100, 400, 500, 900, 1000]
        sym = ["I", "IV", "V", "IX", "X", "XL",
               "L", "XC", "C", "CD", "D", "CM", "M"]
        i = 12
        result = ""

        while number:
            div = number // num[i]
            number %= num[i]

            while div:
                result += sym[i]
                div -= 1
            i -= 1
        return result

    def action_set_draft(self):
        for record in self:
            record.job_estimate_user_ids = [(5, 0, 0)]
            record.write({'state': 'draft',
                          'state_new': 'draft',
                          'approved_user_ids': False,
                          'approved_user': False,
                          })
            record.onchange_approving_matrix_lines()

    def action_export_job_estimate(self):
        for record in self:
            export_id = self.env['export.job.estimate'].create({'job_estimate_id': record.id})
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'Export to Excel',
                'res_model': 'export.job.estimate',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def action_job_estimate_revision(self, default=None):
        self.state = 'revised'
        self.state_new = 'revised'
        if self:
            self.ensure_one()
            self.is_revision_created = True
            if default is None:
                default = {}

            # Change name
            if self.is_revision_je:
                je_count = self.search(
                    [("main_revision_je_id", '=', self.main_revision_je_id.id), ('is_revision_je', '=', True)])
                split_name = self.name.split('/')
                if split_name[-1].startswith('R'):
                    split_name[-1] = 'R%d' % (len(je_count) + 1)
                else:
                    split_name.append('R%d' % (len(je_count) + 1))
                name = '/'.join(split_name)
            else:
                je_count = self.search([("main_revision_je_id", '=', self.id), ('is_revision_je', '=', True)])
                name = _('%s/R%d') % (self.name, len(je_count) + 1)

            # Setting the default values for the new record.
            if 'name' not in default:
                default['state'] = 'draft'
                default['revision_je_id'] = self.id
                default['is_revision_je'] = True
                if self.is_revision_je:
                    default['main_revision_je_id'] = self.main_revision_je_id.id
                else:
                    default['main_revision_je_id'] = self.id
                default['is_revision_created'] = False
                default['revision_count'] = 0

            new_project_id = self.copy(default=default)
            # Project Scope
            for scope_line in self.project_scope_ids:
                scope_line.copy({
                    'scope_id': new_project_id.id,
                })
            # Section
            for section_line in self.section_ids:
                section_line.copy({
                    'section_id': new_project_id.id,
                })
            # Variable
            for variable_line in self.variable_ids:
                variable_line.copy({
                    'variable_id': new_project_id.id,
                })
            # Material Est
            for material_line in self.material_estimation_ids:
                material_line.copy({
                    'material_id': new_project_id.id,
                })
            # Labour Est
            for labour_line in self.labour_estimation_ids:
                labour_line.copy({
                    'labour_id': new_project_id.id,
                })
            # Overhead Est
            for overhead_line in self.overhead_estimation_ids:
                overhead_line.copy({
                    'overhead_id': new_project_id.id,
                })
            # Equipment Est
            for equipment_line in self.equipment_estimation_ids:
                equipment_line.copy({
                    'equipment_id': new_project_id.id,
                })
            # Asset Est
            for asset_line in self.internal_asset_ids:
                asset_line.copy({
                    'asset_job_id': new_project_id.id,
                })
            # Subcon Est
            for subcon_line in self.subcon_estimation_ids:
                subcon_line.copy({
                    'subcon_id': new_project_id.id,
                })
            # Approval Matrix Line
            for approval_line in self.job_estimate_user_ids:
                approval_line.copy({
                    'job_estimate_approver_id': new_project_id.id,
                })

            new_project_id.is_rejected = False
            new_project_id.is_cancelled = False
            new_project_id.job_estimate_user_ids = [(5, 0, 0)]
            new_project_id.write({'state': 'draft',
                                  'state_new': 'draft',
                                  'approved_user_ids': False,
                                  'approved_user': False,
                                  })
            new_project_id.onchange_approving_matrix_lines()

            if name.startswith('BOQ'):
                new_project_id.name = name

            if name.startswith('BOQ/VO'):
                new_project_id.name = name

            if self.is_revision_je:
                new_project_id.revision_history_id = [(6, 0, self.main_revision_je_id.ids + je_count.ids)]
            else:
                new_project_id.revision_history_id = [(6, 0, self.ids)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'BOQ',
            'view_mode': 'form',
            'res_model': 'job.estimate',
            'res_id': new_project_id.id,
            'target': 'current'
        }

    def action_boq_revision(self, job, default=None):
        job.state = 'revised'
        job.state_new = 'revised'
        if job:
            job.ensure_one()
            job.is_revision_created = True
            if default is None:
                default = {}

            # Change name
            if job.is_revision_je:
                je_count = self.search(
                    [("main_revision_je_id", '=', job.main_revision_je_id.id), ('is_revision_je', '=', True)])
                split_name = job.name.split('/')
                if split_name[-1].startswith('R'):
                    split_name[-1] = 'R%d' % (len(je_count) + 1)
                else:
                    split_name.append('R%d' % (len(je_count) + 1))
                name = '/'.join(split_name)
            else:
                je_count = self.search([("main_revision_je_id", '=', job.id), ('is_revision_je', '=', True)])
                name = _('%s/R%d') % (job.name, len(je_count) + 1)

            # Setting the default values for the new record.
            if 'name' not in default:
                default['state'] = 'draft'
                default['revision_je_id'] = job.id
                default['is_revision_je'] = True
                if self.is_revision_je:
                    default['main_revision_je_id'] = job.main_revision_je_id.id
                else:
                    default['main_revision_je_id'] = job.id
                default['is_revision_created'] = False
                default['revision_count'] = 0

            new_project_id = job.copy(default=default)
            # Project Scope
            for scope_line in job.project_scope_ids:
                scope_line.copy({
                    'scope_id': new_project_id.id,
                })
            # Section
            for section_line in job.section_ids:
                section_line.copy({
                    'section_id': new_project_id.id,
                })
            # Variable
            for variable_line in job.variable_ids:
                variable_line.copy({
                    'variable_id': new_project_id.id,
                })
            # Material Est
            for material_line in job.material_estimation_ids:
                material_line.copy({
                    'material_id': new_project_id.id,
                })
            # Labour Est
            for labour_line in job.labour_estimation_ids:
                labour_line.copy({
                    'labour_id': new_project_id.id,
                })
            # Overhead Est
            for overhead_line in job.overhead_estimation_ids:
                overhead_line.copy({
                    'overhead_id': new_project_id.id,
                })
            # Equipment Est
            for equipment_line in job.equipment_estimation_ids:
                equipment_line.copy({
                    'equipment_id': new_project_id.id,
                })
            # Asset Est
            for asset_line in job.internal_asset_ids:
                asset_line.copy({
                    'asset_job_id': new_project_id.id,
                })
            # Subcon Est
            for subcon_line in job.subcon_estimation_ids:
                subcon_line.copy({
                    'subcon_id': new_project_id.id,
                })
            # Approval Matrix Line
            for approval_line in job.job_estimate_user_ids:
                approval_line.copy({
                    'job_estimate_approver_id': new_project_id.id,
                })

            new_project_id.is_rejected = False
            new_project_id.is_cancelled = False
            new_project_id.job_estimate_user_ids = [(5, 0, 0)]
            new_project_id.write({'state': 'draft',
                                  'state_new': 'draft',
                                  'approved_user_ids': False,
                                  'approved_user': False,
                                  })
            new_project_id.onchange_approving_matrix_lines()

            if name.startswith('BOQ'):
                new_project_id.name = name

            if name.startswith('BOQ/VO'):
                new_project_id.name = name

            if job.is_revision_je:
                new_project_id.revision_history_id = [(6, 0, job.main_revision_je_id.ids + je_count.ids)]
            else:
                new_project_id.revision_history_id = [(6, 0, job.ids)]

    def get_revision_count(self):
        if self:
            for rec in self:
                rec.revision_count = 0
                qc = self.env['job.estimate'].search([('revision_je_id', '=', rec.id)])
                rec.revision_count = len(qc.ids)

    def open_revision_tree(self):
        revision = self.env['job.estimate'].search([('revision_je_id', '=', self.id)])
        action = self.env.ref('equip3_construction_sales_operation.action_job_estimate_revision').read()[0]
        action['context'] = {
            'domain': [('id', 'in', revision.ids)]
        }
        action['domain'] = [('id', 'in', revision.ids)]
        return action

    @api.constrains('project_scope_ids')
    def _check_exist_project_scope1(self):
        for rec in self:
            exist_scope_list1 = []
            for line1 in rec.project_scope_ids:
                if line1.project_scope.id in exist_scope_list1:
                    raise ValidationError(_('The Project Scope "%s" already exists. Please change this Project Scope.' % (
                        (line1.project_scope.name))))
                exist_scope_list1.append(line1.project_scope.id)

    @api.onchange('project_scope_ids')
    def _check_exist_project_scope2(self):
        exist_scope_list2 = []
        for line2 in self.project_scope_ids:
            if line2.project_scope.id in exist_scope_list2:
                raise ValidationError(_('The Project Scope "%s" already exists. Please change this Project Scope.' % (
                    (line2.project_scope.name))))
            exist_scope_list2.append(line2.project_scope.id)

    @api.constrains('section_ids')
    def _check_exist_section1(self):
        exist_section_list3 = []
        for line3 in self.section_ids:
            same1 = str(line3.project_scope.id) + ' - ' + str(line3.section_name.id)
            if (same1 in exist_section_list3):
                raise ValidationError(
                    _('The Section "%s" already exists in project scope "%s". Please change this Section.' % (
                        (line3.section_name.name), (line3.project_scope.name))))
            exist_section_list3.append(same1)

    @api.onchange('section_ids')
    def _check_exist_section2(self):
        exist_section_list4 = []
        for line4 in self.section_ids:
            same2 = str(line4.project_scope.id) + ' - ' + str(line4.section_name.id)
            if (same2 in exist_section_list4):
                raise ValidationError(
                    _('The Section "%s" already exists in project scope "%s". Please change this Section.' % (
                        (line4.section_name.name), (line4.project_scope.name))))
            exist_section_list4.append(same2)

    @api.constrains('variable_ids')
    def _check_exist_variable(self):
        exist_variable_list = []
        for line in self.variable_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.variable_name.id)
            if (same in exist_variable_list):
                raise ValidationError(
                    _('The Variable "%s" already exists in project scope "%s" and section "%s". Please change this Variable.' % (
                        (line.variable_name.name), (line.project_scope.name), (line.section_name.name))))
            exist_variable_list.append(same)

    @api.onchange('variable_ids')
    def _check_exist_variable2(self):
        exist_variable_list = []
        for line in self.variable_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.variable_name.id)
            if (same in exist_variable_list):
                raise ValidationError(
                    _('The Variable "%s" already exists in project scope "%s" and section "%s". Please change this Variable.' % (
                        (line.variable_name.name), (line.project_scope.name), (line.section_name.name))))
            exist_variable_list.append(same)

    @api.onchange('material_estimation_ids')
    def _check_exist_group_of_product_material(self):
        exist_section_group_list_material = []
        for line in self.material_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_material):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_material.append(same)

    @api.constrains('material_estimation_ids')
    def _check_exist_group_of_product_material_2(self):
        exist_section_group_list_material = []
        for line in self.material_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_material):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_material.append(same)

    @api.onchange('labour_estimation_ids')
    def _check_exist_group_of_product_labour(self):
        exist_section_group_list_labour1 = []
        for line in self.labour_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_labour1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_labour1.append(same)

    @api.constrains('labour_estimation_ids')
    def _check_exist_group_of_product_labour_2(self):
        exist_section_group_list_labour1 = []
        for line in self.labour_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_labour1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_labour1.append(same)

    @api.onchange('overhead_estimation_ids')
    def _check_exist_group_of_product_overhead(self):
        exist_section_group_list_overhead = []
        for line in self.overhead_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_overhead):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_overhead.append(same)

    @api.constrains('overhead_estimation_ids')
    def _check_exist_group_of_product_overhead_2(self):
        exist_section_group_list_overhead = []
        for line in self.overhead_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_overhead):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_overhead.append(same)

    @api.onchange('equipment_estimation_ids')
    def _check_exist_group_of_product_equipment(self):
        exist_section_group_list_equipment1 = []
        for line in self.equipment_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_equipment1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_equipment1.append(same)

    @api.constrains('equipment_estimation_ids')
    def _check_exist_group_of_product_equipment_2(self):
        exist_section_group_list_equipment1 = []
        for line in self.equipment_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.product_id.id)
            if (same in exist_section_group_list_equipment1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                        (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_equipment1.append(same)

    @api.onchange('internal_asset_ids')
    def _check_exist_group_of_product_asset(self):
        exist_section_group_list_asset1 = []
        for line in self.internal_asset_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.asset_id.id)
            if (same in exist_section_group_list_asset1):
                raise ValidationError(
                    _('The Asset "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Asset selected.' % (
                        (line.asset_id.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_group_list_asset1.append(same)

    @api.constrains('internal_asset_ids')
    def _check_exist_group_of_product_asset_2(self):
        exist_section_group_list_asset1 = []
        for line in self.internal_asset_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.asset_id.id)
            if (same in exist_section_group_list_asset1):
                raise ValidationError(
                    _('The Asset "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Asset selected.' % (
                        (line.asset_id.name), (line.project_scope.name), (line.section_name.name))))

    @api.onchange('subcon_estimation_ids')
    def _check_exist_subcon(self):
        exist_section_subcon_list_subcon = []
        for line in self.subcon_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.variable.id)
            if (same in exist_section_subcon_list_subcon):
                raise ValidationError(
                    _('The Job Subcon "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Job Subcon selected.' % (
                        (line.variable.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_subcon_list_subcon.append(same)

    @api.constrains('subcon_estimation_ids')
    def _check_exist_subcon_2(self):
        exist_section_subcon_list_subcon = []
        for line in self.subcon_estimation_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.variable.id)
            if (same in exist_section_subcon_list_subcon):
                raise ValidationError(
                    _('The Job Subcon "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Job Subcon selected.' % (
                        (line.variable.name), (line.project_scope.name), (line.section_name.name))))
            exist_section_subcon_list_subcon.append(same)

    @api.depends('project_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_job_estimate_approval_matrix = IrConfigParam.get_param('is_job_estimate_approval_matrix')
        for record in self:
            record.is_job_estimate_approval_matrix = is_job_estimate_approval_matrix

    @api.depends('project_id', 'branch_id', 'company_id', 'total_job_estimate', 'department_type', 'start_date',
                 'end_date', 'analytic_idz')
    def _compute_approving_customer_matrix(self):
        total_boq = 0
        for record in self:
            record.approving_matrix_job_id = False
            total_boq = record.total_job_estimate
            if record.is_job_estimate_approval_matrix:
                if record.department_type == 'project':
                    if total_boq >= 0:
                        total_addendum = total_boq
                        approving_matrix_job_id = self.env['approval.matrix.job.estimates'].search([
                            ('company_id', '=', record.company_id.id),
                            ('branch_id', '=', record.branch_id.id),
                            ('project_id', 'in', (record.project_id.id)),
                            ('department_type', '=', 'project'),
                            ('type_boq', '=', 'addendum'),
                            ('set_default', '=', False),
                            ('minimum_amt', '<=', total_addendum),
                            ('maximum_amt', '>=', total_addendum)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.job.estimates'].search([
                            ('company_id', '=', record.company_id.id),
                            ('branch_id', '=', record.branch_id.id),
                            ('department_type', '=', 'project'),
                            ('type_boq', '=', 'addendum'),
                            ('set_default', '=', True),
                            ('minimum_amt', '<=', total_addendum),
                            ('maximum_amt', '>=', total_addendum)], limit=1)

                    else:
                        total_dedendum = total_boq * (-1)
                        approving_matrix_job_id = self.env['approval.matrix.job.estimates'].search([
                            ('company_id', '=', record.company_id.id),
                            ('branch_id', '=', record.branch_id.id),
                            ('project_id', 'in', (record.project_id.id)),
                            ('department_type', '=', 'project'),
                            ('type_boq', '=', 'dedendum'),
                            ('set_default', '=', False),
                            ('minimum_amt', '<=', total_dedendum),
                            ('maximum_amt', '>=', total_dedendum)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.job.estimates'].search([
                            ('company_id', '=', record.company_id.id),
                            ('branch_id', '=', record.branch_id.id),
                            ('department_type', '=', 'project'),
                            ('type_boq', '=', 'dedendum'),
                            ('set_default', '=', True),
                            ('minimum_amt', '<=', total_dedendum),
                            ('maximum_amt', '>=', total_dedendum)], limit=1)

                else:
                    if total_boq >= 0:
                        total_addendum = total_boq
                        approving_matrix_job_id = self.env['approval.matrix.job.estimates'].search([
                            ('company_id', '=', record.company_id.id),
                            ('branch_id', '=', record.branch_id.id),
                            ('project_id', 'in', (record.project_id.id)),
                            ('department_type', '=', 'department'),
                            ('type_boq', '=', 'addendum'),
                            ('set_default', '=', False),
                            ('minimum_amt', '<=', total_addendum),
                            ('maximum_amt', '>=', total_addendum)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.job.estimates'].search([
                            ('company_id', '=', record.company_id.id),
                            ('branch_id', '=', record.branch_id.id),
                            ('department_type', '=', 'department'),
                            ('type_boq', '=', 'addendum'),
                            ('set_default', '=', True),
                            ('minimum_amt', '<=', total_addendum),
                            ('maximum_amt', '>=', total_addendum)], limit=1)
                    else:
                        total_dedendum = total_boq * (-1)
                        approving_matrix_job_id = self.env['approval.matrix.job.estimates'].search([
                            ('company_id', '=', record.company_id.id),
                            ('branch_id', '=', record.branch_id.id),
                            ('project_id', 'in', (record.project_id.id)),
                            ('department_type', '=', 'department'),
                            ('type_boq', '=', 'dedendum'),
                            ('set_default', '=', False),
                            ('minimum_amt', '<=', total_dedendum),
                            ('maximum_amt', '>=', total_dedendum)], limit=1)

                        approving_matrix_default = self.env['approval.matrix.job.estimates'].search([
                            ('company_id', '=', record.company_id.id),
                            ('branch_id', '=', record.branch_id.id),
                            ('department_type', '=', 'department'),
                            ('type_boq', '=', 'dedendum'),
                            ('set_default', '=', True),
                            ('minimum_amt', '<=', total_dedendum),
                            ('maximum_amt', '>=', total_dedendum)], limit=1)

                if approving_matrix_job_id:
                    record.approving_matrix_job_id = approving_matrix_job_id and approving_matrix_job_id.id or False
                else:
                    if approving_matrix_default:
                        record.approving_matrix_job_id = approving_matrix_default and approving_matrix_default.id or False

    @api.onchange('project_id', 'approving_matrix_job_id', 'total_job_estimate', 'start_date', 'end_date',
                  'analytic_idz')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project_id:
                app_list = []
                if record.state_new == 'draft' and record.is_job_estimate_approval_matrix:
                    record.job_estimate_user_ids = []
                    for rec in record.approving_matrix_job_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.job_estimate_user_ids = data

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.job_estimate_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.job_estimate_user_ids)
                if app < a:
                    for line in record.job_estimate_user_ids[app]:
                        if current_user in line.user_ids:
                            record.is_approver = True
                        else:
                            record.is_approver = False
                else:
                    record.is_approver = False
            else:
                record.is_approver = False

    def action_request_for_approving(self):
        for record in self:
            record.action_request_for_approving_sale_matrix()

    def action_request_for_approving_sale_matrix(self):
        for record in self:
            if len(record.project_scope_ids) == 0:
                raise ValidationError(
                    _('The Project Scope table is empty. Please add at least 1 item to the Project Scope table.'))

            if len(record.section_ids) == 0:
                raise ValidationError(
                    _('The Section table is empty. Please add at least 1 item to the Section table.'))

            if len(record.job_estimate_user_ids) == 0:
                raise ValidationError(
                    _("There's no BOQ approval matrix for this project with amount of the total BOQ listed. You have to create it first."))

            if len(record.material_estimation_ids) == len(record.labour_estimation_ids) == len(
                    record.overhead_estimation_ids) == len(record.internal_asset_ids) == len(
                record.equipment_estimation_ids) == len(record.subcon_estimation_ids) == 0:
                raise ValidationError(
                    _('The Estimation tables are empty. Please add at least 1 product for estimation.'))

            if len(record.material_estimation_ids) > 0:
                for material in record.material_estimation_ids:
                    if material.unit_price == 0:
                        raise ValidationError(
                            _('In tab material estimation, the unit price of product "%s" should be greater than 0.' % (
                                (material.product_id.name))))
            if len(record.labour_estimation_ids) > 0:
                for labour in record.labour_estimation_ids:
                    if labour.unit_price == 0:
                        raise ValidationError(
                            _('In tab labour estimation, the unit price of product "%s" should be greater than 0.' % (
                                (labour.product_id.name))))
            if len(record.overhead_estimation_ids) > 0:
                for overhead in record.overhead_estimation_ids:
                    if overhead.unit_price == 0:
                        raise ValidationError(
                            _('In tab overhead estimation, the unit price of product "%s" should be greater than 0.' % (
                                (overhead.product_id.name))))
            if len(record.equipment_estimation_ids) > 0:
                for equipment in record.equipment_estimation_ids:
                    if equipment.unit_price == 0:
                        raise ValidationError(
                            _('In tab equipment estimation, the unit price of product "%s" should be greater than 0.' % (
                                (equipment.product_id.name))))
            if len(record.internal_asset_ids) > 0:
                for internal_asset in record.internal_asset_ids:
                    if internal_asset.unit_price == 0:
                        raise ValidationError(
                            _('In tab internal asset estimation, the unit price of asset "%s" should be greater than 0.' % (
                                (internal_asset.asset_id.name))))
            if len(record.subcon_estimation_ids) > 0:
                for subcon in record.subcon_estimation_ids:
                    if subcon.unit_price == 0:
                        raise ValidationError(
                            _('In tab subcon estimation, the unit price of job subcon "%s" should be greater than 0.' % (
                                (subcon.variable.name))))

            action_id = self.env.ref('bi_job_cost_estimate_customer.action_job_estimate')
            template_id = self.env.ref(
                'equip3_construction_sales_operation.email_template_internal_job_estimate_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=job.estimate'
            if record.job_estimate_user_ids and len(record.job_estimate_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.job_estimate_user_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'date': date.today(),
                        'url': url,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
            else:
                approver = record.job_estimate_user_ids[0].user_ids[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'date': date.today(),
                    'url': url,
                }
                template_id.with_context(ctx).send_mail(record.id, True)

            record.write({'employee_id': self.env.user.id,
                          'state': 'to_approve',
                          'state_new': 'to_approve'
                          })

            for line in record.job_estimate_user_ids:
                line.write({'approver_state': 'draft'})

    def action_confirm_approving_matrix(self):
        if len(self.project_scope_ids) == 0:
            raise ValidationError(
                _('The Project Scope table is empty. Please add at least 1 item to the Project Scope table.'))
        if len(self.section_ids) == 0:
            raise ValidationError(
                _('The Section table is empty. Please add at least 1 item to the Section table.'))

        for tabs in self:
            if len(tabs.material_estimation_ids) == len(tabs.labour_estimation_ids) == len(
                    tabs.overhead_estimation_ids) == len(tabs.internal_asset_ids) == len(
                tabs.equipment_estimation_ids) == len(tabs.subcon_estimation_ids) == 0:
                raise ValidationError(
                    _('The Estimation tables are empty. Please add at least 1 product for estimation.'))

        sequence_matrix = [data.name for data in self.job_estimate_user_ids]
        sequence_approval = [data.name for data in self.job_estimate_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.job_estimate_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)

        for record in self:
            action_id = self.env.ref('bi_job_cost_estimate_customer.action_job_estimate')
            template_app = self.env.ref('equip3_construction_sales_operation.email_template_job_estimate_approved')
            template_id = self.env.ref(
                'equip3_construction_sales_operation.email_template_reminder_for_job_estimate_approval')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=job.estimate'

            current_user = self.env.uid
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

            if self.env.user not in record.approved_user_ids:
                if record.is_approver:
                    for line in record.job_estimate_user_ids:
                        for user in line.user_ids:
                            if current_user == user.user_ids.id:
                                line.timestamp = fields.Datetime.now()
                                record.approved_user_ids = [(4, current_user)]
                                var = len(line.approved_employee_ids) + 1
                                if line.minimum_approver <= var:
                                    line.approver_state = 'approved'
                                    string_approval = []
                                    string_approval.append(line.approval_status)
                                    if line.approval_status:
                                        string_approval.append(f"{self.env.user.name}:Approved")
                                        line.approval_status = "\n".join(string_approval)
                                        string_timestammp = [line.approved_time]
                                        string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                        line.approved_time = "\n".join(string_timestammp)
                                    else:
                                        line.approval_status = f"{self.env.user.name}:Approved"
                                        line.approved_time = f"{self.env.user.name}:{dateformat}"
                                    line.is_approve = True
                                else:
                                    line.approver_state = 'pending'
                                    string_approval = []
                                    string_approval.append(line.approval_status)
                                    if line.approval_status:
                                        string_approval.append(f"{self.env.user.name}:Approved")
                                        line.approval_status = "\n".join(string_approval)
                                        string_timestammp = [line.approved_time]
                                        string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                        line.approved_time = "\n".join(string_timestammp)
                                    else:
                                        line.approval_status = f"{self.env.user.name}:Approved"
                                        line.approved_time = f"{self.env.user.name}:{dateformat}"
                                line.approved_employee_ids = [(4, current_user)]

                    matrix_line = sorted(record.job_estimate_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': record.employee_id.email,
                            'date': date.today(),
                            'url': url,
                        }
                        template_app.sudo().with_context(ctx).send_mail(record.id, True)
                        record.approve_job_estimate()

                    else:
                        record.last_approved = self.env.user.id
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        for approving_matrix_line_user in matrix_line[0].user_ids:
                            ctx = {
                                'email_from': self.env.user.company_id.email,
                                'email_to': approving_matrix_line_user.partner_id.email,
                                'approver_name': approving_matrix_line_user.name,
                                'date': date.today(),
                                'submitter': record.last_approved.name,
                                'url': url,
                            }
                            template_id.sudo().with_context(ctx).send_mail(record.id, True)

                else:
                    raise ValidationError(_(
                        'You are not allowed to perform this action!'
                    ))
            else:
                raise ValidationError(_(
                    'Already approved!'
                ))

    def action_reject_approval(self):
        for record in self:
            action_id = self.env.ref('bi_job_cost_estimate_customer.action_job_estimate')
            template_rej = self.env.ref('equip3_construction_sales_operation.email_template_job_estimate_rejected')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=job.estimate'
            for user in record.job_estimate_user_ids:
                for check_user in user.user_ids:
                    now = datetime.now(timezone(self.env.user.tz))
                    dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                    if self.env.uid == check_user.id:
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'reject'
                        string_approval = []
                        string_approval.append(user.approval_status)
                        if user.approval_status:
                            string_approval.append(f"{self.env.user.name}:Rejected")
                            user.approval_status = "\n".join(string_approval)
                            string_timestammp = [user.approved_time]
                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                            user.approved_time = "\n".join(string_timestammp)
                        else:
                            user.approval_status = f"{self.env.user.name}:Rejected"
                            user.approved_time = f"{self.env.user.name}:{dateformat}"

            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': record.employee_id.email,
                'date': date.today(),
                'url': url,
            }
            template_rej.sudo().with_context(ctx).send_mail(record.id, True)
            record.write({'state': 'rejected',
                          'state_new': 'rejected',
                          'state_1': 'rejected',
                          'is_rejected': True})

    def action_reject_approving_matrix(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.job.reject.const',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.depends('project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            scope_ids = []
            if rec.project_scope_ids:
                for line in rec.project_scope_ids:
                    if line.project_scope:
                        scope_ids.append(line.project_scope.id)
                rec.project_scope_computed = [(6, 0, scope_ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]

    def report_data2array(self, data_dict):
        def traverse(data_dict, depth=0):
            data_arr = []
            blank_data = {}
            for k, v in data_dict.items():
                blank_data = {x: '' for x, _ in v.items()}
                v['style'] = depth
                data_arr += [v]
                data_arr += traverse(v['children'], depth + 1)
                if v.get('_subtotal', False):
                    v['_subtotal']['style'] = 3
                    data_arr += [v['_subtotal']]

                if depth == 0 and len(data_arr) > 0:
                    blank_data['style'] = 1
                    data_arr += [blank_data]

            return data_arr

        return traverse(data_dict)

    def get_report_data(self, print_level_option):
        scope_sect_prod_dict = {}
        job_estimate_id = self
        cost_sheet_id = self.cost_sheet_ref
        contract_category = job_estimate_id.contract_category

        char_inc = 'A'
        for i, item in enumerate(job_estimate_id.project_scope_ids):
            scope_sect_prod_dict[item.project_scope.name] = {
                'field': 'scope',
                'no': chr(ord(char_inc) + i),
                'name': item.project_scope.name,
                'qty': '',
                'contractor': '',
                'time': '',
                'coefficient': '',
                'uom': '',
                'unit_price': '',
                'total': '',
                'children': {},
                'counter': 1,
                '_subtotal': {
                    'field': 'scope',
                    'no': '',
                    'name': 'Subtotal ' + job_estimate_id.getRoman(i + 1),
                    'qty': '',
                    'contractor': '',
                    'time': '',
                    'coefficient': '',
                    'uom': '',
                    'unit_price': '',
                    'total': item.subtotal,
                    'children': {},
                    'counter': 1,
                },
            }
        
        for i, item in enumerate(job_estimate_id.section_ids):
            if scope_sect_prod_dict.get(item.project_scope.name, False):
                scope_sect_prod_dict[item.project_scope.name]['children'][item.section_name.name] = {
                    'field': 'section',
                    'no': scope_sect_prod_dict[item.project_scope.name]['counter'],
                    'name': item.section_name.name,
                    'qty': item.quantity,
                    'contractor': '',
                    'time': '',
                    'coefficient': '',
                    'uom': item.uom_id.name,
                    'unit_price': '',
                    'total': item.subtotal,
                    'children': {},
                    'counter': 'a',
                }
                scope_sect_prod_dict[item.project_scope.name]['counter'] += 1

        if print_level_option == '3_level':
            for field, key in ESTIMATES_DICT.items():
                item_dict = {}

                for x in job_estimate_id[field]:
                    item_key = str(x.project_scope.name) + '_' + str(x.section_name.name) + '_' + str(x[key].name)
                    if item_dict.get(item_key, False):
                        item_dict[item_key]['uom'] = x.uom_id.name
                        item_dict[item_key]['unit_price'] = x.unit_price
                        item_dict[item_key]['total'] = x.subtotal
                    else:
                        item_dict[item_key] = {
                            'field': field,
                            'name': x[key].name,
                            'qty': x.quantity_after if field != 'labour_estimation_ids' else 0,
                            'contractor': x.contractors_after if field == 'labour_estimation_ids' else 0,
                            'time': x.time_after if field == 'labour_estimation_ids' else 0,
                            'coefficient': x.coefficient,
                            'uom': x.uom_id.name,
                            'unit_price': x.unit_price,
                            'total': x.subtotal,
                            'children': {},
                        }

                for key, item in item_dict.items():
                    key_arr = key.split('_')
                    scope = key_arr[0]
                    section = key_arr[1]
                    product = key_arr[2]

                    try:
                        char_inc = scope_sect_prod_dict[scope]['children'][section]['counter']
                        scope_sect_prod_dict[scope]['children'][section]['children'][product] = {
                            'field': item['field'],
                            'no': char_inc,
                            'name': product,
                            'qty': item['qty'],
                            'contractor': item['contractor'],
                            'time': item['time'],
                            'coefficient': item['coefficient'],
                            'uom': item['uom'],
                            'unit_price': item['unit_price'],
                            'total': item['total'],
                            'children': {},
                        }
                        scope_sect_prod_dict[scope]['children'][section]['counter'] = chr(ord(char_inc) + 1)

                    except Exception as e:
                        continue

        return scope_sect_prod_dict


class JobEstimateApproverUser(models.Model):
    _name = 'job.estimate.approver.user'
    _description = 'Job Estimate Approver User'

    job_estimate_approver_id = fields.Many2one('job.estimate', string="BOQ")
    name = fields.Integer('Sequence', compute="fetch_sl_no", store=True)
    user_ids = fields.Many2many('res.users', string="Approvers")
    # , domain=lambda self: [('id', 'in', self.env.branches.ids)])
    approved_employee_ids = fields.Many2many('res.users', 'job_estimate_app_emp_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('reject', 'Rejected')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'job_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    # parent status
    state = fields.Selection(related='job_estimate_approver_id.state_new', string='Parent Status')

    @api.depends('job_estimate_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.job_estimate_approver_id.job_estimate_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.user_ids) < rec.minimum_approver and rec.job_estimate_approver_id.state_new == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.job_estimate_approver_id.state_new == 'draft':
                rec.matrix_user_ids = rec.user_ids

    @api.onchange('name', 'user_ids')
    def _onchange_user_ids(self):
        for rec in self:
            return {'domain': {'user_ids': [('id', 'in', rec.env.ref("sales_team.group_sale_manager").users.ids)]}}


class MaterialEstimateInherits(models.Model):
    _name = 'material.estimate'
    _description = 'BOQ Material Estimate'
    _order = 'sequence'
    _check_company_auto = True

    material_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment'),
        ('asset', 'Asset'),
    ], string="Type", default='material', readonly=1)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True,
                                       domain="[('company_id','=',parent.company_id)]")
    analytic_idz = fields.Many2many(related="material_id.analytic_idz", string='Analytic Group')
    subtotal = fields.Float('Subtotal', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='material_id.company_id', string='Company', readonly=True)
    description = fields.Text('Description', required=True)
    contract_category = fields.Selection(string="Contract Category", related='material_id.contract_category')
    quantity = fields.Float('Quantity', default=1.0)
    coefficient = fields.Float('Coeff', default=1.0)
    discount = fields.Float('Discount (%)', default=0.0)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    unit_price = fields.Float('Unit Price', default=0.0)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    project_id = fields.Many2one(related='material_id.project_id', string='Project')
    prev_uom_id = fields.Many2one('uom.uom', 'Prev Uom')

    @api.onchange('coefficient', 'product_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.contract_category != 'main': return
            if rec.product_id:
                section_id = rec.material_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        for line in self:
            if line.product_id:
                uom_id = line.product_id.uom_id
                if line.prev_uom_id:
                    uom_id = line.prev_uom_id
                elif line._origin:
                    uom_id = line._origin.uom_id
                
                line.quantity = uom_id._compute_quantity(line.quantity, line.uom_id)
                line.prev_uom_id = line.uom_id

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'product')]}
            }

    @api.depends('material_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.material_id.section_ids:
                    for line in rec.material_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = False
            self.group_of_product = False

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.material_id.project_id:
            raise ValidationError(_("Select the Project first"))
        if not self.material_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })

    @api.depends('material_id.material_estimation_ids', 'material_id.material_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.material_id.material_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.contract_category == 'main':
                if line.quantity <= 0:
                    raise ValidationError('Quantity should be greater than 0.')
                else:
                    price = (line.quantity * line.unit_price)
                    line.subtotal = price

class UomUomInheritsOrder(models.Model):
    _inherit = 'uom.uom'
    _order = 'id desc'


class LabourEstimateInherits(models.Model):
    _name = 'labour.estimate'
    _description = 'BOQ Labour Estimate'
    _order = 'sequence'
    _check_company_auto = True

    labour_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment'),
        ('asset', 'Asset'),
    ], string="Type", default='labour', readonly=1)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True,
                                       domain="[('company_id','=',parent.company_id)]")
    analytic_idz = fields.Many2many(related="labour_id.analytic_idz", string='Analytic Group')
    subtotal = fields.Float('Subtotal', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='labour_id.company_id', string='Company', readonly=True)
    description = fields.Text('Description', required=False)
    contract_category = fields.Selection(string="Contract Category", related='labour_id.contract_category')
    quantity = fields.Float('Quantity', default=1.0)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    unit_price = fields.Float('Unit Price', default=0.0, required=True)
    contractors = fields.Integer('Contractors', default=1.0, required=True)
    time = fields.Float('Time', default=1.0, required=True)
    coefficient = fields.Float('Coeff', default=1.0)
    discount = fields.Float('Discount (%)', default=0.0)
    hours = fields.Float('Hours')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    project_id = fields.Many2one(related='labour_id.project_id', string='Project')
    prev_uom_id = fields.Many2one('uom.uom', 'Prev Uom')

    @api.onchange('coefficient', 'product_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.contract_category != 'main': return
            if rec.product_id:
                section_id = rec.labour_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.time = rec.coefficient * s.quantity

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        for line in self:
            if line.product_id:
                uom_id = line.product_id.uom_id
                if line.prev_uom_id:
                    uom_id = line.prev_uom_id
                elif line._origin:
                    uom_id = line._origin.uom_id
                
                line.quantity = uom_id._compute_quantity(line.quantity, line.uom_id)
                line.prev_uom_id = line.uom_id
                
    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', 'in', ['product', 'service'])]}
            }

    @api.depends('labour_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.labour_id.section_ids:
                    for line in rec.labour_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.contractors = 1.0
            self.time = 1.0
            self.uom_id = self.product_id.uom_id.id
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.contractors = 1.0
            self.time = 1.0
            self.description = False
            self.uom_id = False
            self.unit_price = False
            self.group_of_product = False

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.labour_id.project_id:
            raise ValidationError(_("Select the Project first"))
        if not self.labour_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })

    @api.depends('labour_id.labour_estimation_ids', 'labour_id.labour_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.labour_id.labour_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('contract_category', 'quantity', 'unit_price', 'contractors', 'time')
    def onchange_quantity(self):
        quantity = 0.0
        price = 0.0
        for line in self:
            if line.contract_category == 'main':
                if line.contractors <= 0:
                    raise ValidationError('Contractors should be greater than 0.')
                elif line.time <= 0:
                    raise ValidationError('Time should be greater than 0.')
                else:
                    quantity = (line.contractors * line.time)
                    line.quantity = quantity
                    price = (quantity * line.unit_price)
                    line.subtotal = price


class OverheadEstimateInherits(models.Model):
    _name = 'overhead.estimate'
    _description = 'BOQ Overhead Estimate'
    _order = 'sequence'
    _check_company_auto = True

    overhead_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment'),
        ('asset', 'Asset'),
    ], string="Type", default='overhead', readonly=1)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True,
                                       domain="[('company_id','=',parent.company_id)]")
    description = fields.Text(string="Description", required=True)
    analytic_idz = fields.Many2many(related="overhead_id.analytic_idz", string='Analytic Group')
    subtotal = fields.Float('Subtotal', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='overhead_id.company_id', string='Company', readonly=True)
    contract_category = fields.Selection(string="Contract Category", related='overhead_id.contract_category')
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    quantity = fields.Float('Quantity', default=1.0)
    coefficient = fields.Float('Coeff', default=1.0)
    unit_price = fields.Float('Unit Price', defaut=0.0)
    discount = fields.Float('Discount (%)', default=0.0)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    project_id = fields.Many2one(related='overhead_id.project_id', string='Project')
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Category', required=False)
    prev_uom_id = fields.Many2one('uom.uom', 'Prev Uom')

    @api.onchange('coefficient', 'product_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.contract_category != 'main': return
            if rec.product_id:
                section_id = rec.overhead_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        for line in self:
            if line.product_id:
                uom_id = line.product_id.uom_id
                if line.prev_uom_id:
                    uom_id = line.prev_uom_id
                elif line._origin:
                    uom_id = line._origin.uom_id
                
                line.quantity = uom_id._compute_quantity(line.quantity, line.uom_id)
                line.prev_uom_id = line.uom_id

    @api.onchange('overhead_catagory', 'group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            if rec.overhead_catagory in ('product', 'fuel'):
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'product')]}
                }
            else:
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'consu')]}
                }

    @api.depends('overhead_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.overhead_id.section_ids:
                    for line in rec.overhead_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = False
            self.group_of_product = False

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.overhead_id.project_id:
            raise ValidationError(_("Select the Project first"))
        if not self.overhead_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'overhead_catagory': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'overhead_catagory': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'overhead_catagory': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'overhead_catagory': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'overhead_catagory': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'overhead_catagory': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('overhead_catagory')
    def _onchange_overhead_catagory_handling(self):
        if self._origin.overhead_catagory:
            if self._origin.overhead_catagory != self.overhead_catagory:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })

    @api.depends('overhead_id.overhead_estimation_ids', 'overhead_id.overhead_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.overhead_id.overhead_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.contract_category == 'main':
                if line.quantity <= 0:
                    raise ValidationError('Quantity should be greater than 0.')
                else:
                    price = (line.quantity * line.unit_price)
                    line.subtotal = price


class SubconEstimate(models.Model):
    _name = "subcon.estimate"
    _order = 'sequence'
    _check_company_auto = True

    sequence = fields.Integer(string="sequence", default=0)
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    subcon_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment'),
        ('asset', 'Asset'),
    ], string="Type", default='subcon', readonly=1)
    company_id = fields.Many2one(related='subcon_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    contract_category = fields.Selection(string="Contract Category", related='subcon_id.contract_category')
    quantity = fields.Float('Quantity', default=1.0)
    coefficient = fields.Float('Coeff', default=1.0)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure', required='1')
    unit_price = fields.Float('Unit Price', default=0.0)
    discount = fields.Float('Discount (%)', default=0.0)
    analytic_idz = fields.Many2many(related="subcon_id.analytic_idz", string='Analytic Group')
    subtotal = fields.Float('Subtotal', readonly=True)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    variable = fields.Many2one('variable.template', string='Job Subcon',
                               domain="[('variable_subcon', '=', True), ('company_id', '=', parent.company_id)]",
                               check_company=True, ondelete='restrict', required=True)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    project_id = fields.Many2one(related='subcon_id.project_id', string='Project')
    prev_uom_id = fields.Many2one('uom.uom', 'Prev Uom')

    @api.onchange('coefficient', 'variable')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.contract_category != 'main': return
            if rec.variable:
                section_id = rec.subcon_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        for line in self:
            if line.variable:
                uom_id = line._origin.uom_id if line._origin else False
                if line.prev_uom_id:
                    uom_id = line.prev_uom_id
                elif line._origin:
                    uom_id = line._origin.uom_id
                
                if uom_id:
                    line.quantity = uom_id._compute_quantity(line.quantity, line.uom_id)
                    line.prev_uom_id = line.uom_id

    @api.onchange('variable')
    def onchange_variable(self):
        if self.variable:
            self.uom_id = self.variable.variable_uom.id
            self.quantity = 1.0
            self.unit_price = self.variable.total_variable
            self.description = self.variable.name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = False

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.subcon_id.project_id:
            raise ValidationError(_("Select the Project First"))
        if not self.subcon_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'variable': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'variable': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'variable': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'variable': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'variable': False,
                })
        else:
            self.update({
                'variable': False,
            })

    @api.depends('subcon_id.subcon_estimation_ids', 'subcon_id.subcon_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.subcon_id.subcon_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.contract_category == 'main':
                if line.quantity <= 0:
                    raise ValidationError('Quantity should be greater than 0.')
                else:
                    price = (line.quantity * line.unit_price)
                    line.subtotal = price

    @api.depends('subcon_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.subcon_id.section_ids:
                    for line in rec.subcon_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]


class InternalAssets(models.Model):
    _name = 'internal.assets'
    _description = "Assets"
    _order = 'sequence'

    asset_job_id = fields.Many2one('job.estimate', string='BOQ')
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment'),
        ('asset', 'Asset'),
    ], string="Type", default='asset', readonly=1)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    project_scope_line_id = fields.Many2one('project.scope.line', string='Project Scope')
    variable_id = fields.Many2one('variable.template', string='Variable')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category', required=True)
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    analytic_idz = fields.Many2many(related="asset_job_id.analytic_idz", string='Analytic Group')
    quantity = fields.Float('Quantity', default=1.0, required=True)
    coefficient = fields.Float('Coeff', default=1.0)
    description = fields.Text(string="Description", required=True)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure', required=True)
    unit_price = fields.Float(string='Unit Price', default=0.00, required=True)
    subtotal = fields.Float(string='Subtotal', default=0.00)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    project_id = fields.Many2one(related='asset_job_id.project_id', string='Project')
    contract_category = fields.Selection(string="Contract Category", related='asset_job_id.contract_category')
    company_id = fields.Many2one(related='asset_job_id.company_id', string='Company', readonly=True)
    discount = fields.Float('Discount (%)', default=0.0)
    prev_uom_id = fields.Many2one('uom.uom', 'Prev Uom')

    @api.onchange('coefficient', 'asset_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.contract_category != 'main': return
            if rec.asset_id:
                section_id = rec.asset_job_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        for line in self:
            if line.asset_id:
                uom_id = line._origin.uom_id if line._origin else False
                if line.prev_uom_id:
                    uom_id = line.prev_uom_id
                elif line._origin:
                    uom_id = line._origin.uom_id
                
                if uom_id:
                    line.quantity = uom_id._compute_quantity(line.quantity, line.uom_id)
                    line.prev_uom_id = line.uom_id

    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id:
            self.quantity = 1.0
            self.description = self.asset_id.display_name
        else:
            self.quantity = 1.0
            self.description = False

    @api.depends('asset_job_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.asset_job_id.section_ids:
                    for line in rec.asset_job_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('asset_job_id.internal_asset_ids', 'asset_job_id.internal_asset_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.asset_job_id.internal_asset_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'asset_id': False,
                    'asset_category_id': False,
                })
        else:
            self.update({
                'asset_id': False,
                'asset_category_id': False,
            })

    @api.onchange('asset_category_id')
    def _onchange_asset_category_handling(self):
        if self._origin.asset_category_id._origin.id:
            if self._origin.asset_category_id._origin.id != self.asset_category_id.id:
                self.update({
                    'asset_id': False,
                })
        else:
            self.update({
                'asset_id': False,
            })

    @api.onchange('asset_category_id')
    def onchange_asset_category(self):
        if self.asset_category_id:
            asset = self.env['maintenance.equipment'].sudo().search(
                [('category_id.id', '=', self.asset_category_id.id)])
            return {'domain': {'asset_id': [('id', 'in', asset.ids)]}}

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.contract_category == 'main':
                if line.quantity <= 0:
                    raise ValidationError('Quantity should be greater than 0.')
                else:
                    price = (line.quantity * line.unit_price)
                    line.subtotal = price

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.asset_job_id.project_id:
            raise ValidationError(_("Select the Project first"))
        if not self.asset_job_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))

    @api.onchange('asset_id')
    def _onchange_uom_asset_id(self):
        for rec in self:
            domain = self.env['uom.category'].search([('name', '=', 'Working Time')], limit=1)
            if rec.asset_id:
                if domain:
                    return {
                        'domain': {'uom_id': [('category_id', '=', domain.id)]}
                    }
                else:
                    return {
                        'domain': {'uom_id': []}
                    }
            else:
                return {
                    'domain': {'uom_id': []}
                }


class EquipmentEstimate(models.Model):
    _name = "equipment.estimate"
    _order = 'sequence'
    _check_company_auto = True

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    sequence = fields.Integer(string="sequence", default=0)
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    equipment_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment'),
        ('asset', 'Asset'),
    ], string="Type", default='equipment', readonly=1)
    subtotal = fields.Float('Subtotal', default=0.0, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='equipment_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    contract_category = fields.Selection(string="Contract Category", related='equipment_id.contract_category')
    quantity = fields.Float('Quantity', default=1.0)
    coefficient = fields.Float('Coeff', default=1.0)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    unit_price = fields.Float('Unit Price', default=0.0)
    analytic_idz = fields.Many2many(related="equipment_id.analytic_idz", string='Analytic Group')
    discount = fields.Float('Discount (%)', default=0.0)
    subtotal = fields.Float('Subtotal', readonly=True)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True,
                                       domain="[('company_id','=',parent.company_id)]")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    project_id = fields.Many2one(related='equipment_id.project_id', string='Project')
    prev_uom_id = fields.Many2one('uom.uom', 'Prev Uom')

    @api.onchange('coefficient', 'product_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.contract_category != 'main': return
            if rec.product_id:
                section_id = rec.equipment_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        for line in self:
            if line.product_id:
                uom_id = line.product_id.uom_id
                if line.prev_uom_id:
                    uom_id = line.prev_uom_id
                elif line._origin:
                    uom_id = line._origin.uom_id
                
                line.quantity = uom_id._compute_quantity(line.quantity, line.uom_id)
                line.prev_uom_id = line.uom_id

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = 1.0
            self.unit_price = False
            self.group_of_product = False

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.equipment_id.project_id:
            raise ValidationError(_("Select the Project first"))
        if not self.equipment_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,

                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,

            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })

    @api.depends('equipment_id.equipment_estimation_ids', 'equipment_id.equipment_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.equipment_id.equipment_estimation_ids:
                no += 1
                l.sr_no = no

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            if line.contract_category == 'main':
                if line.quantity <= 0:
                    raise ValidationError('Quantity should be greater than 0.')
                else:
                    price = (line.quantity * line.unit_price)
                    line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'asset')]}
            }

    @api.depends('equipment_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.equipment_id.section_ids:
                    for line in rec.equipment_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]


class ProjectScopeLine(models.Model):
    _inherit = "project.scope.line"

    project_id = fields.Many2one('project.project', readonly=True)


class ProjectScopeEstimate(models.Model):
    _name = 'project.scope.estimate'
    _description = 'BOQ Project Scope Estimate'
    _rec_name = 'project_scope'
    _order = 'sequence'

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    sequence = fields.Integer(string="sequence", default=0)
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    is_lock_restriction = fields.Boolean(string="Lock Change Restriction", default=False)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    scope_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    description = fields.Text(string='Description')
    subtotal = fields.Float(string='Subtotal', compute="_amount_total")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    project_id = fields.Many2one(related='scope_id.project_id', string='Project')
    company_id = fields.Many2one(related='scope_id.company_id', string='Company', readonly=True)

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.scope_id.project_id:
            raise ValidationError(_("Select the Project First"))
        if not self.scope_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))

    @api.depends('scope_id.project_scope_ids', 'scope_id.project_scope_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.scope_id.project_scope_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def project_scope_ref(self):
        for res in self:
            proj = res.scope_id.project_id
            for sco in proj.project_scope_ids:
                if res.project_scope:
                    if sco:
                        if res.project_scope.id == sco.project_scope.id:
                            res.description = sco.description
                        else:
                            res.description = False
                    else:
                        res.description = False
                else:
                    res.description = False

    def delete_scope(self):
        for rec in self:
            if rec.is_lock:
                raise ValidationError(_("You can not delete this record"))
            else:
                rec.scope_id._validate_delete_lock('Scope', rec)

    def delete(self):
        res = super(ProjectScopeEstimate, self).delete()
        print('res', res)
        return res

    @api.onchange('is_lock')
    def onchange_is_lock(self):
        for rec in self:
            rec.write({
                'is_lock_restriction': True
            })

    @api.depends('scope_id.material_estimation_ids', 'scope_id.labour_estimation_ids',
                 'scope_id.overhead_estimation_ids', 'scope_id.subcon_estimation_ids',
                 'scope_id.equipment_estimation_ids', 'scope_id.internal_asset_ids',
                 'scope_id.material_estimation_ids.subtotal', 'scope_id.labour_estimation_ids.subtotal',
                 'scope_id.overhead_estimation_ids.subtotal', 'scope_id.subcon_estimation_ids.subtotal',
                 'scope_id.equipment_estimation_ids.subtotal', 'scope_id.internal_asset_ids.subtotal')
    def _amount_total(self):
        for rec in self:
            rec.subtotal = 0

            def condition(estimate, scope):
                return estimate.project_scope.id == scope.project_scope.id

            rec.subtotal = sum([
                sum([item.subtotal for item in
                     rec.scope_id.material_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.scope_id.labour_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.scope_id.overhead_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.scope_id.subcon_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.scope_id.equipment_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in rec.scope_id.internal_asset_ids.filtered(lambda x: condition(x, rec))]),
            ])


class SectionEstimate(models.Model):
    _name = 'section.estimate'
    _description = 'BOQ Section Estimate'
    _order = 'sequence'
    _rec_name = 'section_name'

    section_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    is_lock_restriction = fields.Boolean(string="Lock Change Restriction", default=False)
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    description = fields.Text(string='Description')
    quantity = fields.Float('Quantity', default=1.0)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    subtotal = fields.Float(string='Subtotal', compute="_amount_total_section")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    project_section_computed = fields.Many2many('section.line', string="computed section lines")
    project_id = fields.Many2one(related='section_id.project_id', string='Project')
    company_id = fields.Many2one(related='section_id.company_id', string='Company', readonly=True)

    @api.depends('section_id.section_ids', 'section_id.section_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.section_id.section_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.section_id.project_id:
            raise ValidationError(_("Select the Project first"))
        if not self.section_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'description': False,
                    'subtotal': False,
                    'quantity': 1.0,
                    'uom_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'description': False,
                'subtotal': False,
                'quantity': 1.0,
                'uom_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_name_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'description': False,
                    'subtotal': False,
                    'quantity': 1.0,
                    'uom_id': False,
                })
                section_values = []

                for section in self.section_id.section_ids:
                    section_values.append(section.section_name.id)
                for variable in self.section_id.variable_ids:
                    if variable.section_name.id not in section_values:
                        self.section_id.update({
                            'variable_ids': (2, variable.id, 0)
                        })

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('section_id.material_estimation_ids', 'section_id.labour_estimation_ids',
                 'section_id.overhead_estimation_ids', 'section_id.subcon_estimation_ids',
                 'section_id.equipment_estimation_ids', 'section_id.internal_asset_ids',
                 'section_id.material_estimation_ids.subtotal', 'section_id.labour_estimation_ids.subtotal',
                 'section_id.overhead_estimation_ids.subtotal', 'section_id.subcon_estimation_ids.subtotal',
                 'section_id.equipment_estimation_ids.subtotal', 'section_id.internal_asset_ids.subtotal')
    def _amount_total_section(self):
        for rec in self:
            rec.subtotal = 0

            def condition(estimate, section):
                return estimate.project_scope.id == section.project_scope.id and \
                    estimate.section_name.id == section.section_name.id

            rec.subtotal = sum([
                sum([item.subtotal for item in
                     rec.section_id.material_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.section_id.labour_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.section_id.overhead_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.section_id.subcon_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.section_id.equipment_estimation_ids.filtered(lambda x: condition(x, rec))]),
                sum([item.subtotal for item in
                     rec.section_id.internal_asset_ids.filtered(lambda x: condition(x, rec))]),
            ])

    @api.onchange('is_lock')
    def onchange_is_lock(self):
        for rec in self:
            rec.write({
                'is_lock_restriction': True
            })

    @api.onchange('section_name', 'section_id.project_id')
    def project_section_name_ref(self):
        for res in self:
            proj = res.section_id.project_id
            for sec in proj.project_section_ids:
                if res.section_name:
                    if sec:
                        if res.section_name.id == sec.section.id:
                            res.description = sec.description
                            res.quantity = sec.quantity
                            res.uom_id = sec.uom_id.id
                        else:
                            res.description = False
                            res.quantity = 1.0
                            res.uom_id = False
                    else:
                        res.description = False
                        res.quantity = 1.0
                        res.uom_id = False
                else:
                    res.description = False
                    res.quantity = 1.0
                    res.uom_id = False


class VariableEstimate(models.Model):
    _name = 'variable.estimate'
    _description = 'BOQ Variable Estimate'
    _order = 'sequence'
    _rec_name = 'variable_name'

    variable_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    is_lock = fields.Boolean(string="Locked", default=False)
    is_new = fields.Boolean(string="New", default=True)
    is_lock_restriction = fields.Boolean(string="Lock Change Restriction", default=False)
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_name = fields.Many2one('variable.template', string='Variable', required=True)
    variable_quantity = fields.Float(string='Quantity', default=1.0)
    variable_uom = fields.Many2one('uom.uom', string="Unit Of Measure")
    total_variable = fields.Float(string='Total Variable', readonly=True)
    subtotal = fields.Float(string='Subtotal')
    subtotal_var = fields.Float(string='Subtotal')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    company_id = fields.Many2one(related='variable_id.company_id', string='Company', readonly=True)
    analytic_idz = fields.Many2many(related="variable_id.analytic_idz", string='Analytic Group')
    project_id = fields.Many2one(related='variable_id.project_id', string='Project')
    onchange_pass = fields.Boolean(string="Pass", default=False)

    @api.onchange('project_scope', 'section_name', 'variable_name', 'variable_quantity')
    def onchange_quantity(self):
        self.write({'onchange_pass': False})

    def unlink(self):
        res = super(VariableEstimate, self).unlink()
        self.clear_caches()
        return res

    @api.depends('variable_id.variable_ids', 'variable_id.variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.variable_id.variable_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope')
    def onchange_project_scope(self):
        if not self.variable_id.project_id:
            raise ValidationError(_("Select the Project first"))
        if not self.variable_id.analytic_idz:
            raise ValidationError(_("Fill the Analytic Group first"))
        if not self.variable_id.project_scope_ids:
            raise ValidationError(_("Fill the Project Scope first"))
        if not self.variable_id.section_ids:
            raise ValidationError(_("Fill the Section first"))

    @api.onchange('variable_quantity')
    def _onchange_variable_quantity(self):
        for rec in self:
            if rec.variable_quantity <= 0:
                raise ValidationError('Quantity should be greater than 0.')

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('variable_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.variable_id.section_ids:
                    for line in rec.variable_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_name': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_name': False,
            })

    @api.onchange('section_name')
    def onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_name': False,
                })
        else:
            self.update({
                'variable_name': False,
            })

    @api.onchange('variable_name')
    def onchange_variable_name(self):
        if self.variable_name:
            self.variable_quantity = 1.0
            self.variable_uom = self.variable_name.variable_uom.id
            self.total_variable = self.variable_name.total_variable
        else:
            self.variable_quantity = 1.0
            self.variable_uom = False
            self.total_variable = False
