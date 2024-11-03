# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo import tools
from datetime import datetime, timedelta, date
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
import math
from lxml import etree

dic = {
    'to_19': ('Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'),
    'tens': ('Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'),
    'denom': ('', 'Thousand', 'Million', 'Billion', 'Trillion', 'Quadrillion', 'Quintillion'),
    'to_19_id': ('Nol', 'Satu', 'Dua', 'Tiga', 'Empat', 'Lima', 'Enam', 'Tujuh', 'Delapan', 'Sembilan', 'Sepuluh', 'Sebelas', 'Dua Belas', 'Tiga Belas', 'Empat Belas', 'Lima Belas', 'Enam Belas', 'Tujuh Belas', 'Delapan Belas', 'Sembilan Belas'),
    'tens_id': ('Dua Puluh', 'Tiga Puluh', 'Empat Puluh', 'Lima Puluh', 'Enam Puluh', 'Tujuh Puluh', 'Delapan Puluh', 'Sembilan Puluh'),
    'denom_id': ('', 'Ribu', 'Juta', 'Miliar', 'Triliun', 'Biliun')
}

ESTIMATES = [
    'material_line_ids',
    'labour_line_ids',
    'subcon_line_ids',
    'overhead_line_ids',
    'equipment_line_ids',
    'internal_asset_line_ids'
]

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

class SaleOrderConst(models.Model):
    _name = 'sale.order.const'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _rec_name = "name"
    _description = 'Quotation'
    _order = 'date_order desc, id desc'
    _check_company_auto = True

    # Remove submenu report button
    @api.model
    def fields_view_get(self, view_id = None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu
        )
        if res.get('toolbar', False) and res.get('toolbar').get('print', False):
            reports = res.get('toolbar').get('print')
            for report in reports:
                res['toolbar']['print'].remove(report)
        return res

    def print_out(self):
        return{
            'type' : 'ir.actions.act_window',
            'name' : 'Printout Options',
            'view_mode' : 'form',
            'target' : 'new',
            'res_model' : 'construction.sale.order.report.wizard',
            'context' : {'sale_order_data' : self.id,
                         'default_sale_order_id' : self.id,}
        }
    
    report_name = fields.Char(string='Report Name', compute='_compute_report_name')  
    report_project_scope_id = fields.One2many(string='Report Project Scope', comodel_name='project.scope.line', compute='_compute_report_project_scope_id')
    report_contract_category = fields.Char(string='Report Contract Category', compute='_compute_report_contract_category' )
    report_title = fields.Char(string='Report title based on its state', compute='_compute_report_title' )
    report_street = fields.Char(string='Report Project Location (Street)', compute='_compute_report_street')
    report_country = fields.Char(string='Report Project Location (Country)', compute='_compute_report_country')
    report_tax = fields.Char(string = 'Report Tax', compute='_compute_report_tax')
    report_retention_1_date = fields.Char(string = 'Report Retention 1 Date', compute='_compute_report_retention_1_date')
    report_retention_2_date = fields.Char(string = 'Report Retention 2 Date', compute='_compute_report_retention_2_date')
    said = fields.Char(compute="_said", string="Say", help="Say (English)", store=True)
    is_wizard = fields.Boolean(string="From WIzard", default=False)
    job_count = fields.Integer(string="BOQ Count", default=0)

    @api.depends('report_name')
    def _compute_report_name(self):
        if self.state == 'sale':
            self.report_name = "Sale Order"
        else :
            self.report_name = "Quotation"
        
    @api.depends('report_title')
    def _compute_report_title(self):
        if self.state == 'sale':
            self.report_title = "Sale Order" + " - " +self.name
        else :
            self.report_title = "Quotation" + " - " +self.name

    @api.depends('report_street')
    def _compute_report_street(self):
        if self.street and self.city and self.state_id.name and self.country_id.name and self.zip_code:
            if self.street_2:
                address_street = self.street + ", " + self.street_2 + ", " +self.city + ", " 
            else:   
                address_street = self.street + ", " + self.city + ", " 
            self.report_street = address_street
        else:
            self.report_street = ""

    @api.depends('report_country')
    def _compute_report_country(self):
        if self.street and self.city and self.state_id.name and self.country_id.name and self.zip_code:
            address_country = self.state_id.name + ", " + str(self.country_id.name) + ", " + self.zip_code 
            self.report_country = address_country
        else:
            self.report_country = "" 
    
    @api.depends('report_tax')
    def _compute_report_tax(self):
        if self.tax_id:
            temp_tax = list()
            for tax in self.tax_id:
                temp_str = tax.name + " " + str(abs(tax.amount)) + "%"
                temp_tax.append(temp_str)

            self.report_tax = ", ".join(temp_tax)
        else:
            self.report_tax = ""

        
    @api.depends('report_retention_1_date')
    def _compute_report_retention_1_date(self):
        if self.retention1_date:
            self.report_retention_1_date = self.retention1_date.strftime("%m/%d/%Y")
        else:
            self.report_retention_1_date = ""
    
    @api.depends('report_retention_2_date')
    def _compute_report_retention_2_date(self):
        if self.retention2_date:
            self.report_retention_2_date = self.retention2_date.strftime("%m/%d/%Y")
        else:
            self.report_retention_2_date = ""

    @api.depends('amount_total')
    def _said(self):
        for line in self:
            frac, whole = math.modf(round(line.amount_total))
            amount = whole if line.company_currency_id.name == 'IDR' else line.amount_total
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


    def check_scope_labour_line(self, data):
        if data.labour_line_ids:
            for labour in data.labour_line_ids:
                if not labour.project_scope.name:
                    return False
        return True

    def check_scope_internal_asset(self, data):
        if data.internal_asset_line_ids:
            for internal in data.internal_asset_line_ids:
                if not internal.project_scope.name:
                    return False
        return True
         
    def check_scope_equipment_lease(self, data):
        if data.equipment_line_ids:
            for equipment in data.equipment_line_ids:
                if not equipment.project_scope.name:
                    return False
        return True

    @api.depends('report_contract_category')
    def _compute_report_contract_category(self):
        if self.contract_category == 'main':
            self.report_contract_category = "Main Contract"
        else:
            self.report_contract_category = "Variation Order"

    @api.onchange('penalty')
    def _onchange_penalty(self):
        for rec in self:
            if rec.penalty:
                pen = rec.penalty
                rec.diff_penalty = pen.diff_penalty
                rec.amount = pen.amount
                rec.method = pen.method
                rec.method_client = pen.method_client
                rec.amount_client = pen.amount_client 

    @api.onchange('contract_category')
    def _onchange_domain_penalty(self):
        res = {}
        for rec in self:
            if rec.contract_category == 'main':
                res['domain'] = {'penalty': [('penalty', '=', ['project_cancel'])]}
            elif rec.contract_category == 'var':
                res['domain'] = {'penalty': [('penalty', '=', ['contract_cancel'])]}
        return res 

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

    def _default_validity_date(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_quotation_validity_days'):
            days = self.env.company.quotation_validity_days
            if days > 0:
                return fields.Date.to_string(datetime.now() + timedelta(days))
        return False

    def _compute_is_expired(self):
        today = fields.Date.today()
        for order in self:
            order.is_expired = order.state == 'sent' and order.validity_date and order.validity_date < today


    @api.onchange("job_references")
    def _onchange_job_reference_many2many(self):
        context = self._context
        is_wizard = context.get('is_wizard')
        if is_wizard or self.is_wizard:
            job_reference = context.get('default_job_references')
            if job_reference:
                job_count = len(job_reference)
            else:
                job_count = self.job_count
            if len(self.job_references) > job_count:
                raise ValidationError(_("The addition of a new BOQ does not affect the quotation value. You need to make a new quotation for that BOQ."))
            # elif len(self.job_references) == job_count - 1:
            #     raise ValidationError(_("You can't delete the default BOQ."))
            for job in job_reference:
                if job[1] not in self.job_references._origin.ids:
                    raise ValidationError(_("You can't delete the default BOQ."))
            
        if self.job_references:
            job = self.job_references
            self.project_id = job[0].project_id.id
            # self.partner_id = job[0].partner_id.id
            self.client_order_ref = job[0].customer_ref
            self.analytic_idz = job[0].analytic_idz
            self.start_date = job[0].start_date
            self.end_date = job[0].end_date
            self.contract_category = job[0].contract_category
            self.main_contract_ref = job[0].main_contract_ref
            self.warehouse_address = job[0].warehouse_address

            if not (self.is_wizard or is_wizard):
                scope = []
                section = []
                variable = []
                material_lines = []
                labour_lines = []
                overhead_lines = []
                asset_lines = []
                equipment_lines = []
                subcon_lines = []
                self.project_scope_ids = False
                self.section_ids = False
                self.variable_ids = False
                self.material_line_ids = False
                self.labour_line_ids = False
                self.overhead_line_ids = False
                self.internal_asset_line_ids = False
                self.equipment_line_ids = False
                self.subcon_line_ids = False
                scope_vals = []
                sect_vals = []
                var_vals = []
                mat_vals = []
                lab_vals = []
                ov_vals = []
                asset_vals = []
                equip_vals = []
                sub_vals = []
                for line in self.job_references:
                    if line.project_scope_ids:
                        for sco in line.project_scope_ids:
                            value = {
                                "project_scope": sco.project_scope.name,
                                "description": sco.description
                            }
                            if value not in scope_vals:
                                scope.append((0, 0, {
                                    "project_scope": sco.project_scope and sco.project_scope.id or False,
                                    "description": sco.description,
                                    "subtotal_scope": sco.subtotal,
                                }))
                                scope_vals.append(value)
                            else:
                                idx = scope_vals.index(value)
                                scope[idx][2]['subtotal_scope'] += sco.subtotal

                    
                    if line.section_ids:
                        for sec in line.section_ids:
                            value = {
                                "project_scope": sec.project_scope.name,
                                "section": sec.section_name.name,
                                "description": sec.description,
                                "uom_id": sec.uom_id.id
                            }
                            if value not in sect_vals:
                                section.append((0, 0, {
                                    "project_scope": sec.project_scope and sec.project_scope.id or False,
                                    "section": sec.section_name or sec.section_name.id or False,
                                    "description": sec.description,
                                    "quantity": sec.quantity,
                                    "uom_id": sec.uom_id or sec.uom_id.id or False,
                                    "subtotal_section": sec.subtotal,
                                }))
                                sect_vals.append(value)
                            else:
                                idx = sect_vals.index(value)
                                section[idx][2]['subtotal_section'] += sec.subtotal
                                section[idx][2]['quantity'] += sec.quantity

                    if line.variable_ids:
                        for var in line.variable_ids:
                            value = {
                                "project_scope": var.project_scope.name,
                                "section": var.section_name.name,
                                "variable": var.variable_name.name,
                                "uom_id": var.variable_uom.id
                            }
                            if value not in var_vals:
                                variable.append((0, 0, {
                                    "project_scope": var.project_scope and var.project_scope.id or False,
                                    "section": var.section_name or var.section_name.id or False,
                                    "variable": var.variable_name or var.variable_name.id or False,
                                    "quantity": var.variable_quantity,
                                    "uom_id": var.variable_uom or var.variable_uom.id or False,
                                    "subtotal_variable": var.subtotal,
                                }))
                                var_vals.append(value)
                            else:
                                idx = var_vals.index(value)
                                variable[idx][2]['subtotal_variable'] += var.subtotal
                                variable[idx][2]['quantity'] += var.variable_quantity

                    if line.material_estimation_ids:
                        for material in line.material_estimation_ids:
                            value = {
                                "project_scope": material.project_scope.name,
                                "section_name": material.section_name.name,
                                "variable_ref": material.variable_ref.name,
                                "type": "material",
                                "group_of_product": material.group_of_product.id,
                                "material_id": material.product_id.id,
                                "description": material.description,
                                "uom_id": material.uom_id.id,
                                "unit_price": material.unit_price
                            }
                            if value not in mat_vals:
                                material_lines.append((0, 0, {
                                    "project_scope": material.project_scope and material.project_scope.id or False,
                                    "section_name": material.section_name and material.section_name.id or False,
                                    "variable_ref": material.variable_ref and material.variable_ref.id or False,
                                    "type": "material",
                                    "group_of_product": material.group_of_product and material.group_of_product.id or False,
                                    "material_id": material.product_id and material.product_id.id or False,
                                    "description": material.description,
                                    "analytic_idz": material.analytic_idz and [(6, 0, material.analytic_idz.ids)] or False,
                                    "quantity": material.quantity,
                                    "uom_id": material.uom_id and material.uom_id.id or False,
                                    "unit_price": material.unit_price,
                                    "subtotal": material.subtotal,
                                }))
                                mat_vals.append(value)
                            else:
                                idx = mat_vals.index(value)
                                if value['unit_price'] > material_lines[idx][2]['unit_price']:
                                    material_lines[idx][2]['unit_price'] = value['unit_price']
                                    
                                material_lines[idx][2]['quantity'] += material.quantity
                                material_lines[idx][2]['subtotal'] += material.subtotal
                    
                    if line.labour_estimation_ids:
                        for labour in line.labour_estimation_ids:
                            value = {
                                "project_scope": labour.project_scope.name,
                                "section_name": labour.section_name.name,
                                "variable_ref": labour.variable_ref.name,
                                "type": "labour",
                                "group_of_product": labour.group_of_product.id,
                                "labour_id": labour.product_id.id,
                                "description": labour.description,
                                "contractors": labour.contractors,
                                "time": labour.time,
                                "uom_id": labour.uom_id.id,
                                "unit_price": labour.unit_price
                            }
                            if value not in lab_vals:
                                labour_lines.append((0, 0, {
                                    "project_scope": labour.project_scope and labour.project_scope.id or False,
                                    "section_name": labour.section_name and labour.section_name.id or False,
                                    "variable_ref": labour.variable_ref and labour.variable_ref.id or False,
                                    "type": "labour",
                                    "group_of_product": labour.group_of_product and labour.group_of_product.id or False,
                                    "labour_id": labour.product_id and labour.product_id.id or False,
                                    "description": labour.description,
                                    "analytic_idz": labour.analytic_idz and [(6, 0, labour.analytic_idz.ids)] or False,
                                    "contractors": labour.contractors,
                                    "time": labour.time,
                                    "quantity": labour.quantity,
                                    "uom_id": labour.uom_id and labour.uom_id.id or False,
                                    "unit_price": labour.unit_price,
                                    "subtotal": labour.subtotal,
                                }))
                                lab_vals.append(value)
                            else:
                                idx = lab_vals.index(value)
                                if value['unit_price'] > labour_lines[idx][2]['unit_price']:
                                    labour_lines[idx][2]['unit_price'] = value['unit_price']

                                labour_lines[idx][2]['quantity'] += labour.quantity
                                labour_lines[idx][2]['subtotal'] += labour.subtotal
                    
                    if line.overhead_estimation_ids:
                        for overhead in line.overhead_estimation_ids:
                            value = {
                                "project_scope": overhead.project_scope.name,
                                "section_name": overhead.section_name.name,
                                "variable_ref": overhead.variable_ref.name,
                                "type": "overhead",
                                "group_of_product": overhead.group_of_product.id,
                                "overhead_id": overhead.product_id.id,
                                "description": overhead.description,
                                "uom_id": overhead.uom_id.id,
                                "unit_price": overhead.unit_price
                            }
                            if value not in ov_vals:
                                overhead_lines.append((0, 0, {
                                    "project_scope": overhead.project_scope and overhead.project_scope.id or False,
                                    "section_name": overhead.section_name and overhead.section_name.id or False,
                                    "variable_ref": overhead.variable_ref and overhead.variable_ref.id or False,
                                    "type": "overhead",
                                    "group_of_product": overhead.group_of_product and overhead.group_of_product.id or False,
                                    "overhead_id": overhead.product_id and overhead.product_id.id or False,
                                    "description": overhead.description,
                                    "analytic_idz": overhead.analytic_idz and [(6, 0, overhead.analytic_idz.ids)] or False,
                                    "quantity": overhead.quantity,
                                    "uom_id": overhead.uom_id and overhead.uom_id.id or False,
                                    "unit_price": overhead.unit_price,
                                    "subtotal": overhead.subtotal,
                                }))
                                ov_vals.append(value)
                            else:
                                idx = ov_vals.index(value)
                                if value['unit_price'] > overhead_lines[idx][2]['unit_price']:
                                    overhead_lines[idx][2]['unit_price'] = value['unit_price']

                                overhead_lines[idx][2]['quantity'] += overhead.quantity
                                overhead_lines[idx][2]['subtotal'] += overhead.subtotal
                    
                    if line.internal_asset_ids:
                        for asset in line.internal_asset_ids:
                            value = {
                                'project_scope': asset.project_scope.name,
                                'section_name': asset.section_name.name,
                                'variable_ref': asset.variable_ref.name,
                                'type': 'asset',
                                'asset_category_id': asset.asset_category_id.id,
                                'asset_id': asset.asset_id.id,
                                'description': asset.description,
                                'uom_id': asset.uom_id.id,
                                'unit_price': asset.unit_price
                            }
                            if value not in asset_vals:
                                asset_lines.append((0, 0, {
                                    'project_scope': asset.project_scope and asset.project_scope.id or False,
                                    'section_name': asset.section_name and asset.section_name.id or False,
                                    'variable_ref': asset.variable_ref and asset.variable_ref.id or False,
                                    'type': 'asset',
                                    'asset_category_id': asset.asset_category_id and asset.asset_category_id.id or False,
                                    'asset_id': asset.asset_id and asset.asset_id.id or False,
                                    'description': asset.description,
                                    'analytic_idz': asset.analytic_idz and [(6, 0, asset.analytic_idz.ids)] or False,
                                    'quantity': asset.quantity,
                                    'uom_id': asset.uom_id and asset.uom_id.id or False,
                                    'unit_price': asset.unit_price,
                                    'subtotal': asset.subtotal,
                                }))
                                asset_vals.append(value)
                            else:
                                idx = asset_vals.index(value)
                                if value['unit_price'] > asset_lines[idx][2]['unit_price']:
                                    asset_lines[idx][2]['unit_price'] = value['unit_price']

                                asset_lines[idx][2]['quantity'] += asset.quantity
                                asset_lines[idx][2]['subtotal'] += asset.subtotal

                    if line.equipment_estimation_ids:
                        for equipment in line.equipment_estimation_ids:
                            value = {
                                "project_scope": equipment.project_scope.name,
                                "section_name": equipment.section_name.name,
                                "variable_ref": equipment.variable_ref.name,
                                "type": "equipment",
                                "group_of_product": equipment.group_of_product.id,
                                "equipment_id": equipment.product_id.id,
                                "description": equipment.description,
                                "uom_id": equipment.uom_id and equipment.uom_id.id or False,
                                "unit_price": equipment.unit_price
                            }
                            if value not in equip_vals:
                                equipment_lines.append((0, 0, {
                                    "project_scope": equipment.project_scope and equipment.project_scope.id or False,
                                    "section_name": equipment.section_name and equipment.section_name.id or False,
                                    "variable_ref": equipment.variable_ref and equipment.variable_ref.id or False,
                                    "type": "equipment",
                                    "group_of_product": equipment.group_of_product and equipment.group_of_product.id or False,
                                    "equipment_id": equipment.product_id and equipment.product_id.id or False,
                                    "description": equipment.description,
                                    "analytic_idz": equipment.analytic_idz and [(6, 0, equipment.analytic_idz.ids)] or False,
                                    "quantity": equipment.quantity,
                                    "uom_id": equipment.uom_id and equipment.uom_id.id or False,
                                    "unit_price": equipment.unit_price,
                                    "subtotal": equipment.subtotal,
                                }))
                                equip_vals.append(value)
                            else:
                                idx = equip_vals.index(value)
                                if value['unit_price'] > equipment_lines[idx][2]['unit_price']:
                                    equipment_lines[idx][2]['unit_price'] = value['unit_price']

                                equipment_lines[idx][2]['quantity'] += equipment.quantity
                                equipment_lines[idx][2]['subtotal'] += equipment.subtotal
                    
                    if line.subcon_estimation_ids:
                        for subcon in line.subcon_estimation_ids:
                            value = {
                                "project_scope": subcon.project_scope.name,
                                "section_name": subcon.section_name.name,
                                "variable_ref": subcon.variable_ref.name,
                                "type": "subcon",
                                "subcon_id": subcon.variable.id,
                                "description": subcon.description,
                                "uom_id": subcon.uom_id.id,
                                "unit_price": subcon.unit_price
                            }
                            if value not in sub_vals:
                                subcon_lines.append((0, 0, {
                                    "project_scope": subcon.project_scope and subcon.project_scope.id or False,
                                    "section_name": subcon.section_name and subcon.section_name.id or False,
                                    "variable_ref": subcon.variable_ref and subcon.variable_ref.id or False,
                                    "type": "subcon",
                                    "subcon_id": subcon.variable and subcon.variable.id or False,
                                    "description": subcon.description,
                                    "analytic_idz": subcon.analytic_idz and [(6, 0, subcon.analytic_idz.ids)] or False,
                                    "quantity": subcon.quantity,
                                    "uom_id": subcon.uom_id and subcon.uom_id.id or False,
                                    "unit_price": subcon.unit_price,
                                    "subtotal": subcon.subtotal,
                                }))
                                sub_vals.append(value)
                            else:
                                idx = sub_vals.index(value)
                                if value['unit_price'] > subcon_lines[idx][2]['unit_price']:
                                    subcon_lines[idx][2]['unit_price'] = value['unit_price']

                                subcon_lines[idx][2]['quantity'] += subcon.quantity
                                subcon_lines[idx][2]['subtotal'] += subcon.subtotal
                        
                if len(scope) > 0:
                    self.project_scope_ids = scope
                if len(section) > 0:
                    self.section_ids = section
                if len(variable) > 0:
                    self.variable_ids = variable
                if len(material_lines) > 0:
                    self.material_line_ids = material_lines
                if len(labour_lines) > 0:
                    self.labour_line_ids = labour_lines
                if len(overhead_lines) > 0:
                    self.overhead_line_ids = overhead_lines
                if len(asset_lines) > 0:
                    self.internal_asset_line_ids = asset_lines
                if len(equipment_lines) > 0:
                    self.equipment_line_ids = equipment_lines
                if len(subcon_lines) > 0:
                    self.subcon_line_ids = subcon_lines

            elif self.is_wizard or is_wizard:
                self.project_scope_ids = False
                self.section_ids = False
                self.variable_ids = False

                self.material_line_ids = False
                self.labour_line_ids = False
                self.overhead_line_ids = False
                self.internal_asset_line_ids = False
                self.equipment_line_ids = False
                self.subcon_line_ids = False

                self.project_scope_ids = context.get('default_project_scope_ids')
                self.section_ids = context.get('default_section_ids')
                self.variable_ids = context.get('default_variable_ids')

                self.material_line_ids = context.get('default_material_line_ids')
                self.labour_line_ids = context.get('default_labour_line_ids')
                self.overhead_line_ids = context.get('default_overhead_line_ids')
                self.internal_asset_line_ids = context.get('default_internal_asset_line_ids')
                self.equipment_line_ids = context.get('default_equipment_line_ids')
                self.subcon_line_ids = context.get('default_subcon_line_ids')
                
    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.project_id:
            project = self.project_id
            self.partner_id = project.partner_id.id
            self.branch_id = project.branch_id.id
            self.opportunity_id = project.lead_id.id
            self.address = project.address
            self.street = project.street
            self.street_2 = project.street_2
            self.city = project.city
            self.state_id = project.state_id.id
            self.country_id = project.country_id.id
            self.zip_code = project.zip_code
            self.user_id = [(6, 0, [v.id for v in project.sales_person_id])]
            self.team_id = project.sales_team
            self.update(project.get_contract_customer_values())

    
    @api.onchange('contract_category')
    def set_vo_payment_type(self):
        self.vo_payment_type = False
        if self.contract_category == 'main':
            self.vo_payment_type = 'split'
        else:
            self.vo_payment_type = 'join'

    @api.onchange('vo_payment_type')
    def onchange_vo_payment_type(self):
        if self.vo_payment_type == 'split' and self.contract_category == 'var':
            self.contract_parent = False
            self.dp_method = 'per'
            self.down_payment = False
            self.retention1 = False
            self.retention1_date = False
            self.retention_term_1 = False
            self.retention2 = False
            self.retention2_date = False
            self.retention_term_2 = False
            self.tax_id = False
        
    @api.onchange('contract_amount')
    def onchange_contract_amount_to_join(self):
        for res in self:
            if res.contract_category == 'var':
                if res.contract_amount < 0:
                    res.vo_payment_type = 'join'  
        
    @api.onchange('contract_parent')
    def onchange_contract_parent(self): 
        if self.contract_parent:
            join = self.contract_parent
            self.dp_method = join.dp_method
            self.down_payment = join.down_payment
            self.retention1 = join.retention1
            self.retention1_date = join.retention1_date
            self.retention_term_1 = join.retention_term_1
            self.retention2 = join.retention2
            self.retention2_date = join.retention2_date
            self.retention_term_2 = join.retention_term_2
            self.tax_id = [(6, 0, [v.id for v in join.tax_id])]
            self.payment_term_id = join.payment_term_id
            self.diff_penalty = join.diff_penalty
            self.amount = join.amount
            self.method = join.method
            self.method_client = join.method_client
            self.amount_client = join.amount_client
        
    @api.constrains('state')
    def contract_category_cahnge(self):
        if self.state != 'sale':
            self.name = self.env['ir.sequence'].next_by_code('sale.order.quotation.const')
        else:
            self.name = self.env['ir.sequence'].next_by_code('sale.order.quotation.order.const')

    @api.constrains('start_date', 'end_date')
    def constrains_date(self):
        for rec in self:
            if rec.start_date != False and rec.end_date != False:
                if rec.start_date > rec.end_date:
                    raise UserError(_('End date should be after planned start date.'))
                    
    
    # @api.constrains('retention1_date','retention2_date')
    # def constrains_retention(self):
    #     for rec in self:
    #         if rec.retention1_date and rec.retention2_date == False:
    #             if rec.end_date > rec.retention1_date:
    #                 raise UserError(_('Retention 1 date should be after planned end date.'))
    #         elif rec.retention1_date and rec.retention2_date:
    #             if rec.end_date > rec.retention1_date and rec.end_date > rec.retention2_date:
    #                 raise UserError(_('Retention 1 date and retention 2 date should be after planned end date.'))
    #             elif rec.end_date > rec.retention1_date:
    #                 raise UserError(_('Retention 1 date should be after planned end date.'))
    #             elif rec.end_date > rec.retention2_date:
    #                 raise UserError(_('Retention 2 date should be after planned end date.'))
    #             elif rec.retention1_date > rec.retention2_date:
    #                 raise UserError(_('Retention 2 date should be after retention 1 date.'))
    #             elif rec.retention1_date == rec.retention2_date:
    #                 raise UserError(_('Retention 2 date should be after retention 1 date.'))
    #         elif rec.retention1_date == False and rec.retention2_date == False:
    #             pass

    # @api.onchange('retention1_date','retention2_date')
    # def onchange_retention(self):
    #     for rec in self:
    #         if rec.retention1_date and rec.retention2_date == False:
    #             if rec.end_date > rec.retention1_date:
    #                 raise UserError(_('Retention 1 date should be after planned end date.'))
    #         elif rec.retention1_date and rec.retention2_date:
    #             if rec.end_date > rec.retention1_date and rec.end_date > rec.retention2_date:
    #                 raise UserError(_('Retention 1 date and retention 2 date should be after planned end date.'))
    #             elif rec.end_date > rec.retention1_date:
    #                 raise UserError(_('Retention 1 date should be after planned end date.'))
    #             elif rec.end_date > rec.retention2_date:
    #                 raise UserError(_('Retention 2 date should be after planned end date.'))
    #             elif rec.retention1_date > rec.retention2_date:
    #                 raise UserError(_('Retention 2 date should be after retention 1 date.'))
    #             elif rec.retention1_date == rec.retention2_date:
    #                 raise UserError(_('Retention 2 date should be after retention 1 date.'))
    #         elif rec.retention1_date == False and rec.retention2_date == False:
    #             pass

    def send_email(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        template_id = self._find_mail_template()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order.const',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            # 'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            # 'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def _find_mail_template(self, force_confirmation_template=False):
        template_id = False

        if force_confirmation_template or (self.state == 'sale' and not self.env.context.get('proforma', False)):
            template_id = int(self.env['ir.config_parameter'].sudo().get_param('equip3_construction_sales_operation.default_confirmation_template_sale_const'))
            template_id = self.env['mail.template'].search([('id', '=', template_id)]).id
            if not template_id:
                template_id = self.env['ir.model.data'].xmlid_to_res_id('equip3_construction_sales_operation.mail_template_sale_const_confirmation', raise_if_not_found=False)
        if not template_id:
            template_id = self.env['ir.model.data'].xmlid_to_res_id('equip3_construction_sales_operation.email_template_edi_sale_const', raise_if_not_found=False)

        return template_id

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('sale.order.quotation.const')
        res =  super(SaleOrderConst, self).create(vals)
        # if res.job_references:
        #     for job in res.job_references:
        #         job.write({
        #             'state':'done',
        #             'sale_state':'quotation',
        #             'quotation_id' : [(4, vals.get('id'))]
        #         })
        if res.end_date and res.start_date:
            end_year = int(res.end_date.strftime('%Y'))
            start_year = int(res.start_date.strftime('%Y'))
            for i in range(start_year, end_year+1):
                # year = self.env['const.year'].search([('name', '=', i)])
                # convert above code to query
                self.env.cr.execute("SELECT * FROM const_year WHERE name = %s", (i,))
                year = self.env.cr.fetchall()
                if len(year) < 1:
                    # self.env['const.year'].create({'name': i})
                    # convert above code to query
                    self.env.cr.execute("INSERT INTO const_year (name) VALUES (%s)", (i,))
        return res

    def write(self, values):
        res = super().write(values)
        for rec in self:
            if rec.end_date:
                if rec.start_date:
                    end_year = int(rec.end_date.strftime('%Y'))
                    start_year = int(rec.start_date.strftime('%Y'))
                    for i in range(start_year, end_year+1):
                        # year = self.env['const.year'].search([('name', '=', i)])
                        # convert above code to query
                        self.env.cr.execute("SELECT * FROM const_year WHERE name = %s", (i,))
                        year = self.env.cr.fetchall()
                        if len(year) < 1:
                            # self.env['const.year'].create({'name': i})
                            # convert above code to query
                            self.env.cr.execute("INSERT INTO const_year (name) VALUES (%s)", (i,))
        return res
    
    @api.model
    def _domain_project(self):
        return [('company_id','=',self.env.company.id),('branch_id', 'in', self.env.branches.ids)]

    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                        index=True, default=lambda self: _('New'))
    active = fields.Boolean(string='Active', default=True)
    payment_seq = fields.Char(string='Payment Seq', required=True, copy=False, readonly=True,
                        index=True, default=lambda self: _('New'))
    job_reference = fields.Many2one('job.estimate', required=False, tracking=True, string="BOQ", ondelete='restrict', readonly=True,
                    states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                    domain="[('state_new', '=', 'confirmed'), ('sale_state','in', ['draft','quotation']), ('department_type','!=','department')]")
    job_references = fields.Many2many('job.estimate', required=True, tracking=True, string="BOQ",
                                     ondelete='restrict', readonly=True,
                                     states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                     domain="[('state_new', '=', 'confirmed'), ('sale_state','in', ['draft','quotation']), ('department_type','!=','department')]")
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1)
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',
        readonly=True, required=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                           'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)], 'sale': [('readonly', False)]}, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    # penalty = fields.Html(string='Penalty')
    
    analytic_idz = fields.Many2many('account.analytic.tag', string='Analytic Group', domain="[('company_id', '=', company_id)]", readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                           'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    project_id = fields.Many2one('project.project', required=True, tracking=True, string="Project", readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},domain=_domain_project)
    report_template_id = fields.Many2one('ir.actions.report', string="Sale Order Template")
    date_order = fields.Datetime(string='Order Date', required=True, readonly=True, index=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=False, default=fields.Datetime.now, help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.",tracking=True)
    validity_date = fields.Date(string='Expiration Date', readonly=True, copy=False, default=_default_validity_date,
                                states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    is_expired = fields.Boolean(compute='_compute_is_expired', string="Is expired")
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=1,
        help="If you change the pricelist, only newly added lines will be affected.")
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=["pricelist_id"], store=True, string="Sale Order Currency")
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    type_name = fields.Char('Type Name', compute='_compute_type_name')
    adjustment_type = fields.Selection([
                        ('scope', 'Project Scope'),
                        ('section', 'Section'),
                        ('line', 'Order Line'), 
                        ('global', 'Global')
                        ],string='Adjustment Applies to',default='global', readonly=True,
                        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                           'over_limit_approved': [('readonly', False)]}) 
    discount_type = fields.Selection([
                        ('scope', 'Project Scope'),
                        ('section', 'Section'),
                        ('line', 'Order Line'), 
                        ('global', 'Global')
                        ],string='Discount Applies to', default='global', readonly=True,
                        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                           'over_limit_approved': [('readonly', False)]}) 
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('to_approve', 'Waiting For Contract Approval'),
        ('quotation_approved', 'Quotation Approved'),
        ('reject', 'Quotation Rejected'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('on_hold', 'On Hold'),
        ('block', 'Blocked')
        ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    
    state_const = fields.Selection(related='state', tracking=False)
    state_1_const = fields.Selection(related='state', tracking=False)
    state_done = fields.Selection(related='state', tracking=False)
    state_cancel = fields.Selection(related='state', tracking=False)
    state_block = fields.Selection(related='state', tracking=False)

    use_retention = fields.Boolean(string="Use Retention", default=True)
    use_dp = fields.Boolean(string="Use Down Payment", default=True)
    boq_revised_bool = fields.Boolean(string='BOQ Revised', default=False)
    total_boq_revision= fields.Integer(string="BOQ Revision",compute='_comute_revision_boq')

    signature = fields.Image('Signature', help='Signature received through the portal.', copy=False, attachment=True, max_width=1024, max_height=1024)
    signed_by = fields.Char('Signed By', help='Name of the person that signed the SO.', copy=False)
    signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False)

    penalty = fields.Many2one('construction.penalty',string='Penalty', readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})
    penalty_type = fields.Selection(
                    [('project_cancel', 'Project Cancel'),
                     ('contract_cancel', 'Contract Cancel')], string='Penalty Type', readonly=True,
                     states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})
    diff_penalty = fields.Boolean(string='Different Penalty', readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})
    method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage', readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})
    amount = fields.Float(string='Amount', readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})
    method_client = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                              default='percentage', readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})
    amount_client = fields.Float(string='Amount', readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})

    note = fields.Html(string='Description', readonly=True,
                       states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                               'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})

    # address
    address = fields.Text(tracking=True, readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    street = fields.Char('Street', tracking=True, readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    street_2 = fields.Char('Street2', tracking=True, readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    city = fields.Char('City', tracking=True, readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    state_id = fields.Many2one('res.country.state',string="State", tracking=True, readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    country_id = fields.Many2one('res.country',string="Country", tracking=True, readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    zip_code = fields.Char('Zip', tracking=True, readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})
    
    # tab project details

    warehouse_address = fields.Many2one('stock.warehouse', string='Warehouse Address', readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)], 'quotation_approved': [('readonly', False)]})

    contract_category = fields.Selection([
                        ('main', 'Main Contract'),
                        ('var', 'Variation Order')
                        ],string="Contract Category", default='main', required=True)
    main_contract_ref = fields.Many2one('sale.order.const', string="Main Contract")
    vo_payment_type = fields.Selection([
                        ('join', 'Join Payment'),
                        ('split', 'Split Payment')
                        ], string="Payment Method")
    contract_parent = fields.Many2one('sale.order.const', string="Parent Contract")
    start_date = fields.Date(string="Planned Start Date", readonly=True,
                    states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                           'over_limit_approved': [('readonly', False)]}) 
    end_date = fields.Date(string="Planned End Date", readonly=True,
                    states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                           'over_limit_approved': [('readonly', False)]}) 
    contract_amount = fields.Float(string="Contract Amount", compute="_compute_amount")
    contract_amount1 = fields.Float(related='contract_amount', store=True)
    down_payment = fields.Float(string="Down Payment")
    dp_method = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Down Payment Method", default='per')
    dp_amount = fields.Float(string="Down Payment Amount", compute="_compute_total_downpayment")
    retention1 = fields.Float(string="Retention 1 (%)")
    retention1_amount = fields.Float(string="Retention 1 Amount", compute="_compute_total_retention1")
    retention1_date = fields.Date(string="Retention 1 Date")
    retention2 = fields.Float(string="Retention 2 (%)")
    retention2_amount = fields.Float(string="Retention 2 Amount", compute="_compute_total_retention2")
    retention2_date = fields.Date(string="Retention 2 Date")
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=[('active', '=', True), ('type_tax_use', '=', 'sale')])
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    retention_term_1 = fields.Many2one(
        'retention.term', string='Retention 1 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    retention_term_2 = fields.Many2one(
        'retention.term', string='Retention 2 Term', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")    
    
    
    order_line_ids = fields.One2many('sale.order.line.const', 'order_id', string='Order Lines', copy=True, auto_join=True)
    
    labour_line_ids = fields.One2many('sale.order.labour.line', 'order_id', string='Labour Lines', copy=True,
                                      auto_join=True)
    overhead_line_ids = fields.One2many('sale.order.overhead.line', 'order_id', string='Overhead Lines', copy=True,
                                      auto_join=True)
    subcon_line_ids = fields.One2many('sale.order.subcon.line', 'order_id', string='Subcon Lines', copy=True,
                                        auto_join=True)
    material_line_ids = fields.One2many('sale.order.material.line', 'order_id', string='Material Lines', copy=True,
                                        auto_join=True)
    equipment_line_ids = fields.One2many('sale.order.equipment.line', 'order_id', string='Equipment Lines', copy=True,
                                        auto_join=True)
    internal_asset_line_ids = fields.One2many('sale.internal.asset.line', 'order_id', string='Internal Asset Lines', copy=True,
                                        auto_join=True)

    project_scope_ids = fields.One2many('scope.order.line', 'order_id')
    section_ids = fields.One2many('section.order.line', 'order_id')
    variable_ids = fields.One2many('variable.order.line', 'order_id')

    scope_adjustment_ids = fields.One2many('scope.adjustment', 'order_id')
    section_adjustment_ids = fields.One2many('section.adjustment', 'order_id')
    scope_discount_ids = fields.One2many('scope.discount', 'order_id')
    section_discount_ids = fields.One2many('section.discount', 'order_id')
    note = fields.Text(string="Term and Conditions...")
    adjustment_method_global = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method", readonly=True,
                        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                'over_limit_approved': [('readonly', False)]})
    adjustment_amount_global = fields.Float(string="Adjustment Amount", readonly=True,
                                states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})
    discount_method_global = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method", readonly=True,
                        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                'over_limit_approved': [('readonly', False)]})
    discount_amount_global = fields.Float(string="Discount Amount", readonly=True,
                            states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                    'over_limit_approved': [('readonly', False)]})
    
    total_material = fields.Float(string="Total Material", compute="_compute_amount")
    total_labour = fields.Float(string="Total Labour", compute="_compute_amount")
    total_overhead = fields.Float(string="Total Overhead", compute="_compute_amount")
    total_internal_asset = fields.Float(string="Total Internal Asset", compute="_compute_amount")
    total_equipment = fields.Float(string="Total Equipment", compute="_compute_amount")
    total_asset = fields.Float(string="Total Asset", compute="_compute_amount")
    total_subcon = fields.Float(string="Total Subcon", compute="_compute_amount")
    
    amount_untaxed = fields.Float(string="Amount Before Adjustment", compute="_compute_amount")
    adjustment_sub = fields.Float(string="Global Adjustment (+)", compute="_compute_amount")
    discount_sub = fields.Float(string="Global Discount (-)", compute="_compute_amount")
    line_adjustment = fields.Float(string="LIne Adjustment (+)")
    line_discount = fields.Float(string="Line Discount (-)")
    
    adjustment_scope = fields.Float(string="Scope Adjustment (+)")
    discount_scope = fields.Float(string="Scope Discount (-)")
    adjustment_section = fields.Float(string="Section Adjustment (+)")
    discount_section = fields.Float(string="Section Discount (-)")

    adjustment_variable = fields.Float(string="Variable Adjustment (+)")
    discount_variable = fields.Float(string="Variable Discount (-)")

    amount_tax = fields.Float(string="Taxes", compute="_compute_amount")
    amount_total = fields.Float(string="Total", compute="_compute_amount")
    amount_total_rel = fields.Float(related='amount_total', string="Total", store=True)

    is_set_adjustment_sale = fields.Boolean(string='Advance Adjustment Calculation', default=False, readonly=True,
                        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                'over_limit_approved': [('readonly', False)]})

    #sale term and condition
    terms_conditions_id = fields.Many2one('sale.terms.and.conditions', string='Terms and Conditions', readonly=True,
                          states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                                        'over_limit_approved': [('readonly', False)]})

    state_1 = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('to_approve', 'Waiting For Approval'),
        ('quotation_approved', 'Quotation Approved'),
        ('sale', 'Sales Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('reject', 'Quotation Rejected')
        ], string='Status', readonly=True, copy=False, index=True, default='draft')
    sale_state = fields.Selection([
        ('pending', 'Pending'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ] ,string="Sale State", default='pending')
    sale_state_const = fields.Selection(related='sale_state')
    sale_state_1 = fields.Selection(related='sale_state')
    related_contract_ids = fields.Many2many("sale.order.const",
                                         relation="related_contract_rel_id",
                                         column1="so_id",
                                         column2="contract_id",
                                         string="")
    count_contract = fields.Integer(compute="_compute_count_contract")
    year = fields.Char(string="Year")
    department_type = fields.Selection(related="project_id.department_type", string='Type of Project')
    total_variation_order_material = fields.Monetary(string='Total Variation Order Material',)
    total_variation_order_labour = fields.Monetary(string='Total Variation Order Labour', )
    total_variation_order_overhead = fields.Monetary(string='Total Variation Order Overhead',)
    total_variation_order_asset = fields.Monetary(string='Total Variation Order Internal Asset',)
    total_variation_order_equipment = fields.Monetary(string='Total Variation Order Equipment',)
    total_variation_order_subcon = fields.Monetary(string='Total Variation Order Subcon', )
    total_variation_order = fields.Monetary(string="Total Variation Order", store=True)
    amount_total_variation_order = fields.Monetary(string="Total Variation Order (Adjusted)", compute="_compute_amount")
    is_over_budget_ratio = fields.Boolean(string="Over Budget Ratio")
    ratio_value = fields.Float(string="Ratio Value(%)")

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(SaleOrderConst, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)

        if res.get('toolbar', False) and res.get('toolbar').get('print', False):
            reports = res.get('toolbar').get('print')
            for report in reports:
                res['toolbar']['print'].remove(report)

        return res    
    
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('project_id.id','in',self.env.user.project_ids.ids))
        
        return super(SaleOrderConst, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('project_id.id','in',self.env.user.project_ids.ids))
            
        return super(SaleOrderConst, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', 'in', ('draft','progress')), ('company_id', '=', rec.company_id.id),('id', 'in', self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', 'in', ('draft','progress')), ('company_id', '=', rec.company_id.id),('id', 'in', self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', 'in', ('draft','progress')), ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', 'in', ('draft','progress')), ('company_id', '=', rec.company_id.id)]}
                    }

    @api.onchange('start_date')
    def onchange_year(self):
        if self.start_date:
            start_date = datetime.strptime(str(self.start_date), DEFAULT_SERVER_DATE_FORMAT)
            year_date = start_date.strftime("%Y")

            self.write({
                    "year": year_date
                })

    def _compute_count_contract(self):
        for res in self:
            contract = self.env['sale.order.const'].search_count([('contract_parent', '=', res.id), ('project_id', '=', res.project_id.id), ('state', 'in', ('sale','done'))])
            res.count_contract = contract
    
    def _period_values(self):
        return {
            'name': self.project_id.name,
            'project': self.project_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'branch_id': self.branch_id.id,
        }

    def _create_budget_period(self, budget_period):
        budget_period = self.env['project.budget.period'].create(self._period_values())
        return budget_period                

    def _onchange_so(self):
        return {
            'date_order': datetime.now(),
            'state': 'sale',
            'state_1': 'sale',
            'sale_state': 'progress'
        }
    
    def _onchange_job_ref(self):
        return {
            'state':'sale',
        }
    
    def _onchange_project_false(self):
        return {
            'project_scope_ids': False,
            'project_section_ids': False,
        }
    
    def _send_contract(self):
        return {
            'contract_parent': self.id,
            'related_contract_ids': [(6, 0, self.ids)],
            }
    
    def _send_project(self, scope_list, section_list):
        return {
            'start_date' : self.start_date,
            'end_date' : self.end_date,
            'partner_id' : self.partner_id.id,
            'customer_ref' : self.client_order_ref,
            'analytic_idz' : [(6, 0, [v.id for v in self.analytic_idz])],
            'primary_states' : 'progress',
            'sale_order_main': self.id,
            'address': self.address,
            'street': self.street,
            'street_2': self.street_2,
            'city': self.city,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
            'zip_code': self.zip_code, 
            'diff_penalty': self.diff_penalty,
            'amount': self.amount,
            'method': self.method,
            'amount_client': self.amount_client,
            'method_client': self.method_client,
            'project_scope_ids': scope_list,
            'project_section_ids': section_list,
            }

    def _method_budget_period(self):
            budget_period = False
            budget_period = self._create_budget_period(budget_period)
            budget_period.sudo().action_create_period()
            budget_period.sudo().action_open()
    
    def _send_contract_var(self):
        def _var_contract_variable(con):
            return {
                'name':  self.id,
                'order_date': datetime.now(),
                'contract_amount': con.contract_amount,
                'dp_method': con.dp_method,
                'down_payment': con.down_payment,
                'dp_amount': con.dp_amount,
                'retention1': con.retention1,
                'retention1_amount': con.retention1_amount,
                'retention1_date': con.retention1_date,
                'retention_term_1': con.retention_term_1.id,
                'retention2': con.retention2,
                'retention2_amount': con.retention2_amount,
                'retention2_date': con.retention2_date,
                'retention_term_2': con.retention_term_2.id,
                'tax_id': [(6, 0, [v.id for v in con.tax_id])],
                'payment_term': con.payment_term_id.id,
                'vo_payment_type': con.vo_payment_type,                
                'diff_penalty': con.diff_penalty,
                'amount': con.amount,
                'method': con.method,
                'amount_client': con.amount_client,
                'method_client': con.method_client,
                }
        
        contract_list = []
        for con in self:
            contract_list.append(
                (0, 0, _var_contract_variable(con)))
        return contract_list
    
    def _split_payment_type(self, contract_list):            
        self.write({'contract_parent': self.id,
                    'related_contract_ids': [(6, 0, self.ids)],
                })

        self.project_id.write({
            'variation_order_ids' : contract_list,
        })

    def _join_payment_type(self, contract_list):        
        if self.contract_parent:
            res = self.contract_parent
            res.write({'related_contract_ids' : [(4, self.id)]})
        
        self.project_id.write({
            'variation_order_ids' : contract_list,
        })
    
    def _button_confirm_contd(self):
        
        self.write(self._onchange_so())
        self.job_references.write(self._onchange_job_ref())
        
        if self.contract_category == 'main':   
            
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
                    'section': section.section.id,
                    'description': section.description,
                    'quantity': section.quantity,
                    'uom_id': section.uom_id.id,
                    })
                )
            
            if self.opportunity_id:
                self.opportunity_id.stage_id = 4
            self.project_id.write(self._onchange_project_false())
            self.write(self._send_contract())
            self.project_id.write(self._send_project(scope_list, section_list))
            self.project_id.sudo()._onchange_sale_order_main()
            self.project_id.sudo()._inprogress_project_warehouse()
            self._method_budget_period()
            
            for sale in self:
                except_main = self.env['sale.order.const'].search([('project_id', '=', sale.project_id.id), 
                                                                ('contract_category', '=', 'main'), 
                                                                ('id', '!=', sale.id)])
                if except_main:
                    for res in except_main:
                        res.write({'state' : 'block'})
                else:
                    pass

        elif self.contract_category == 'var':
            
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
            
            contract_list = self._send_contract_var()
            self.project_id.write({
                    'project_scope_ids': scope_list,
                    'project_section_ids': section_list,
                })

            if self.vo_payment_type == 'split':   
                self._split_payment_type(contract_list)

            if self.vo_payment_type == 'join': 
                self._join_payment_type(contract_list)
                                
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.write({'sale_state': 'progress'})
            keep_name_so = IrConfigParam.get_param('keep_name_so', False)
            if not keep_name_so:
                if record.origin:
                    record.origin += "," + record.name
                else:
                    record.origin = record.name
                record.name = self.env['ir.sequence'].next_by_code('sale.order.quotation.order.const')
        return
    
    def button_confirm(self):
        if self.adjustment_sub == 0 and self.contract_amount1 > 0:
            raise ValidationError(_("You haven't set Adjustment (Mark Up) for this contract"))
        
        if self.retention1 > 0 and not self.retention_term_1:
            raise ValidationError(_("You haven't set Retention 1 Term for this contract"))
        
        if self.retention2 > 0 and not self.retention_term_2:
            raise ValidationError(_("You haven't set Retention 2 Term for this contract"))
        
        if self.use_dp == True and self.down_payment == 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirmation',
                'res_model': 'confirm.downpayment',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                }
        elif self.use_retention == True and self.retention1 == 0:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'confirm.retention',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }
        else:
            self._button_confirm_contd()

    
    def action_project(self):
        action = self.project_id.get_formview_action()
        action['domain'] = [('id', '=', self.project_id.id)]
        return action

    def action_close_budget_period(self):
        filtered_proj_budget_period = self.env['project.budget.period'].search([('project','=', self.project_id.id)])
        if filtered_proj_budget_period:
            for rec in filtered_proj_budget_period:       
                rec.sudo().action_closed()

    def button_cancel(self):
        for res in self:
            res.write({'state': 'cancel'})

            if res.job_references:
                for job in res.job_references:
                    job.write({
                        'state':'quotation_cancel',
                        'sale_state':'canceled',
                    })
            # res.action_close_budget_period()

    def action_boq_revision(self):
        for res in self:
            if res.job_references:
                for job in res.job_references:
                    job.action_boq_revision(job,default=None)
                res.write({'boq_revised_bool': True})

    def _comute_revision_boq(self):
        for res in self:
            if res.job_references:
                for job in res.job_references:
                    boq_count = self.env['job.estimate'].search_count([('project_id', '=', res.project_id.id), ('revision_je_id', '=', job.id)])
                res.total_boq_revision += boq_count
            else:
                res.total_boq_revision = 0

    def action_revision_boq_view(self):
        for res in self:
            if res.job_references:
                for job in res.job_references:
                    domain = [('project_id', '=', res.project_id.id), ('revision_je_id', '=', job.id)]
            else:
                domain = []
        
        return {
            'name': ("BOQ Revision"),
            'view_mode': 'tree,form',
            'res_model': 'job.estimate',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
        }

    def button_create_invoice(self):
        return

    def button_done(self):
        if self.sale_state == 'done':
            self.state='done'
        else:
            raise ValidationError("You have an unfinished invoice")
    
    @api.depends('dp_method','down_payment', 'contract_amount')
    def _compute_total_downpayment(self):
        for res in self:
            if res.dp_method == 'per':
                res.dp_amount = res.contract_amount * (res.down_payment / 100)
            elif res.dp_method == 'fix':
                res.dp_amount = res.down_payment
            else:
                res.dp_amount = 0

    @api.depends('retention1', 'contract_amount')
    def _compute_total_retention1(self):
        for res in self:
            res.retention1_amount = res.contract_amount * (res.retention1 / 100)

    @api.depends('retention2', 'contract_amount')
    def _compute_total_retention2(self):
        for res in self:
            res.retention2_amount = res.contract_amount * (res.retention2 / 100)
    
    @api.depends('contract_amount')
    def _compute_contract_amount(self):
        for res in self:
            res.contract_amount1 = res.contract_amount
            res.amount_total_rel = res.amount_total

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Sales Team
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'fiscal_position_id': False,
            })
            return

        self = self.with_company(self.company_id)

        addr = self.partner_id.address_get(['invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
        }
        self.update(values)

    @api.depends('state')
    def _compute_type_name(self):
        for record in self:
            record.type_name = _('Quotation') if record.state in ('draft', 'sent', 'cancel') else _('Sales Order')

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete this quotation or contract. You must set to quotation (draft) or cancel it first.'))
        return super(SaleOrderConst, self).unlink()


    def _get_default_require_signature(self):
        return self.env.company.portal_confirmation_sign

    def _get_default_require_payment(self):
        return self.env.company.portal_confirmation_pay
    
    def _compute_is_expired(self):
        today = fields.Date.today()
        for order in self:
            order.is_expired = order.state == 'sent' and order.validity_date and order.validity_date < today

    @api.depends('is_set_adjustment_sale',
        'material_line_ids','labour_line_ids','overhead_line_ids','subcon_line_ids', 'equipment_line_ids', 'internal_asset_line_ids',
        'adjustment_type', 'adjustment_method_global', 'adjustment_amount_global', 'discount_method_global', 'discount_amount_global', 'discount_type',
        'project_scope_ids','section_ids','variable_ids')
    def _compute_amount(self):
        for record in self:
            record.contract_amount = 0
            record.total_material       = sum(record.material_line_ids.mapped('subtotal'))
            record.total_labour         = sum(record.labour_line_ids.mapped('subtotal'))
            record.total_overhead       = sum(record.overhead_line_ids.mapped('subtotal'))
            record.total_internal_asset = sum(record.internal_asset_line_ids.mapped('subtotal'))
            record.total_equipment      = sum(record.equipment_line_ids.mapped('subtotal'))
            record.total_subcon         = sum(record.subcon_line_ids.mapped('subtotal'))
            record.total_asset          = sum(record.internal_asset_line_ids.mapped('subtotal')) + sum(record.equipment_line_ids.mapped('subtotal'))

            record.amount_untaxed = sum([sum(record[x].mapped('subtotal')) for x in ESTIMATES])
            record.adjustment_sub = 0
            record.discount_sub = 0

            record.amount_tax = 0
            record.amount_total = 0
            
            record._set_tax_id_lines()
            # ADJUSTMENT
            if record.adjustment_type == 'global' :
                total_scope = sum(record.project_scope_ids.mapped('subtotal_scope'))
                if record.adjustment_method_global == 'fix':
                    record.adjustment_sub = record.adjustment_amount_global
                else:
                    record.adjustment_sub = record.amount_untaxed * (record.adjustment_amount_global / 100)
                    if record.is_set_adjustment_sale:
                        record.adjustment_sub = (record.amount_untaxed / (1 - record.adjustment_amount_global / 100)) - record.amount_untaxed

                
                for scope in record.project_scope_ids:
                    ratio = scope.subtotal_scope / total_scope if total_scope else 0
                    scope.scope_adjustment = record.adjustment_sub * ratio

                    for section in record.section_ids.filtered(lambda x: x.project_scope.id == scope.project_scope.id):
                        ratio = section.subtotal_section / scope.subtotal_scope if scope.subtotal_scope else 0
                        section.section_adjustment = scope.scope_adjustment * ratio
                        for estimate in ESTIMATES:
                            for item in record[estimate].filtered(lambda x: (x.project_scope.id == section.project_scope.id) and (x.section_name.id == section.section.id)):
                                ratio = item.subtotal / section.subtotal_section if section.subtotal_section else 0
                                item.adjustment_line = section.section_adjustment * ratio

            elif record.adjustment_type == 'scope':
                for scope in record.project_scope_ids:
                    if scope.adjustment_method_scope == 'fix':
                        scope.scope_adjustment = scope.adjustment_amount_scope
                    else:
                        scope.scope_adjustment = scope.subtotal_scope * (scope.adjustment_amount_scope/100)
                        if record.is_set_adjustment_sale:
                            scope.scope_adjustment = (scope.subtotal_scope / (1 - scope.adjustment_amount_scope / 100)) - scope.subtotal_scope

                    for section in record.section_ids.filtered(lambda x: x.project_scope.id == scope.project_scope.id):
                        ratio = section.subtotal_section / scope.subtotal_scope if scope.subtotal_scope else 0
                        section.section_adjustment = scope.scope_adjustment * ratio
                        for estimate in ESTIMATES:
                            for item in record[estimate].filtered(lambda x: (x.project_scope.id == section.project_scope.id) and (x.section_name.id == section.section.id)):
                                ratio = item.subtotal / section.subtotal_section if section.subtotal_section else 0
                                item.adjustment_line = section.section_adjustment * ratio
            
            elif record.adjustment_type == 'section':
                for section in record.section_ids:
                    if section.adjustment_method_section == 'fix':
                        section.section_adjustment = section.adjustment_amount_section
                    else:
                        section.section_adjustment = section.subtotal_section * (section.adjustment_amount_section / 100)
                        if record.is_set_adjustment_sale:
                            section.section_adjustment = (section.subtotal_section / (1 - section.adjustment_amount_section / 100)) - section.subtotal_section

                    for estimate in ESTIMATES:
                        for item in record[estimate].filtered(lambda x: (x.project_scope.id == section.project_scope.id) and (x.section_name.id == section.section.id)):
                            ratio = item.subtotal / section.subtotal_section if section.subtotal_section else 0
                            item.adjustment_line = section.section_adjustment * ratio

                for scope in record.project_scope_ids:
                    scope.scope_adjustment = sum(record.section_ids.filtered(lambda x: x.project_scope.id == scope.project_scope.id ).mapped('section_adjustment'))
            
            elif record.adjustment_type == 'line':
                for estimate in ESTIMATES:
                    for item in record[estimate]:
                        if item.adjustment_method_line == 'fix':
                            item.adjustment_line = item.adjustment_amount_line  
                        else:
                            item.adjustment_line = item.subtotal * (item.adjustment_amount_line / 100)
                            if record.is_set_adjustment_sale:
                                item.adjustment_line = (item.subtotal / (1 - item.adjustment_amount_line / 100)) - item.subtotal

                for section in record.section_ids:
                    section.section_adjustment = sum([sum(record[x].filtered(lambda x: (x.project_scope.id == section.project_scope.id) and (x.section_name.id == section.section.id)).mapped('adjustment_line')) for x in ESTIMATES])

                for scope in record.project_scope_ids:
                    scope.scope_adjustment = sum(record.section_ids.filtered(lambda x: x.project_scope.id == scope.project_scope.id ).mapped('section_adjustment'))
            # ADJUSTMENT
            # DISCOUNT
            if record.discount_type == 'global' :
                total_scope = sum(record.project_scope_ids.mapped('subtotal_scope'))
                if record.discount_method_global == 'fix':
                    record.discount_sub = record.discount_amount_global
                else:
                    record.discount_sub = record.amount_untaxed * (record.discount_amount_global / 100)
                
                for scope in record.project_scope_ids:
                    ratio = scope.subtotal_scope / total_scope if total_scope else 0
                    scope.scope_discount = record.discount_sub * ratio

                    for section in record.section_ids.filtered(lambda x: x.project_scope.id == scope.project_scope.id):
                        ratio = section.subtotal_section / scope.subtotal_scope if scope.subtotal_scope else 0
                        section.section_discount = scope.scope_discount * ratio
                        for estimate in ESTIMATES:
                            for item in record[estimate].filtered(lambda x: (x.project_scope.id == section.project_scope.id) and (x.section_name.id == section.section.id)):
                                ratio = item.subtotal / section.subtotal_section if section.subtotal_section else 0
                                item.discount_line = section.section_discount * ratio

            elif record.discount_type == 'scope':
                for scope in record.project_scope_ids:
                    if scope.discount_method_scope == 'fix':
                        scope.scope_discount = scope.discount_amount_scope
                    else:
                        scope.scope_discount = scope.subtotal_scope * (scope.discount_amount_scope/100)

                    for section in record.section_ids.filtered(lambda x: x.project_scope.id == scope.project_scope.id):
                        ratio = section.subtotal_section / scope.subtotal_scope if scope.subtotal_scope else 0
                        section.section_discount = scope.scope_discount * ratio
                        for estimate in ESTIMATES:
                            for item in record[estimate].filtered(lambda x: (x.project_scope.id == section.project_scope.id) and (x.section_name.id == section.section.id)):
                                ratio = item.subtotal / section.subtotal_section if section.subtotal_section else 0
                                item.discount_line = section.section_discount * ratio
            
            elif record.discount_type == 'section':
                for section in record.section_ids:
                    if section.discount_method_section == 'fix':
                        section.section_discount = section.discount_amount_section
                    else:
                        section.section_discount = section.subtotal_section * (section.discount_amount_section / 100)

                    for estimate in ESTIMATES:
                        for item in record[estimate].filtered(lambda x: (x.project_scope.id == section.project_scope.id) and (x.section_name.id == section.section.id)):
                            ratio = item.subtotal / section.subtotal_section if section.subtotal_section else 0
                            item.discount_line = section.section_discount * ratio

                for scope in record.project_scope_ids:
                    scope.scope_discount = sum(record.section_ids.filtered(lambda x: x.project_scope.id == scope.project_scope.id ).mapped('section_discount'))
            
            elif record.discount_type == 'line':
                for estimate in ESTIMATES:
                    for item in record[estimate]:
                        if item.discount_method_line == 'fix':
                            item.discount_line = item.discount_amount_line  
                        else:
                            item.discount_line = item.subtotal * (item.discount_amount_line / 100)

                for section in record.section_ids:
                    section.section_discount = sum([sum(record[x].filtered(lambda x: (x.project_scope.id == section.project_scope.id) and (x.section_name.id == section.section.id)).mapped('discount_line')) for x in ESTIMATES])

                for scope in record.project_scope_ids:
                    scope.scope_discount = sum(record.section_ids.filtered(lambda x: x.project_scope.id == scope.project_scope.id ).mapped('section_discount'))
            # DISCOUNT
            
            for estimate in ESTIMATES:
                for item in record[estimate]:
                    item.amount_line = item.subtotal + item.adjustment_line - item.discount_line
                    item.total_amount = item.amount_line + item.amount_tax_line
            
            for section in record.section_ids:
                section.amount_line = section.subtotal_section + section.section_adjustment - section.section_discount

            for scope in record.project_scope_ids:
                scope.amount_line = scope.subtotal_scope + scope.scope_adjustment - scope.scope_discount
            
            record.adjustment_sub = sum(record.project_scope_ids.mapped('scope_adjustment'))
            record.discount_sub = sum(record.project_scope_ids.mapped('scope_discount'))
            record.contract_amount = record.amount_untaxed + record.adjustment_sub - record.discount_sub 
            record.amount_total = record.contract_amount + record.amount_tax

            if record.amount_untaxed > 0:
                total_variation_order_adjustment_sub = (record.total_variation_order * (record.adjustment_sub / record.amount_untaxed))
                total_variation_order_discount_sub = (record.total_variation_order * (record.discount_sub / record.amount_untaxed))
                record.amount_total_variation_order = record.amount_total - (record.amount_total - (record.total_variation_order + total_variation_order_adjustment_sub - total_variation_order_discount_sub))
            else:
                record.amount_total_variation_order = 0

            return record.amount_total

    @api.depends('material_line_ids.amount_line', 'labour_line_ids.amount_line', 'overhead_line_ids.amount_line', 
                 'subcon_line_ids.amount_line', 'equipment_line_ids.amount_line', 'internal_asset_line_ids.amount_line',
                 'material_line_ids.line_tax_id', 'labour_line_ids.line_tax_id', 'overhead_line_ids.line_tax_id', 
                 'subcon_line_ids.line_tax_id', 'equipment_line_ids.line_tax_id', 'internal_asset_line_ids.line_tax_id')
    def _set_tax_id_lines(self):
        for res in self:
            for line1 in res.material_line_ids:
                line_tax_id_amount1 = 0
                for tax_line1 in line1.line_tax_id:
                    line_tax_id_amount1 += tax_line1.amount
                line_amount_tax_line1 = line1.amount_line * (line_tax_id_amount1 / 100)
                line1.sudo().write({'amount_tax_line': line_amount_tax_line1})
            for line2 in res.labour_line_ids:
                line_tax_id_amount2 = 0
                for tax_line2 in line2.line_tax_id:
                    line_tax_id_amount2 += tax_line2.amount
                line_amount_tax_line2 = line2.amount_line * (line_tax_id_amount2 / 100)
                line2.sudo().write({'amount_tax_line': line_amount_tax_line2})
            for line3 in res.overhead_line_ids:
                line_tax_id_amount3 = 0
                for tax_line3 in line3.line_tax_id:
                    line_tax_id_amount3 += tax_line3.amount
                line_amount_tax_line3 = line3.amount_line * (line_tax_id_amount3 / 100)
                line3.sudo().write({'amount_tax_line': line_amount_tax_line3})
            for line4 in res.internal_asset_line_ids:
                line_tax_id_amount4 = 0
                for tax_line4 in line4.line_tax_id:
                    line_tax_id_amount4 += tax_line4.amount
                line_amount_tax_line4 = line4.amount_line * (line_tax_id_amount4 / 100)
                line4.sudo().write({'amount_tax_line': line_amount_tax_line4})
            for line5 in res.equipment_line_ids:
                line_tax_id_amount5 = 0
                for tax_line5 in line5.line_tax_id:
                    line_tax_id_amount5 += tax_line5.amount
                line_amount_tax_line5 = line5.amount_line * (line_tax_id_amount5 / 100)
                line5.sudo().write({'amount_tax_line': line_amount_tax_line5})
            for line6 in res.subcon_line_ids:
                line_tax_id_amount6 = 0
                for tax_line6 in line6.line_tax_id:
                    line_tax_id_amount6 += tax_line6.amount
                line_amount_tax_line6 = line6.amount_line * (line_tax_id_amount6 / 100)
                line6.sudo().write({'amount_tax_line': line_amount_tax_line6})

        for order in self:
            order.amount_tax = sum(order.material_line_ids.mapped('amount_tax_line')) + sum(order.labour_line_ids.mapped('amount_tax_line')) + sum(order.overhead_line_ids.mapped('amount_tax_line')) + sum(order.subcon_line_ids.mapped('amount_tax_line')) + sum(order.internal_asset_line_ids.mapped('amount_tax_line')) + sum(order.equipment_line_ids.mapped('amount_tax_line'))

    @api.onchange('terms_conditions_id')
    def _onchange_terms_conditions_id(self):
        if self.terms_conditions_id:
            self.note = self.terms_conditions_id.terms_and_conditions

    def action_set_quotation(self):
        for record in self:
            record.sale_order_const_user_ids = [(5, 0, 0)]
            record.write({'state': 'draft',
                          'state_1': 'draft', 
                          'sale_state': 'pending', 
                          'sale_state_1': 'pending',
                          'use_retention': True,
                          'use_dp': True,
                          'boq_revised_bool': False,
                          'approved_user_ids': False,
                          'approved_user': False,
                         })

            if record.job_references:
                for job in record.job_references:
                    job.write({
                        'state':'done',
                        'sale_state':'quotation',
                    })
                
            record.onchange_approving_matrix_lines()


    @api.model
    def _action_sale_order_cancel(self):
        today_date = date.today()
        sale_order_ids = self.search([('validity_date', '<', today_date), ('state', 'in', ('draft', 'sent'))])
        sale_order_ids.write({'sale_state': 'cancel', 'state': 'cancel'})

    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 
                            'sent', 'reject'])
        return orders.write({
            'state': 'draft',
            'signature': False,
            'signed_by': False,
            'signed_on': False,
        })

    def action_done(self):
        for res in self:
            res.write({'state': 'done',
                        'sale_state': 'done', 
                         })

    @api.onchange('partner_id')
    def _set_domain_partner_invoice_id(self):
        b = {}
        if self.partner_id:
            partner_inv_ids = self.env['res.partner'].search([('parent_id', '=', self.partner_id.id), ('type', '=', 'invoice')]).ids
            b = {'domain': {'partner_invoice_id': [('id', 'in', partner_inv_ids)]}}
        return b

    # sales
    user_id = fields.Many2many(
        'res.users', 'sales_const_id', string='Salesperson', index=True, tracking=2, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        change_default=True, check_company=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company, readonly=True)
    require_signature = fields.Boolean('Online Signature', default=_get_default_require_signature, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help='Request a online signature to the customer in order to confirm orders automatically.')
    require_payment = fields.Boolean('Online Payment', default=_get_default_require_payment, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help='Request an online payment to the customer in order to confirm orders automatically.')
    client_order_ref = fields.Char(string='Customer Reference', copy=False)
    tag_ids = fields.Many2many('crm.tag', string='Tags')
    report_grids = fields.Boolean(string="Print Variant Grids", default=True)

    # invoicing
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Fiscal Position',
        domain="[('company_id', '=', company_id)]", check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices."
        "The default value comes from the customer.")
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account',
        readonly=True, copy=False, check_company=True,  # Unrequired company
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="The analytic account related to a sales order.")

    # branch
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])

    
    # Pricelist
    show_update_pricelist = fields.Boolean(string='Has Pricelist Changed',
                                           help="Technical Field, True if the pricelist was changed;\n"
                                                " this will then display a recomputation button")
    
    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        if self.material_line_ids  or self.labour_line_ids or self.overhead_line_ids or self.equipment_line_ids:
            if self.pricelist_id and self._origin.pricelist_id != self.pricelist_id:
                self.show_update_pricelist = True
            else:
                self.show_update_pricelist = False
    
    def update_prices(self):
        self.ensure_one()
        lines_to_update_material = []
        lines_to_update_labour = []
        lines_to_update_overhead = []
        lines_to_update_equipment = []

        for material in self.material_line_ids:
            product = material.material_id.with_context(
                partner=self.partner_id,
                quantity=material.quantity,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=material.uom_id.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                material._get_display_price(product), material.material_id.taxes_id, material.line_tax_id, material.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                discount = max(0, (price_unit - product.price) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update_material.append((1, material.id, {'unit_price': price_unit, 'discount': discount}))
        
        for labour in self.labour_line_ids:
            product = labour.labour_id.with_context(
                partner=self.partner_id,
                quantity=labour.quantity,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=labour.uom_id.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                labour._get_display_price(product), labour.labour_id.taxes_id, labour.line_tax_id, labour.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                discount = max(0, (price_unit - product.price) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update_labour.append((1, labour.id, {'unit_price': price_unit, 'discount': discount}))

        for overhead in self.overhead_line_ids:
            product = overhead.overhead_id.with_context(
                partner=self.partner_id,
                quantity=overhead.quantity,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=overhead.uom_id.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                overhead._get_display_price(product), overhead.overhead_id.taxes_id, overhead.line_tax_id, overhead.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                discount = max(0, (price_unit - product.price) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update_overhead.append((1, overhead.id, {'unit_price': price_unit, 'discount': discount}))

        for equipment in self.equipment_line_ids:
            product = equipment.equipment_id.with_context(
                partner=self.partner_id,
                quantity=equipment.quantity,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=equipment.uom_id.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                equipment._get_display_price(product), equipment.equipment_id.taxes_id, equipment.line_tax_id, equipment.company_id)
            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                discount = max(0, (price_unit - product.price) * 100 / price_unit)
            else:
                discount = 0
            lines_to_update_equipment.append((1, equipment.id, {'unit_price': price_unit, 'discount': discount}))


        
        self.update({'material_line_ids': lines_to_update_material,
                     'labour_line_ids': lines_to_update_labour,
                     'overhead_line_ids': lines_to_update_overhead,
                     'equipment_line_ids': lines_to_update_equipment})
        self.show_update_pricelist = False
        self.message_post(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ", self.pricelist_id.display_name))


    # reporting
    origin = fields.Char(string='Source Document', help="Reference of the document that generated this sales order request.")
    opportunity_id = fields.Many2one('crm.lead', string="Opportunity")
    campaign_id = fields.Many2one('utm.campaign', string="Campaign")
    medium_id = fields.Many2one('utm.medium', string="Medium")
    source_id = fields.Many2one('utm.source', string="Source")
    
    # tab customer signature
    signature = fields.Image('Signature', help='Signature received through the portal.', copy=False, attachment=True, max_width=1024, max_height=1024)
    signed_by = fields.Char('Signed By', help='Name of the person that signed the SO.', copy=False)
    signed_on = fields.Datetime('Signed On', help='Date of the signature.', copy=False)

    #tab sale order approval matrix line
    approval_matrix_state = fields.Selection(related='state', tracking=False)
    approval_matrix_state_1 = fields.Selection(related='state', tracking=False)
    approval_matrix_state_const = fields.Selection(related='state', tracking=False)
    approval_matrix_state_1_const = fields.Selection(related='state', tracking=False)
    approving_matrix_sale_id = fields.Many2many('approval.matrix.sale.order.const', string="Approval Matrix", store=True)
    approved_matrix_ids = fields.One2many('approval.matrix.sale.order.lines.const', 'order_id', store=True, string="Approved Matrix")
    is_customer_approval_matrix_const = fields.Boolean(string="Custome Matrix", store=False, compute='_compute_is_customer_approval_matrix')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.sale.order.lines.const', string='Sale Approval Matrix Line', store=False)
    is_quotation_cancel = fields.Boolean(string='Is Quotation Cancel', default=False)

    approving_matrix_cont_id = fields.Many2many('approval.matrix.sale.order.const', 'order_id', string="Approval Matrix",
                                               compute='_compute_approving_customer_matrix', store=True)
    sale_order_const_user_ids = fields.One2many('sale.order.const.approver.user', 'sale_order_const_approver_id',
                                                string='Approver')
    approvers_ids = fields.Many2many('res.users', 'sale_order_const_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    employee_id = fields.Many2one('res.users', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')


    @api.depends('partner_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_customer_approval_matrix_const = IrConfigParam.get_param('is_customer_approval_matrix_const')
        for record in self:
            record.is_customer_approval_matrix_const = is_customer_approval_matrix_const


    @api.depends('project_id', 'branch_id', 'company_id','contract_amount', 'adjustment_sub', 'discount_sub', 'amount_total')
    def _compute_approving_customer_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_contract_amount = IrConfigParam.get_param('is_contract_amount', False)
        is_adjustment_amount = IrConfigParam.get_param('is_adjustment_amount', False)
        is_discount_amount_const = IrConfigParam.get_param('is_discount_amount_const', False)
        contract_sequence = IrConfigParam.get_param('contract_sequence', 0)
        adjustment_sequence = IrConfigParam.get_param('adjustment_sequence', 0)
        discount_sequence_const = IrConfigParam.get_param('discount_sequence_const', 0)
        data = []
        if is_contract_amount:
            data.insert(int(contract_sequence) - 1, 'contract_amt')
        if is_adjustment_amount:
            data.insert(int(adjustment_sequence) - 1, 'adjustment_amt')
        if is_discount_amount_const:
            data.insert(int(discount_sequence_const) - 1, 'discount_amt')
        for record in self:
            total_contract = record.contract_amount
            matrix_ids = []
            if record.is_customer_approval_matrix_const:
                record.approving_matrix_cont_id = False
                for sale_matrix_config in data: 
                    if sale_matrix_config == 'contract_amt':
                        if total_contract >= 0:
                            total_addendum = total_contract
                            matrix_id = self.env['approval.matrix.sale.order.const'].search([('company_id', '=', record.company_id.id),
                                                                                            ('branch_id', '=', record.branch_id.id),
                                                                                            ('project_id', 'in', [record.project_id.id]),
                                                                                            ('config', '=', 'contract_amt'),
                                                                                            ('type_contract', '=', 'addendum'),
                                                                                            ('set_default', '=', False), 
                                                                                            ('minimum_amt', '<=', total_addendum), 
                                                                                            ('maximum_amt', '>=', total_addendum)], limit=1)
                            
                            matrix_id_default = self.env['approval.matrix.sale.order.const'].search([('company_id', '=', record.company_id.id),
                                                                                            ('branch_id', '=', record.branch_id.id),
                                                                                            ('config', '=', 'contract_amt'),
                                                                                            ('type_contract', '=', 'addendum'),
                                                                                            ('set_default', '=', True), 
                                                                                            ('minimum_amt', '<=', total_addendum), 
                                                                                            ('maximum_amt', '>=', total_addendum)], limit=1)
                            
                        else:
                            total_dedendum = total_contract * (-1)
                            matrix_id = self.env['approval.matrix.sale.order.const'].search([('company_id', '=', record.company_id.id),
                                                                                            ('branch_id', '=', record.branch_id.id),
                                                                                            ('project_id', 'in', [record.project_id.id]),
                                                                                            ('config', '=', 'contract_amt'),
                                                                                            ('type_contract', '=', 'dedendum'),
                                                                                            ('set_default', '=', False), 
                                                                                            ('minimum_amt', '<=', total_dedendum), 
                                                                                            ('maximum_amt', '>=', total_dedendum)], limit=1)
                            
                            matrix_id_default = self.env['approval.matrix.sale.order.const'].search([('company_id', '=', record.company_id.id),
                                                                                            ('branch_id', '=', record.branch_id.id),
                                                                                            ('config', '=', 'contract_amt'),
                                                                                            ('type_contract', '=', 'dedendum'),
                                                                                            ('set_default', '=', True), 
                                                                                            ('minimum_amt', '<=', total_dedendum), 
                                                                                            ('maximum_amt', '>=', total_dedendum)], limit=1)
                        
                        if matrix_id:
                            matrix_ids.append(matrix_id.id)
                        else:
                            if matrix_id_default:
                                matrix_ids.append(matrix_id_default.id)
                            

                    elif sale_matrix_config == 'adjustment_amt':
                        matrix_id = self.env['approval.matrix.sale.order.const'].search([('company_id', '=', record.company_id.id),
                                                                                             ('branch_id', '=', record.branch_id.id),
                                                                                             ('project_id', 'in', [record.project_id.id]),
                                                                                             ('config', '=', 'adjustment_amt'), 
                                                                                             ('set_default', '=', False), 
                                                                                             ('minimum_amt', '<=', record.adjustment_sub), 
                                                                                             ('maximum_amt', '>=', record.adjustment_sub)], limit=1)
                        
                        matrix_id_default = self.env['approval.matrix.sale.order.const'].search([('company_id', '=', record.company_id.id),
                                                                                             ('branch_id', '=', record.branch_id.id),
                                                                                             ('config', '=', 'adjustment_amt'), 
                                                                                             ('set_default', '=', True), 
                                                                                             ('minimum_amt', '<=', record.adjustment_sub), 
                                                                                             ('maximum_amt', '>=', record.adjustment_sub)], limit=1)
                        
                        if matrix_id:
                            matrix_ids.append(matrix_id.id)
                        else:
                            if matrix_id_default:
                                matrix_ids.append(matrix_id_default.id)
                        

                    elif sale_matrix_config == 'discount_amt':
                        matrix_id = self.env['approval.matrix.sale.order.const'].search([('company_id', '=', record.company_id.id),
                                                                                             ('branch_id', '=', record.branch_id.id),
                                                                                             ('project_id', 'in', [record.project_id.id]),
                                                                                             ('config', '=', 'discount_amt'),  
                                                                                             ('set_default', '=', False), 
                                                                                             ('minimum_amt', '<=', record.discount_sub), 
                                                                                             ('maximum_amt', '>=', record.discount_sub)], limit=1)
                        
                        matrix_id_default = self.env['approval.matrix.sale.order.const'].search([('company_id', '=', record.company_id.id),
                                                                                             ('branch_id', '=', record.branch_id.id),
                                                                                             ('config', '=', 'discount_amt'),  
                                                                                             ('set_default', '=', True), 
                                                                                             ('minimum_amt', '<=', record.discount_sub), 
                                                                                             ('maximum_amt', '>=', record.discount_sub)], limit=1)
                        
                        if matrix_id:
                            matrix_ids.append(matrix_id.id)
                        else:
                            if matrix_id_default:
                                matrix_ids.append(matrix_id_default.id)
                        

                record.approving_matrix_cont_id = [(6 ,0, matrix_ids)]
            else:
                record.approving_matrix_cont_id = False


    @api.onchange('project_id', 'approving_matrix_cont_id', 'contract_amount', 'adjustment_sub', 'discount_sub', 'amount_total')
    def onchange_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.project_id:
                app_list = []
                if record.state == 'draft' and record.is_customer_approval_matrix_const:
                    record.sale_order_const_user_ids = []
                    for rec in record.approving_matrix_cont_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'user_ids': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                    record.approvers_ids = app_list
                    record.sale_order_const_user_ids = data
                

    def _compute_is_approver(self):
        for record in self:
            if record.approvers_ids:
                current_user = record.env.user
                matrix_line = sorted(record.sale_order_const_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(record.sale_order_const_user_ids)
                if app < a:
                    for line in record.sale_order_const_user_ids[app]:
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
            if len(record.sale_order_const_user_ids) == 0:
                raise ValidationError(
                    _("There's no contract approval matrix for this project with specific amount listed. You have to create it first."))

            if record.adjustment_sub == 0 and record.contract_amount1 > 0:
                raise ValidationError(_("You haven't set Adjustment (Mark Up) for this contract"))
            
            if record.retention1 > 0 and not record.retention_term_1:
                raise ValidationError(_("You haven't set Retention 1 Term for this contract"))
            
            if record.retention2 > 0 and not record.retention_term_2:
                raise ValidationError(_("You haven't set Retention 2 Term for this contract"))
            
            if record.use_dp == True and record.down_payment == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'confirm.downpayment',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    }
            elif record.use_retention == True and record.retention1 == 0:
                return {
                        'type': 'ir.actions.act_window',
                        'name': 'Confirmation',
                        'res_model': 'confirm.retention',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'target': 'new',
                    }
            else:
                record.action_request_for_approving_sale_matrix()


    def action_request_for_approving_sale_matrix(self):
        for record in self:
            action_id = self.env.ref('equip3_construction_sales_operation.quotation_const_action')
            template_id = self.env.ref('equip3_construction_sales_operation.email_template_internal_sale_order_approval_const')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order.const'
            if record.sale_order_const_user_ids and len(record.sale_order_const_user_ids[0].user_ids) > 1:
                for approved_matrix_id in record.sale_order_const_user_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'url' : url,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
            else:
                approver = record.sale_order_const_user_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'url' : url,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
            
            record.write({'employee_id': self.env.user.id,
                          'state': 'to_approve',
                          })

            for line in record.sale_order_const_user_ids:
                line.write({'approver_state': 'draft'})

    def action_confirm_approving_matrix(self):
        sequence_matrix = [data.name for data in self.sale_order_const_user_ids]
        sequence_approval = [data.name for data in self.sale_order_const_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.sale_order_const_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        
        for record in self:
            action_id = self.env.ref('equip3_construction_sales_operation.quotation_const_action')
            template_id = self.env.ref('equip3_construction_sales_operation.email_template_reminder_for_sale_order_approval_const')
            template_app = self.env.ref('equip3_construction_sales_operation.email_template_sale_order_approval_approved')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order.const'
            
            current_user = self.env.uid
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                
            if self.env.user not in record.approved_user_ids:
                if record.is_approver:
                    for line in record.sale_order_const_user_ids:
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

                    matrix_line = sorted(record.sale_order_const_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        ctx = {
                                'email_from' : self.env.user.company_id.email,
                                'email_to' : record.employee_id.email,
                                'date': date.today(),
                                'url' : url,
                            }
                        template_app.sudo().with_context(ctx).send_mail(record.id, True)
                        record.write({'state': 'quotation_approved'})
                        
                    else:
                        record.last_approved = self.env.user.id
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                        for approving_matrix_line_user in matrix_line[0].user_ids:
                            ctx = {
                                'email_from' : self.env.user.company_id.email,
                                'email_to' : approving_matrix_line_user.partner_id.email,
                                'approver_name' : approving_matrix_line_user.name,
                                'date': date.today(),
                                'submitter' : record.last_approved.name,
                                'url' : url,
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
            action_id = self.env.ref('equip3_construction_sales_operation.quotation_const_action')
            template_rej = self.env.ref('equip3_construction_sales_operation.email_template_sale_order_approval_rejected')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order.const'
            for user in record.sale_order_const_user_ids:
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
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.employee_id.email,
                    'date': date.today(),
                    'url' : url,
                }
            template_rej.sudo().with_context(ctx).send_mail(record.id, True)
            record.write({'state': 'reject'})


    def action_reject_approving_matrix(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'Reject Reason',
                'res_model': 'approval.matrix.sale.reject.const',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                }

    contract_template = fields.Many2one('const.contract.letter')
    edit_hide_css = fields.Html(string='CSS', sanitize=False, compute='_compute_edit_hide_css')
    document_attachment = fields.Binary(string='Document Attachment')
    document_attachment_fname = fields.Char('Document Name')
    email_template_id = fields.Many2one(comodel_name="mail.template", string="Email Template",
                                        help="This field contains the Email Template that will be used by default when sending this Email.",
                                        )

    # def update_digital_sign(self):
    #     for rec in self:
    #         module_installed = self.env['ir.module.module'].search(
    #             [('name', '=', 'web_digital_sign'), ('state', '=', 'installed')], limit=1)
    #         if module_installed and rec.employee_id.user_id.digital_signature:
    #             rec.employee_signature = rec.employee_id.user_id.digital_signature
    #         else:
    #             rec.employee_signature = False

    @api.depends('state')
    def _compute_edit_hide_css(self):
        for rec in self:
            if rec.state in ['sale', 'done']:
                rec.edit_hide_css = '<style>.btn.btn-primary.o_form_button_edit {display: none !important;} .o_form_label.o_readonly_modifier{display: none !important;} </style>'
            else:
                rec.edit_hide_css = False

    def print_on_page(self):
        # self.update_digital_sign()
        for record in self:
            temp = record.contract_template.letter_content
            letter_content_replace = record.contract_template.letter_content

            if "$(amount_tax)" in letter_content_replace:
                if not record.amount_tax:
                    raise ValidationError("Amount Tax is empty")
                letter_content_replace = str(letter_content_replace).replace("$(amount_tax)", str(record.amount_tax))
            if "$(amount_total)" in letter_content_replace:
                if not record.amount_total:
                    raise ValidationError("Amount Total is empty")
                letter_content_replace = str(letter_content_replace).replace("$(amount_total)",
                                                                             str(record.amount_total))
            if "$(amount_untaxed)" in letter_content_replace:
                if not record.amount_untaxed:
                    raise ValidationError("Amount Untaxed is empty")
                letter_content_replace = str(letter_content_replace).replace("$(amount_untaxed)",
                                                                             str(record.amount_untaxed))
            if "$(analytic_account_id)" in letter_content_replace:
                if not record.analytic_account_id:
                    raise ValidationError("Analytic Account is empty")
                letter_content_replace = str(letter_content_replace).replace("$(analytic_account_id)",
                                                                             record.analytic_account_id.name)
            if "$(analytic_idz)" in letter_content_replace:
                if not record.analytic_idz:
                    raise ValidationError("Analytic Group is empty")
                letter_content_replace = str(letter_content_replace).replace("$(analytic_idz)",
                                                                             record.analytic_idz.name)
            if "$(branch_id)" in letter_content_replace:
                if not record.branch_id:
                    raise ValidationError("Branch is empty")
                letter_content_replace = str(letter_content_replace).replace("$(branch_id)", record.branch_id.name)
            if "$(campaign_id)" in letter_content_replace:
                if not record.campaign_id:
                    raise ValidationError("Campaign is empty")
                letter_content_replace = str(letter_content_replace).replace("$(campaign_id)", record.campaign_id.name)
            if "$(city)" in letter_content_replace:
                if not record.city:
                    raise ValidationError("City is empty")
                letter_content_replace = str(letter_content_replace).replace("$(city)", record.city)
            if "$(client_order_ref)" in letter_content_replace:
                if not record.client_order_ref:
                    raise ValidationError("Customer Reference is empty")
                letter_content_replace = str(letter_content_replace).replace("$(client_order_ref)",
                                                                             record.client_order_ref)
            if "$(company_currency_id)" in letter_content_replace:
                if not record.company_currency_id:
                    raise ValidationError("Currency is empty")
                letter_content_replace = str(letter_content_replace).replace("$(company_currency_id)",
                                                                             record.company_currency_id.name)
            if "$(company_id)" in letter_content_replace:
                if not record.company_id:
                    raise ValidationError("Company is empty")
                letter_content_replace = str(letter_content_replace).replace("$(company_id)",
                                                                             str(record.company_id.name))
            if "$(contract_amount)" in letter_content_replace:
                if not record.contract_amount:
                    raise ValidationError("Contract Amount is empty")
                letter_content_replace = str(letter_content_replace).replace("$(contract_amount)",
                                                                             str(record.contract_amount))
            if "$(contract_amount1)" in letter_content_replace:
                if not record.contract_amount1:
                    raise ValidationError("Contract Amount is empty")
                letter_content_replace = str(letter_content_replace).replace("$(contract_amount1)",
                                                                             str(record.contract_amount1))
            if "$(contract_category)" in letter_content_replace:
                if not record.contract_category:
                    raise ValidationError("Contract Category is empty")
                letter_content_replace = str(letter_content_replace).replace("$(contract_category)",
                                                                             record.report_contract_category)
            if "$(contract_parent)" in letter_content_replace:
                if not record.contract_parent:
                    raise ValidationError("Contract Parent is empty")
                letter_content_replace = str(letter_content_replace).replace("$(contract_parent)",
                                                                             record.contract_parent.name)
            if "$(contract_template)" in letter_content_replace:
                if not record.contract_template:
                    raise ValidationError("Contract Template is empty")
                letter_content_replace = str(letter_content_replace).replace("$(contract_template)",
                                                                             record.contract_template.name)
            if "$(cost_sheet_ref)" in letter_content_replace:
                if not record.cost_sheet_ref:
                    raise ValidationError("Cost Sheet is empty")
                letter_content_replace = str(letter_content_replace).replace("$(cost_sheet_ref)",
                                                                             record.cost_sheet_ref.number)
            if "$(count_contract)" in letter_content_replace:
                contract = self.env['sale.order.const'].search_count(
                    [('contract_parent', '=', record.id), ('project_id', '=', record.project_id.id),
                     ('state', 'in', ('sale', 'done'))])
                letter_content_replace = str(letter_content_replace).replace("$(count_contract)", str(contract))
            if "$(country_id)" in letter_content_replace:
                if not record.country_id:
                    raise ValidationError("Country is empty")
                letter_content_replace = str(letter_content_replace).replace("$(country_id)", record.country_id.name)
            if "$(create_date)" in letter_content_replace:
                if not record.create_date:
                    raise ValidationError("Create Date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(create_date)",
                                                                             record.create_date.strftime("%m/%d/%Y"))
            if "$(currency_id)" in letter_content_replace:
                if not record.currency_id:
                    raise ValidationError("Sale Order Currency is empty")
                letter_content_replace = str(letter_content_replace).replace("$(currency_id)",
                                                                             record.currency_id.symbol)
            if "$(date_order)" in letter_content_replace:
                if not record.date_order:
                    raise ValidationError("Order Date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(date_order)",
                                                                             record.date_order.strftime("%m/%d/%Y"))

            if record.discount_type == 'global':
                if "$(discount_amount_global)" in letter_content_replace:
                    letter_content_replace = str(letter_content_replace).replace("$(discount_amount_global)",
                                                                                 str(record.discount_amount_global))
                if "$(discount_method_global)" in letter_content_replace:
                    letter_content_replace = str(letter_content_replace).replace("$(discount_method_global)",
                                                                                 record.discount_method_global)
            if "$(discount_scope)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(discount_scope)",
                                                                             str(record.discount_scope))
            if "$(discount_section)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(discount_section)",
                                                                             str(record.discount_section))
            if "$(discount_sub)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(discount_sub)",
                                                                             str(record.discount_sub))
            if "$(discount_type)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(discount_type)",
                                                                             str(record.discount_type))
            if "$(discount_variable)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(discount_variable)",
                                                                             str(record.discount_variable))
            # if "$(document_attachment)" in letter_content_replace:
            #     if not record.document_attachment:
            #         raise ValidationError("Document Attachment is empty")
            #     letter_content_replace = str(letter_content_replace).replace("$(document_attachment)", record.document_attachment)
            # if "$(document_attachment_fname)" in letter_content_replace:
            #     if not record.document_attachment_fname:
            #         raise ValidationError("Document Name is empty")
            #     letter_content_replace = str(letter_content_replace).replace("$(document_attachment_fname)", record.document_attachment_fname)
            if "$(down_payment)" in letter_content_replace:
                if not record.down_payment:
                    raise ValidationError("Down Payment is empty")
                letter_content_replace = str(letter_content_replace).replace("$(down_payment)",
                                                                             str(record.down_payment))
            if "$(dp_amount)" in letter_content_replace:
                if not record.dp_amount:
                    raise ValidationError("Down Payment Amount is empty")
                letter_content_replace = str(letter_content_replace).replace("$(dp_amount)", str(record.dp_amount))
            if "$(dp_method)" in letter_content_replace:
                if not record.dp_method:
                    raise ValidationError("Down Payment Method is empty")
                letter_content_replace = str(letter_content_replace).replace("$(dp_method)", record.dp_method)
            if "$(end_date)" in letter_content_replace:
                if not record.end_date:
                    raise ValidationError("Planned End Date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(end_date)",
                                                                             record.end_date.strftime("%m/%d/%Y"))
            if "$(fiscal_position_id)" in letter_content_replace:
                if not record.fiscal_position_id:
                    raise ValidationError("Fiscal Position is empty")
                letter_content_replace = str(letter_content_replace).replace("$(fiscal_position_id)",
                                                                             record.fiscal_position_id.name)
            if "$(job_reference)" in letter_content_replace:
                if not record.job_references:
                    raise ValidationError("BOQ References is empty")
                letter_content_replace = str(letter_content_replace).replace("$(job_reference)",
                                                                             record.job_reference.name)
            if "$(line_adjustment)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(line_adjustment)",
                                                                             str(record.line_adjustment))
            if "$(line_discount)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(line_discount)",
                                                                             str(record.line_discount))
            if "$(main_contract_ref)" in letter_content_replace:
                if not record.main_contract_ref:
                    raise ValidationError("main_contract_ref is empty")
                letter_content_replace = str(letter_content_replace).replace("$(main_contract_ref)",
                                                                             record.main_contract_ref.name)
            if "$(medium_id)" in letter_content_replace:
                if not record.medium_id:
                    raise ValidationError("medium_id is empty")
                letter_content_replace = str(letter_content_replace).replace("$(medium_id)", record.medium_id.name)
            if "$(name)" in letter_content_replace:
                if not record.name:
                    raise ValidationError("name is empty")
                letter_content_replace = str(letter_content_replace).replace("$(name)", record.name)
            if "$(opportunity_id)" in letter_content_replace:
                if not record.opportunity_id:
                    raise ValidationError("opportunity_id is empty")
                letter_content_replace = str(letter_content_replace).replace("$(opportunity_id)",
                                                                             record.opportunity_id.name)
            if "$(origin)" in letter_content_replace:
                if not record.origin:
                    raise ValidationError("origin is empty")
                letter_content_replace = str(letter_content_replace).replace("$(origin)", record.origin)
            if "$(note)" in letter_content_replace:
                if not record.note:
                    raise ValidationError("note is empty")
                letter_content_replace = str(letter_content_replace).replace("$(note)", record.note)
            # if "$(partner_credit_conform)" in letter_content_replace:
            #     if not record.partner_credit_conform:
            #         raise ValidationError("partner_credit_conform is empty")
            #     letter_content_replace = str(letter_content_replace).replace("$(partner_credit_conform)", record.partner_credit_conform)
            if "$(partner_invoice_id)" in letter_content_replace:
                if not record.partner_invoice_id:
                    raise ValidationError("Invoice Address is empty")
                letter_content_replace = str(letter_content_replace).replace("$(partner_invoice_id)",
                                                                             str(record.partner_invoice_id.name))
            if "$(payment_seq)" in letter_content_replace:
                if not record.payment_seq:
                    raise ValidationError("Payment Seq is empty")
                letter_content_replace = str(letter_content_replace).replace("$(payment_seq)", str(record.payment_seq))
            if "$(payment_term_id)" in letter_content_replace:
                if not record.payment_term_id:
                    raise ValidationError("Payment Terms is empty")
                letter_content_replace = str(letter_content_replace).replace("$(payment_term_id)",
                                                                             str(record.payment_term_id.name))
            if "$(pricelist_id)" in letter_content_replace:
                if not record.pricelist_id:
                    raise ValidationError("Price List is empty")
                letter_content_replace = str(letter_content_replace).replace("$(pricelist_id)",
                                                                             str(record.pricelist_id.name))
            if "$(project_id)" in letter_content_replace:
                if not record.project_id:
                    raise ValidationError("Project is empty")
                letter_content_replace = str(letter_content_replace).replace("$(project_id)",
                                                                             str(record.project_id.name))
            # if "$(project_scope_ids)" in letter_content_replace:
            #     if not record.project_scope_ids:
            #         raise ValidationError("Project Scopes is empty")
            #     letter_content_replace = str(letter_content_replace).replace("$(project_scope_ids)", str(record.project_scope_ids.name))
            # if "$(relate_contract_ids)" in letter_content_replace:
            #     if not record.relate_contract_ids:
            #         raise ValidationError("Related Contract is empty")
            #     letter_content_replace = str(letter_content_replace).replace("$(relate_contract_ids)", str(record.relate_contract_ids))
            if "$(retention1)" in letter_content_replace:
                if not record.retention1:
                    raise ValidationError("Retention1(%) is empty")
                letter_content_replace = str(letter_content_replace).replace("$(retention1)", str(record.retention1))
            if "$(retention2)" in letter_content_replace:
                if not record.retention2:
                    raise ValidationError("Retention2(%) is empty")
                letter_content_replace = str(letter_content_replace).replace("$(retention2)", str(record.retention2))
            if "$(retention1_amount)" in letter_content_replace:
                if not record.retention1_amount:
                    raise ValidationError("Retention1_amount is empty")
                letter_content_replace = str(letter_content_replace).replace("$(retention1_amount)",
                                                                             str(record.retention1_amount))
            if "$(retention2_amount)" in letter_content_replace:
                if not record.retention2_amount:
                    raise ValidationError("Retention2_amount is empty")
                letter_content_replace = str(letter_content_replace).replace("$(retention2_amount)",
                                                                             str(record.retention2_amount))
            if "$(retention1_date)" in letter_content_replace:
                if not record.retention1_date:
                    raise ValidationError("Retention1 Date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(retention1_date)",
                                                                             record.retention1_date.strftime(
                                                                                 "%m/%d/%Y"))
            if "$(retention2_date)" in letter_content_replace:
                if not record.retention2_date:
                    raise ValidationError("Retention2 Date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(retention2_date)",
                                                                             record.retention2_date.strftime(
                                                                                 "%m/%d/%Y"))
            if "$(said)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(said)", record.said)
            if "$(state)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(state)", record.state)
            if "$(start_date)" in letter_content_replace:
                if not record.start_date:
                    raise ValidationError("Planned Start Date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(start_date)",
                                                                             record.start_date.strftime("%m/%d/%Y"))
            # Signature, signed_by, signed_on not implemented yet
            if "$(street)" in letter_content_replace:
                if not record.street:
                    raise ValidationError("Street is empty")
                letter_content_replace = str(letter_content_replace).replace("$(street)", record.street)
            if "$(street_2)" in letter_content_replace:
                if not record.street_2:
                    raise ValidationError("Street 2 is empty")
                letter_content_replace = str(letter_content_replace).replace("$(street_2)", record.street_2)
            if "$(tax_id)" in letter_content_replace:
                if not record.tax_id:
                    raise ValidationError("Tax ID is empty")
                temp_tax = list()
                for tax in record.tax_id:
                    temp_str = tax.name + " " + str(tax.amount) + "%"
                    temp_tax.append(temp_str)

                tax_value = ", ".join(temp_tax)

                letter_content_replace = str(letter_content_replace).replace("$(tax_id)", tax_value)
            if "$(team_id)" in letter_content_replace:
                if not record.team_id:
                    raise ValidationError("Sales Team is empty")
                letter_content_replace = str(letter_content_replace).replace("$(team_id)", str(record.team_id.name))
            if "$(terms_conditions_id)" in letter_content_replace:
                if not record.terms_conditions_id:
                    raise ValidationError("Term and Conditions is empty")
                letter_content_replace = str(letter_content_replace).replace("$(terms_conditions_id)",
                                                                             str(record.terms_conditions_id.name))
            if "$(user_id)" in letter_content_replace:
                if not record.user_id:
                    raise ValidationError("Salesperson is empty")
                letter_content_replace = str(letter_content_replace).replace("$(user_id)", str(record.user_id.name))
            if "$(validity_date)" in letter_content_replace:
                if not record.validity_date:
                    raise ValidationError("Expiration Date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(validity_date)",
                                                                             record.validity_date.strftime("%m/%d/%Y"))
            if "$(vo_payment_type)" in letter_content_replace:
                if not record.vo_payment_type:
                    raise ValidationError("Payment Method is empty")
                letter_content_replace = str(letter_content_replace).replace("$(vo_payment_type)",
                                                                             record.vo_payment_type)
            if "$(warehouse_address)" in letter_content_replace:
                if not record.warehouse_address:
                    raise ValidationError("Warehouse Address is empty")
                letter_content_replace = str(letter_content_replace).replace("$(warehouse_address)",
                                                                             record.warehouse_address.name)
            if "$(year)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(year)",
                                                                             record.start_date.strftime("%Y"))
            if "$(zip_code)" in letter_content_replace:
                if not record.zip_code:
                    raise ValidationError("Zip Code is empty")
                letter_content_replace = str(letter_content_replace).replace("$(zip_code)", record.zip_code)
            if "$(partner_id)" in letter_content_replace:
                if not record.partner_id:
                    raise ValidationError("Customer is empty")
                letter_content_replace = str(letter_content_replace).replace("$(partner_id)", record.partner_id.name)

            record.contract_template.letter_content = letter_content_replace
            data = record.contract_template.letter_content
            record.contract_template.letter_content = temp

            return data

    # def search_manpower_planning(self):
    #     mpp_on = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp')
    #     if mpp_on:
    #         if self.first_contract_date:
    #             first_contract_date = datetime.strptime(str(self.first_contract_date), "%Y-%m-%d")
    #             mpp_line = self.env['manpower.planning.line'].search(
    #                 [('job_position_id', '=', self.job_id.id), ('work_location_id', '=', self.work_location_id.id)])
    #             if mpp_line:
    #                 for record in mpp_line:
    #                     if record.manpower_id:
    #                         if first_contract_date.date() >= record.manpower_id.mpp_period.start_period and first_contract_date.date() <= record.manpower_id.mpp_period.end_period:
    #                             record.total_fullfillment = record.total_fullfillment + 1

    # def ir_cron_send_notification(self):
    #     global_setting = self.env['expiry.contract.notification'].search([])

    #     now = datetime.now()
    #     draft_contract = self.search([('state', '=', 'draft'), ('date_start', '<=', now.date())])
    #     if draft_contract:
    #         for data in draft_contract:
    #             data.state = 'open'
    #             ## start add by hadorik
    #             employee = self.env['hr.employee'].browse(data.employee_id.id)
    #             employee.department_id = data.department_id.id
    #             employee.job_id = data.job_id.id
    #             data.search_manpower_planning()
    #             ## end of add
    #     running_contract = self.search([('state', '=', 'open'), ('date_end', '<=', now.date())])
    #     if running_contract:
    #         for data_running in running_contract:
    #             data_running.state = 'close'
    #             setting = self.env['expiry.contract.notification'].search([])
    #             setting.send_notification("contract_expire", data_running.id)
    #     total_days = global_setting.days
    #     to_renew_contract = self.search([('date_end', '=', now.date() + timedelta(days=total_days))])
    #     if to_renew_contract:
    #         for data_renew in to_renew_contract:
    #             global_setting.send_notification("contract_renew", data_renew.id)

    # def write(self, vals):
    #     res = super(HrContractInherit, self).write(vals)
    #     if vals.get('state'):
    #         if vals.get('state') == 'open':
    #             self.search_manpower_planning()
    #         self.employee_id.department_id = self.department_id.id
    #         self.employee_id.job_id = self.job_id.id
    #     return res

    # @api.onchange('employee_id')
    # def _onchange_employee_id(self):
    #     if self.employee_id:
    #         self.work_location_id = self.employee_id.location_id
    #     else:
    #         self.work_location_id = False

    # def get_certificate_template(self):
    #     self.update_digital_sign()
    #     for rec in self:
    #         parent_record = rec
    #         if parent_record.contract_template:
    #             temp = parent_record.contract_template.letter_content
    # letter_content_replace = parent_record.contract_template.letter_content
    #             if "$(name)" in letter_content_replace:
    #                 if not parent_record.name:
    #                     raise ValidationError("Certificate Name is empty")
    #                 letter_content_replace = str(letter_content_replace).replace("$(name)",
    #                                                                              parent_record.name)
    #             if "$(employee_id)" in letter_content_replace:
    #                 if not rec.employee_id.name:
    #                     raise ValidationError("Employee Name is empty")
    #                 letter_content_replace = str(letter_content_replace).replace("$(employee_id)",
    #                                                                              rec.employee_id.name)
    #             if "$(employee_signature)" in letter_content_replace:
    #                 if not rec.employee_id:
    #                     raise ValidationError("Employee Signature is empty")
    #                 if rec.employee_signature:
    #                     attachment = self.env['ir.attachment'].search(
    #                         [('res_model', '=', 'res.users'), ('res_id', '=', rec.employee_id.user_id.id),
    #                          ('res_field', '=', 'digital_signature')], limit=1)
    #                     sign_url = '''"/web/image/ir.attachment/''' + str(attachment.id) + '''/datas"'''
    #                     img_tag = '''<img src=''' + str(
    #                         sign_url) + ' ' + '''class="img img-fluid" border="1" width="200" height="150"/>'''

    #                     letter_content_replace = str(letter_content_replace).replace("$(employee_signature)",
    #                                                                                  str(img_tag))
    #                 else:
    #                     letter_content_replace = str(letter_content_replace).replace("$(employee_signature)", str())
    #             if "$(job_id)" in letter_content_replace:
    #                 if not parent_record.job_id.name:
    #                     raise ValidationError("Job is empty")
    #                 letter_content_replace = str(letter_content_replace).replace("$(job_id)",
    #                                                                              rec.job_id.name)
    #             if "$(wage)" in letter_content_replace:
    #                 if not rec.wage:
    #                     raise ValidationError("Wage is empty")
    #                 letter_content_replace = str(letter_content_replace).replace("$(wage)",
    #                                                                              str(rec.wage))
    #             if "$(create_date)" in letter_content_replace:
    #                 if not rec.date_start:
    #                     raise ValidationError("Create Date is empty")
    #                 c_date = rec.create_date
    #                 c_date_format = c_date.strftime('%m/%d/%Y')
    #                 letter_content_replace = str(letter_content_replace).replace("$(create_date)",
    #                                                                              str(c_date_format))

    #             if "$(start_date)" in letter_content_replace:
    #                 if not parent_record.start_date:
    #                     raise ValidationError("Start Date is empty")
    #                 s_date = parent_record.start_date
    #                 s_date_format = s_date.strftime('%m/%d/%Y')
    #                 letter_content_replace = str(letter_content_replace).replace("$(start_date)",
    #                                                                              str(s_date_format))
    #             if "$(end_date)" in letter_content_replace:
    #                 if not parent_record.end_date:
    #                     raise ValidationError("End Date is empty")
    #                 e_date = parent_record.end_date
    #                 e_date_format = e_date.strftime('%m/%d/%Y')
    #                 letter_content_replace = str(letter_content_replace).replace("$(end_date)",
    #                                                                              str(e_date_format))
    #             if "$(resource_calendar_id)" in letter_content_replace:
    #                 if parent_record.resource_calendar_id:
    #                     letter_content_replace = str(letter_content_replace).replace("$(resource_calendar_id)",
    #                                                                                  rec.resource_calendar_id.name)
    #             parent_record.contract_template.letter_content = letter_content_replace
    #             data = parent_record.contract_template.letter_content
    #             parent_record.contract_template.letter_content = temp
    #             return data

    # def update_certificate(self):
    #     for rec in self:
    #         pdf = self.env.ref('equip3_hr_contract_extend.equip3_hr_contract_letter_mail')._render_qweb_pdf(rec.id)
    #         attachment = base64.b64encode(pdf[0])
    #         rec.certificate_attachment = attachment
    #         rec.certificate_attachment_fname = f"{'contract'}_{rec.employee_id.name}"

    # def action_contract_email_send(self):
    #     ir_model_data = self.env['ir.model.data']
    #     self.update_certificate()
    #     for rec in self:
    #         if not rec.contract_template:
    #             raise ValidationError("Sorry, you can't send a contract letter. Because the Contract Template field has not been filled")
    #         try:
    #             template_id = ir_model_data.get_object_reference(
    #                 'equip3_hr_contract_extend',
    #                 'email_template_contract_letter')[1]
    #         except ValueError:
    #             template_id = False
    #         ir_values = {
    #             'name': self.certificate_attachment_fname + '.pdf',
    #             'type': 'binary',
    #             'datas': self.certificate_attachment,
    #             'store_fname': self.certificate_attachment_fname,
    #             'mimetype': 'application/x-pdf',
    #         }
    #         data_id = self.env['ir.attachment'].create(ir_values)
    #         template = self.env['mail.template'].browse(template_id)
    #         template.attachment_ids = [(6, 0, [data_id.id])]
    #         template.send_mail(rec.id, force_send=True)
    #         template.attachment_ids = [(3, data_id.id)]
    #         break

    # def action_contract_email_send(self):
    #     self.ensure_one()
    #     if not self.employee_id.user_id:
    #         raise ValidationError(
    #             "Sorry, you can't send a contract letter because the employee is not mapped to related user")
    #     ir_model_data = self.env['ir.model.data']
    #     self.update_certificate()
    #     if not self.contract_template:
    #         raise ValidationError(
    #             "Sorry, you can't send a contract letter. Because the Contract Template field has not been filled")
    #     try:
    #         template_id = ir_model_data.get_object_reference(
    #             'equip3_hr_contract_extend',
    #             'email_template_contract_letter')[1]
    #     except ValueError:
    #         template_id = False
    #     try:
    #         compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
    #     except ValueError:
    #         compose_form_id = False
    #     ir_values = {
    #         'name': self.certificate_attachment_fname + '.pdf',
    #         'type': 'binary',
    #         'datas': self.certificate_attachment,
    #         'store_fname': self.certificate_attachment_fname,
    #         'mimetype': 'application/x-pdf',
    #     }
    #     data_id = self.env['ir.attachment'].create(ir_values)
    #     lang = self.env.context.get('lang')
    #     template = self.env['mail.template'].browse(template_id)
    #     if template.lang:
    #         lang = template._render_lang(self.ids)[self.id]
    #     ctx = {
    #         'default_model': 'hr.contract',
    #         'active_model': 'hr.contract',
    #         'default_res_id': self.id,
    #         'default_partner_ids': [self.employee_id.user_id.partner_id.id],
    #         'active_id': self.ids[0],
    #         'default_use_template': bool(template_id),
    #         'default_template_id': template_id,
    #         'default_composition_mode': 'comment',
    #         'custom_layout': " ",
    #         'default_attachment_ids': (data_id.id,),
    #         'force_email': True,
    #         'model_description': 'Contract Letter',
    #     }
    #     return {
    #         'name': _('Compose Email'),
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'res_model': 'mail.compose.message',
    #         'views': [(compose_form_id, 'form')],
    #         'view_id': compose_form_id,
    #         'target': 'new',
    #         'context': ctx,
    #     }

    # def certificate_mail(self):
    #     for rec in self:
    #         rec.update_certificate()
    #         ir_model_data = self.env['ir.model.data']
    #         ir_values = {
    #             'name': rec.certificate_attachment_fname + '.pdf',
    #             'type': 'binary',
    #             'datas': rec.certificate_attachment,
    #             'store_fname': rec.certificate_attachment_fname,
    #             'mimetype': 'application/x-pdf',
    #         }
    #         data_id = rec.env['ir.attachment'].create(ir_values)
    #         try:
    #             template_id = rec.email_template_id.id
    #         except ValueError:
    #             template_id = False
    #         ctx = rec._context.copy()
    #         ctx.update({
    #             'email_from': rec.env.user.email,
    #             'email_to': rec.employee_id.user_id.email,
    #         })
    #         template = rec.env['mail.template'].browse(template_id)
    #         template.attachment_ids = [(6, 0, [data_id.id])]
    #         template.with_context(ctx).send_mail(rec.id, force_send=True)
    #         template.attachment_ids = [(3, data_id.id)]

    def get_report_data(self, print_level_option):
        scope_sect_prod_dict = {}
        sale_order_id = self

        scopes = [item.project_scope.name for item in sale_order_id.project_scope_ids]
        for item in sale_order_id.project_scope_ids:
            scope_sect_prod_dict[item.project_scope.name] = {
                'name': item.project_scope.name,
                'total': item.amount_line,
                'children': {},
            }

        sections = [item.section.name for item in sale_order_id.section_ids]
        for item in sale_order_id.section_ids:
            if scope_sect_prod_dict.get(item.project_scope.name, False):
                scope_sect_prod_dict[item.project_scope.name]['children'][item.section.name] = {
                    'name': item.section.name,
                    'total': item.amount_line,
                    'qty': item.quantity,
                    'uom': item.uom_id.name,
                    'children': {},
                }

        if print_level_option == '3_level':
            for item in sale_order_id.material_line_ids:
                if scope_sect_prod_dict.get(item.project_scope.name, False):
                    if scope_sect_prod_dict[item.project_scope.name]['children'].get(item.section_name.name, False):
                        scope_sect_prod_dict[item.project_scope.name]['children'][item.section_name.name]['children'][
                            item.material_id.name] = {
                            'name': item.material_id.name,
                            'qty': item.quantity,
                            'uom': item.uom_id.name,
                            'unit_price': item.amount_line / item.quantity if item.quantity else item.unit_price,
                            'total': item.amount_line,
                            'children': {},
                        }

            for item in sale_order_id.labour_line_ids:
                if scope_sect_prod_dict.get(item.project_scope.name, False):
                    if scope_sect_prod_dict[item.project_scope.name]['children'].get(item.section_name.name, False):
                        scope_sect_prod_dict[item.project_scope.name]['children'][item.section_name.name]['children'][
                            item.labour_id.name] = {
                            'name': item.labour_id.name,
                            'qty': item.quantity,
                            'uom': item.uom_id.name,
                            'unit_price': item.amount_line / item.quantity if item.quantity else item.unit_price,
                            'total': item.amount_line,
                            'children': {},
                        }

            for item in sale_order_id.overhead_line_ids:
                if scope_sect_prod_dict.get(item.project_scope.name, False):
                    if scope_sect_prod_dict[item.project_scope.name]['children'].get(item.section_name.name, False):
                        scope_sect_prod_dict[item.project_scope.name]['children'][item.section_name.name]['children'][
                            item.overhead_id.name] = {
                            'name': item.overhead_id.name,
                            'qty': item.quantity,
                            'uom': item.uom_id.name,
                            'unit_price': item.amount_line / item.quantity if item.quantity else item.unit_price,
                            'total': item.amount_line,
                            'children': {},
                        }

            for item in sale_order_id.subcon_line_ids:
                if scope_sect_prod_dict.get(item.project_scope.name, False):
                    if scope_sect_prod_dict[item.project_scope.name]['children'].get(item.section_name.name, False):
                        scope_sect_prod_dict[item.project_scope.name]['children'][item.section_name.name]['children'][
                            item.subcon_id.name] = {
                            'name': item.subcon_id.name,
                            'qty': item.quantity,
                            'uom': item.uom_id.name,
                            'unit_price': item.amount_line / item.quantity if item.quantity else item.unit_price,
                            'total': item.amount_line,
                            'children': {},
                        }

            for item in sale_order_id.equipment_line_ids:
                if scope_sect_prod_dict.get(item.project_scope.name, False):
                    if scope_sect_prod_dict[item.project_scope.name]['children'].get(item.section_name.name, False):
                        scope_sect_prod_dict[item.project_scope.name]['children'][item.section_name.name]['children'][
                            item.equipment_id.name] = {
                            'name': item.equipment_id.name,
                            'qty': item.quantity,
                            'uom': item.uom_id.name,
                            'unit_price': item.amount_line / item.quantity if item.quantity else item.unit_price,
                            'total': item.amount_line,
                            'children': {},
                        }

            for item in sale_order_id.internal_asset_line_ids:
                if scope_sect_prod_dict.get(item.project_scope.name, False):
                    if scope_sect_prod_dict[item.project_scope.name]['children'].get(item.section_name.name, False):
                        scope_sect_prod_dict[item.project_scope.name]['children'][item.section_name.name]['children'][
                            item.asset_id.name] = {
                            'name': item.asset_id.name,
                            'qty': item.quantity,
                            'uom': item.uom_id.name,
                            'unit_price': item.amount_line / item.quantity if item.quantity else item.unit_price,
                            'total': item.amount_line,
                            'children': {},
                        }

        return scope_sect_prod_dict

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


class SalesOrderConsApproverUser(models.Model):
    _name = 'sale.order.const.approver.user'
    _description = 'Sales Order Construction Approver User'

    sale_order_const_approver_id = fields.Many2one('sale.order.const', string="Contract")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'sale_order_const_app_emp_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'const_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(related='sale_order_const_approver_id.state', string='Parent Status')

    @api.depends('sale_order_const_approver_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.sale_order_const_approver_id.sale_order_const_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.sale_order_const_approver_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.sale_order_const_approver_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids


class OrderLines(models.Model):
    _name = 'sale.order.line.const'
    _description = 'Sales Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _rec_name = "type"
    _order = 'order_id, sequence, id'
    _check_company_auto = True

    order_id = fields.Many2one('sale.order.const', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line',string='Section')
    variable_ref = fields.Many2one('variable.template',string='Variable')
    type = fields.Selection([
            ('material', 'Material'),
            ('labour', 'Labour'),
            ('subcon', 'Subcon'),
            ('overhead', 'Overhead'),
            ('equipment', 'Equipment'),
            ('asset', 'Asset'),
            ],string="Estimation Type")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    product_id = fields.Many2one('product.product', string="Product", tracking=True)
    variable = fields.Many2one('variable.template', string='Subcon', 
               domain="[('variable_subcon', '=', True), ('company_id', '=', parent.company_id)]")
    description = fields.Text(string="Description", tracking=True)
    quantity = fields.Float(string="Quantity", tracking=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', readonly=True)
    analytic_idz = fields.Many2many(related="order_id.analytic_idz", string='Analytic Group')
    uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
    line_tax_id = fields.Many2many(related="order_id.tax_id", string="Taxes")
    unit_price = fields.Float(string="Unit Price", tracking=True)
    subtotal = fields.Float(string="Subtotal")
    adjustment_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_line = fields.Float(string="Adjustment Amount", tracking=True)
    adjustment_subtotal_line = fields.Float(string="Adjustment Subtotal")
    adjustment_line = fields.Float(string="Adjustment Line")
    discount_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_line = fields.Float(string="Discount Amount", tracking=True)
    discount_subtotal_line = fields.Float(string="Discount Subtotal")
    discount_line = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    amount_line = fields.Float(string="Amount Before Tax")
    amount_tax_line = fields.Float(string="Amount Tax", compute='_compute_amount_tax_line')
    total_amount = fields.Float(string="Total Amount", compute='_compute_total_amount')

    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")

    def _compute_amount_tax_line(self):
        for line in self:
            line_tax_id_amount = 0
            for tax_line in line.line_tax_id:
                line_tax_id_amount += tax_line.amount
            line.amount_tax_line = line.amount_line * (line_tax_id_amount / 100)
            return line_tax_id_amount

    def _compute_total_amount(self):
        total = 0.0
        for line in self:
            total = line.amount_line + line.amount_tax_line
            line.total_amount = total
        return total

    @api.depends('order_id.order_line_ids', 'order_id.order_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.order_line_ids:
                no += 1
                l.sr_no = no

    # @api.onchange('quantity')
    # def set_account_group(self):
    #     for res in self:
    #         res.analytic_idz = res.order_id.analytic_idz
    #         res.line_tax_id = res.order_id.tax_id


class SaleOrderMaterialLine(models.Model):
    _name = 'sale.order.material.line'
    _description = 'Material Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _rec_name = "type"
    _order = 'order_id, sequence, id'
    _check_company_auto = True

    @api.depends('order_id.material_line_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.material_line_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line',string='Section')
    variable_ref = fields.Many2one('variable.template',string='Variable')
    type = fields.Selection([
            ('material', 'Material'),
            ('labour', 'Labour'),
            ('subcon', 'Subcon'),
            ('overhead', 'Overhead'),
            ('equipment', 'Equipment'),
            ('asset', 'Asset'),
            ],string="Estimation Type")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    material_id = fields.Many2one('product.product', string="Material", tracking=True)
    variable = fields.Many2one('variable.template', string='Subcon', 
               domain="[('variable_subcon', '=', True), ('company_id', '=', parent.company_id)]")
    description = fields.Text(string="Description", tracking=True)
    quantity = fields.Float(string="Quantity", tracking=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', readonly=True)
    analytic_idz = fields.Many2many(related="order_id.analytic_idz", string='Analytic Group')
    uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
    line_tax_id = fields.Many2many(related="order_id.tax_id", string="Taxes")
    unit_price = fields.Float(string="Unit Price", tracking=True)
    subtotal = fields.Float(string="Subtotal", compute='_compute_subtotal')
    adjustment_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_line = fields.Float(string="Adjustment Amount", tracking=True)
    adjustment_subtotal_line = fields.Float(string="Adjustment Subtotal")
    adjustment_line = fields.Float(string="Adjustment Line")
    discount_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_line = fields.Float(string="Discount Amount", tracking=True)
    discount_subtotal_line = fields.Float(string="Discount Subtotal")
    discount_line = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    amount_line = fields.Float(string="Amount Before Tax")
    amount_tax_line = fields.Float(string="Amount Tax")
    total_amount = fields.Float(string="Total Amount")

    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    current_quantity = fields.Float(string='Available Budget Quantity', default=0.0)
    budget_quantity = fields.Float(string='Budget Quantity', default=0.0)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(SaleOrderMaterialLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res    
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
        
        return super(SaleOrderMaterialLine, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            
        return super(SaleOrderMaterialLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _get_display_price(self, product):
        if self.order_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.order_id.pricelist_id.id, uom=self.uom_id.id).price
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.uom_id.id)

        final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(product or self.material_id, self.quantity or 1.0, self.order_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.uom_id, self.order_id.pricelist_id.id)
        if currency != self.order_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.order_id.pricelist_id.currency_id,
                self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)
    
    
    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price, suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.order_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.order_id.date_order or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id
    
    @api.onchange('material_id', 'unit_price', 'uom_id', 'quantity', 'line_tax_id')
    def _onchange_discount(self):
        if not (self.material_id and self.uom_id and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.material_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.quantity,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.uom_id.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.uom_id.id)

        price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.material_id, self.quantity or 1.0, self.order_id.partner_id)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.uom_id, self.order_id.pricelist_id.id)

        if new_list_price != 0:
            if self.order_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.order_id.pricelist_id.currency_id,
                    self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                self.discount = discount

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        price = 0.0
        for rec in self:
            if rec.order_id.contract_category == 'main':
                price = (rec.quantity * rec.unit_price)
            elif rec.order_id.contract_category == 'var':
                price = (rec.budget_quantity + rec.quantity) * rec.unit_price
            rec.subtotal = price

    # @api.onchange('quantity')
    # def set_account_group(self):
    #     for res in self:
    #         res.analytic_idz = res.order_id.analytic_idz
    #         res.line_tax_id = res.order_id.tax_id

    # def _compute_amount_tax_line(self):
    #     for line in self:
    #         line_tax_id_amount = 0
    #         for tax_line in line.line_tax_id:
    #             line_tax_id_amount += tax_line.amount
    #         line.amount_tax_line = line.amount_line * (line_tax_id_amount / 100)
    #         return line_tax_id_amount

    # @api.depends('subtotal', 'adjustment_line', 'discount_line')
    # def _compute_amount_line(self):
    #     for total in self:
    #         total.amount_line = total.subtotal + total.adjustment_line - total.discount_line

    # @api.depends('amount_line', 'amount_tax_line')
    # def _compute_total_amount(self):
    #     for total in self:
    #         total.total_amount = total.amount_line + total.amount_tax_line


class SaleOrderlabourLine(models.Model):
    _name = 'sale.order.labour.line'
    _description = 'Labour Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _rec_name = "type"
    _order = 'order_id, sequence, id'
    _check_company_auto = True

    @api.depends('order_id.labour_line_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.labour_line_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line',string='Section')
    variable_ref = fields.Many2one('variable.template',string='Variable')
    type = fields.Selection([
            ('material', 'Material'),
            ('labour', 'Labour'),
            ('subcon', 'Subcon'),
            ('overhead', 'Overhead'),
            ('equipment', 'Equipment'),
            ('asset', 'Asset'),
            ],string="Estimation Type")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    labour_id = fields.Many2one('product.product', string="Labour", tracking=True)
    description = fields.Text(string="Description", tracking=True)
    contractors = fields.Integer('Contractors')
    time = fields.Float('Time')
    quantity = fields.Float(string="Quantity", tracking=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', readonly=True)
    analytic_idz = fields.Many2many(related="order_id.analytic_idz", string='Analytic Group')
    uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
    line_tax_id = fields.Many2many(related="order_id.tax_id", string="Taxes")
    unit_price = fields.Float(string="Unit Price", tracking=True)
    subtotal = fields.Float(string="Subtotal", compute='_compute_subtotal')
    adjustment_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_line = fields.Float(string="Adjustment Amount", tracking=True)
    adjustment_subtotal_line = fields.Float(string="Adjustment Subtotal")
    adjustment_line = fields.Float(string="Adjustment Line")
    discount_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_line = fields.Float(string="Discount Amount", tracking=True)
    discount_subtotal_line = fields.Float(string="Discount Subtotal")
    discount_line = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    amount_line = fields.Float(string="Amount Before Tax")
    amount_tax_line = fields.Float(string="Amount Tax")
    total_amount = fields.Float(string="Total Amount")

    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    current_time = fields.Float(string='Available Budget Time', default=0.0)
    current_contractors = fields.Integer(string='Available Budget Contractors', default=0)
    budget_time = fields.Float(string='Budget Time', default=0.0)
    budget_contractors = fields.Integer(string='Budget Contractors', default=0)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(SaleOrderlabourLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res    
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
        
        return super(SaleOrderlabourLine, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            
        return super(SaleOrderlabourLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _get_display_price(self, product):
        if self.order_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.order_id.pricelist_id.id, uom=self.uom_id.id).price
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.uom_id.id)

        final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(product or self.labour_id, self.quantity or 1.0, self.order_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.uom_id, self.order_id.pricelist_id.id)
        if currency != self.order_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.order_id.pricelist_id.currency_id,
                self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)
    
    
    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price, suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.order_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.order_id.date_order or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id
    
    @api.onchange('labour_id', 'unit_price', 'uom_id', 'quantity', 'line_tax_id')
    def _onchange_discount(self):
        if not (self.labour_id and self.uom_id and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.labour_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.quantity,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.uom_id.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.uom_id.id)

        price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.labour_id, self.quantity or 1.0, self.order_id.partner_id)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.uom_id, self.order_id.pricelist_id.id)

        if new_list_price != 0:
            if self.order_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.order_id.pricelist_id.currency_id,
                    self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                self.discount = discount

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        price = 0.0
        for rec in self:
            if rec.order_id.contract_category == 'main':
                price = (rec.quantity * rec.unit_price)
            elif rec.order_id.contract_category == 'var':
                price = (rec.budget_contractors + rec.contractors) * (rec.budget_time + rec.time) * rec.unit_price
            rec.subtotal = price

    # @api.onchange('quantity')
    # def set_account_group(self):
    #     for res in self:
    #         res.analytic_idz = res.order_id.analytic_idz
    #         res.line_tax_id = res.order_id.tax_id
    
    # def _compute_amount_tax_line(self):
    #     for line in self:
    #         line_tax_id_amount = 0
    #         for tax_line in line.line_tax_id:
    #             line_tax_id_amount += tax_line.amount
    #         line.amount_tax_line = line.amount_line * (line_tax_id_amount / 100)
    #         return line_tax_id_amount


    # @api.depends('subtotal', 'adjustment_line', 'discount_line')
    # def _compute_amount_line(self):
    #     for total in self:
    #         total.amount_line = total.subtotal + total.adjustment_line - total.discount_line

    # @api.depends('amount_line', 'amount_tax_line')
    # def _compute_total_amount(self):
    #     for total in self:
    #         total.total_amount = total.amount_line + total.amount_tax_line


class SaleOrderoverheadLine(models.Model):
    _name = 'sale.order.overhead.line'
    _description = 'Overhead Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _rec_name = "type"
    _order = 'order_id, sequence, id'
    _check_company_auto = True

    @api.depends('order_id.overhead_line_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.overhead_line_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line',string='Section')
    variable_ref = fields.Many2one('variable.template',string='Variable')
    type = fields.Selection([
            ('material', 'Material'),
            ('labour', 'Labour'),
            ('subcon', 'Subcon'),
            ('overhead', 'Overhead'),
            ('equipment', 'Equipment'),
            ('asset', 'Asset'),
            ],string="Estimation Type")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    overhead_id = fields.Many2one('product.product', string="Overhead", tracking=True)
    description = fields.Text(string="Description", tracking=True)
    quantity = fields.Float(string="Quantity", tracking=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', readonly=True)
    analytic_idz = fields.Many2many(related="order_id.analytic_idz", string='Analytic Group')
    uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
    line_tax_id = fields.Many2many(related="order_id.tax_id", string="Taxes")
    unit_price = fields.Float(string="Unit Price", tracking=True)
    subtotal = fields.Float(string="Subtotal", compute='_compute_subtotal')
    adjustment_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_line = fields.Float(string="Adjustment Amount", tracking=True)
    adjustment_subtotal_line = fields.Float(string="Adjustment Subtotal")
    adjustment_line = fields.Float(string="Adjustment Line")
    discount_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_line = fields.Float(string="Discount Amount", tracking=True)
    discount_subtotal_line = fields.Float(string="Discount Subtotal")
    discount_line = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    amount_line = fields.Float(string="Amount Before Tax")
    amount_tax_line = fields.Float(string="Amount Tax")
    total_amount = fields.Float(string="Total Amount")

    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Category', required=False)
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    current_quantity = fields.Float(string='Available Budget Quantity', default=0.0)
    budget_quantity = fields.Float(string='Budget Quantity', default=0.0)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(SaleOrderoverheadLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res   
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
        
        return super(SaleOrderoverheadLine, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            
        return super(SaleOrderoverheadLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _get_display_price(self, product):
        if self.order_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.order_id.pricelist_id.id, uom=self.uom_id.id).price
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.uom_id.id)

        final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(product or self.overhead_id, self.quantity or 1.0, self.order_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.uom_id, self.order_id.pricelist_id.id)
        if currency != self.order_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.order_id.pricelist_id.currency_id,
                self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)
    
    
    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price, suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.order_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.order_id.date_order or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id
    
    @api.onchange('overhead_id', 'unit_price', 'uom_id', 'quantity', 'line_tax_id')
    def _onchange_discount(self):
        if not (self.overhead_id and self.uom_id and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.overhead_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.quantity,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.uom_id.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.uom_id.id)

        price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.overhead_id, self.quantity or 1.0, self.order_id.partner_id)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.uom_id, self.order_id.pricelist_id.id)

        if new_list_price != 0:
            if self.order_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.order_id.pricelist_id.currency_id,
                    self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                self.discount = discount

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        price = 0.0
        for rec in self:
            if rec.order_id.contract_category == 'main':
                price = (rec.quantity * rec.unit_price)
            elif rec.order_id.contract_category == 'var':
                price = (rec.budget_quantity + rec.quantity) * rec.unit_price
            rec.subtotal = price

    # @api.onchange('quantity')
    # def set_account_group(self):
    #     for res in self:
    #         res.analytic_idz = res.order_id.analytic_idz
    #         res.line_tax_id = res.order_id.tax_id
    
    # def _compute_amount_tax_line(self):
    #     for line in self:
    #         line_tax_id_amount = 0
    #         for tax_line in line.line_tax_id:
    #             line_tax_id_amount += tax_line.amount
    #         line.amount_tax_line = line.amount_line * (line_tax_id_amount / 100)
    #         return line_tax_id_amount

    # @api.depends('quantity', 'unit_price')
    # def _compute_subtotal(self):
    #     for total in self:
    #         total.subtotal = total.quantity * total.unit_price

    # @api.depends('subtotal', 'adjustment_line', 'discount_line')
    # def _compute_amount_line(self):
    #     for total in self:
    #         total.amount_line = total.subtotal + total.adjustment_line - total.discount_line

    # @api.depends('amount_line', 'amount_tax_line')
    # def _compute_total_amount(self):
    #     for total in self:
    #         total.total_amount = total.amount_line + total.amount_tax_line


class SaleOrdersubconLine(models.Model):
    _name = 'sale.order.subcon.line'
    _description = 'Subcon Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _rec_name = "type"
    _order = 'order_id, sequence, id'
    _check_company_auto = True

    @api.depends('order_id.subcon_line_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.subcon_line_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line',string='Section')
    variable_ref = fields.Many2one('variable.template',string='Variable')
    type = fields.Selection([
            ('material', 'Material'),
            ('labour', 'Labour'),
            ('subcon', 'Subcon'),
            ('overhead', 'Overhead'),
            ('equipment', 'Equipment'),
            ('asset', 'Asset'),
            ],string="Estimation Type")
    subcon_id = fields.Many2one('variable.template', string='Job Subcon', 
               domain="[('variable_subcon', '=', True), ('company_id', '=', parent.company_id)]")
    description = fields.Text(string="Description", tracking=True)
    quantity = fields.Float(string="Quantity", tracking=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', readonly=True)
    analytic_idz = fields.Many2many(related="order_id.analytic_idz", string='Analytic Group')
    uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
    line_tax_id = fields.Many2many(related="order_id.tax_id", string="Taxes")
    unit_price = fields.Float(string="Unit Price", tracking=True)
    subtotal = fields.Float(string="Subtotal", compute='_compute_subtotal')
    adjustment_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_line = fields.Float(string="Adjustment Amount", tracking=True)
    adjustment_subtotal_line = fields.Float(string="Adjustment Subtotal")
    adjustment_line = fields.Float(string="Adjustment Line")
    discount_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_line = fields.Float(string="Discount Amount", tracking=True)
    discount_subtotal_line = fields.Float(string="Discount Subtotal")
    discount_line = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    amount_line = fields.Float(string="Amount Before Tax")
    amount_tax_line = fields.Float(string="Amount Tax")
    total_amount = fields.Float(string="Total Amount")

    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    current_quantity = fields.Float(string='Available Budget Quantity', default=0.0)
    budget_quantity = fields.Float(string='Budget Quantity', default=0.0)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(SaleOrdersubconLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
        
        return super(SaleOrdersubconLine, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            
        return super(SaleOrdersubconLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        price = 0.0
        for rec in self:
            if rec.order_id.contract_category == 'main':
                price = (rec.quantity * rec.unit_price)
            elif rec.order_id.contract_category == 'var':
                price = (rec.budget_quantity + rec.quantity) * rec.unit_price
            rec.subtotal = price

    # @api.onchange('quantity')
    # def set_account_group(self):
    #     for res in self:
    #         res.analytic_idz = res.order_id.analytic_idz
    #         res.line_tax_id = res.order_id.tax_id

    # def _compute_amount_tax_line(self):
    #     for line in self:
    #         line_tax_id_amount = 0
    #         for tax_line in line.line_tax_id:
    #             line_tax_id_amount += tax_line.amount
    #         line.amount_tax_line = line.amount_line * (line_tax_id_amount / 100)
    #         return line_tax_id_amount

    # @api.depends('quantity', 'unit_price')
    # def _compute_subtotal(self):
    #     for total in self:
    #         total.subtotal = total.quantity * total.unit_price

    # @api.depends('subtotal', 'adjustment_line', 'discount_line')
    # def _compute_amount_line(self):
    #     for total in self:
    #         total.amount_line = total.subtotal + total.adjustment_line - total.discount_line

    # @api.depends('amount_line', 'amount_tax_line')
    # def _compute_total_amount(self):
    #     for total in self:
    #         total.total_amount = total.amount_line + total.amount_tax_line


class SaleOrderEquipmentLine(models.Model):
    _name = 'sale.order.equipment.line'
    _description = 'Equipment Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _rec_name = "type"
    _order = 'order_id, sequence, id'
    _check_company_auto = True

    @api.depends('order_id.equipment_line_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.equipment_line_ids:
                no += 1
                l.sr_no = no
    
    order_id = fields.Many2one('sale.order.const', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line',string='Section')
    variable_ref = fields.Many2one('variable.template',string='Variable')
    type = fields.Selection([
            ('material', 'Material'),
            ('labour', 'Labour'),
            ('subcon', 'Subcon'),
            ('overhead', 'Overhead'),
            ('equipment', 'Equipment'),
            ('asset', 'Asset'),
            ],string="Estimation Type")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    equipment_id = fields.Many2one('product.product', string="Equipment")
    description = fields.Text(string="Description", tracking=True)
    quantity = fields.Float(string="Quantity", tracking=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', readonly=True)
    analytic_idz = fields.Many2many(related="order_id.analytic_idz", string='Analytic Group')
    uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
    line_tax_id = fields.Many2many(related="order_id.tax_id", string="Taxes")
    unit_price = fields.Float(string="Unit Price", tracking=True)
    subtotal = fields.Float(string="Subtotal", compute='_compute_subtotal')
    adjustment_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_line = fields.Float(string="Adjustment Amount", tracking=True)
    adjustment_subtotal_line = fields.Float(string="Adjustment Subtotal")
    adjustment_line = fields.Float(string="Adjustment Line")
    discount_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_line = fields.Float(string="Discount Amount", tracking=True)
    discount_subtotal_line = fields.Float(string="Discount Subtotal")
    discount_line = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    amount_line = fields.Float(string="Amount Before Tax")
    amount_tax_line = fields.Float(string="Amount Tax")
    total_amount = fields.Float(string="Total Amount")

    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    current_quantity = fields.Float(string='Available Budget Quantity', default=0.0)
    budget_quantity = fields.Float(string='Budget Quantity', default=0.0)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(SaleOrderEquipmentLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
        
        return super(SaleOrderEquipmentLine, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            
        return super(SaleOrderInternalAsset, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _get_display_price(self, product):
        if self.order_id.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.order_id.pricelist_id.id, uom=self.uom_id.id).price
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.uom_id.id)

        final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(product or self.equipment_id, self.quantity or 1.0, self.order_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.uom_id, self.order_id.pricelist_id.id)
        if currency != self.order_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.order_id.pricelist_id.currency_id,
                self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)
    
    
    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price, suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env['product.pricelist.item']
        field_name = 'lst_price'
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(uom=uom.id).get_product_price_rule(product, qty, self.order_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == 'standard_price':
                field_name = 'standard_price'
                product_currency = product.cost_currency_id
            elif pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id:
                field_name = 'price'
                product = product.with_context(pricelist=pricelist_item.base_pricelist_id.id)
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(product_currency, currency_id, self.company_id or self.env.company, self.order_id.date_order or fields.Date.today())

        product_uom = self.env.context.get('uom') or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        return product[field_name] * uom_factor * cur_factor, currency_id
    
    @api.onchange('equipment_id', 'unit_price', 'uom_id', 'quantity', 'line_tax_id')
    def _onchange_discount(self):
        if not (self.equipment_id and self.uom_id and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.equipment_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.quantity,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.uom_id.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.uom_id.id)

        price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.equipment_id, self.quantity or 1.0, self.order_id.partner_id)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.quantity, self.uom_id, self.order_id.pricelist_id.id)

        if new_list_price != 0:
            if self.order_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.order_id.pricelist_id.currency_id,
                    self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                self.discount = discount

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        price = 0.0
        for rec in self:
            if rec.order_id.contract_category == 'main':
                price = (rec.quantity * rec.unit_price)
            elif rec.order_id.contract_category == 'var':
                price = (rec.budget_quantity + rec.quantity) * rec.unit_price
            rec.subtotal = price

    # @api.onchange('discount', 'quantity', 'unit_price')
    # def onchange_subtotal(self):
    #     price = 0.0
    #     for line in self:
    #         price = (line.quantity * line.unit_price) - line.discount
    #         line.subtotal = price

    # @api.onchange('quantity')
    # def set_account_group(self):
    #     for res in self:
    #         res.analytic_idz = res.order_id.analytic_idz
    #         res.line_tax_id = res.order_id.tax_id

    # def _compute_amount_tax_line(self):
    #     for line in self:
    #         line_tax_id_amount = 0
    #         for tax_line in line.line_tax_id:
    #             line_tax_id_amount += tax_line.amount
    #         line.amount_tax_line = line.amount_line * (line_tax_id_amount / 100)
    #         return line_tax_id_amount

    # @api.depends('quantity', 'unit_price')
    # def _compute_subtotal(self):
    #     for total in self:
    #         total.subtotal = total.quantity * total.unit_price

    # @api.depends('subtotal', 'adjustment_line', 'discount_line')
    # def _compute_amount_line(self):
    #     for total in self:
    #         total.amount_line = total.subtotal + total.adjustment_line - total.discount_line

    # @api.depends('amount_line', 'amount_tax_line')
    # def _compute_total_amount(self):
    #     for total in self:
    #         total.total_amount = total.amount_line + total.amount_tax_line


class SaleOrderInternalAsset(models.Model):
    _name = 'sale.internal.asset.line'
    _description = 'Internal Asset Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _rec_name = "type"
    _order = 'order_id, sequence, id'
    _check_company_auto = True
    
    @api.depends('order_id.internal_asset_line_ids')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.internal_asset_line_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False)
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment'),
        ('asset', 'Asset'),
    ], string="Estimation Type")
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category', required=True)
    asset_id = fields.Many2one('maintenance.equipment', string="Asset")
    description = fields.Text(string="Description")
    quantity = fields.Float(string="Quantity", tracking=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', readonly=True)
    analytic_idz = fields.Many2many(related="order_id.analytic_idz", string='Analytic Group')
    uom_id = fields.Many2one('uom.uom', string="Unit Of Measure")
    line_tax_id = fields.Many2many(related="order_id.tax_id", string="Taxes")
    unit_price = fields.Float(string="Unit Price", tracking=True)
    subtotal = fields.Float(string="Subtotal", compute='_compute_subtotal')
    adjustment_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_line = fields.Float(string="Adjustment Amount", tracking=True)
    adjustment_subtotal_line = fields.Float(string="Adjustment Subtotal")
    adjustment_line = fields.Float(string="Adjustment Line")
    discount_method_line = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_line = fields.Float(string="Discount Amount", tracking=True)
    discount_subtotal_line = fields.Float(string="Discount Subtotal")
    discount_line = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    amount_line = fields.Float(string="Amount Before Tax")
    amount_tax_line = fields.Float(string="Amount Tax")
    total_amount = fields.Float(string="Total Amount")

    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    current_quantity = fields.Float(string='Available Budget Quantity', default=0.0)
    budget_quantity = fields.Float(string='Budget Quantity', default=0.0)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(SaleOrderInternalAsset, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
        
        return super(SaleOrderInternalAsset, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('order_id.create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
            domain.append(('order_id.project_id.id','in',self.env.user.project_ids.ids))
            
        return super(SaleOrderInternalAsset, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        price = 0.0
        for rec in self:
            if rec.order_id.contract_category == 'main':
                price = (rec.quantity * rec.unit_price)
            elif rec.order_id.contract_category == 'var':
                price = (rec.budget_quantity + rec.quantity) * rec.unit_price
            rec.subtotal = price

    # @api.onchange('quantity')
    # def set_account_group(self):
    #     for res in self:
    #         res.analytic_idz = res.order_id.analytic_idz
    #         res.line_tax_id = res.order_id.tax_id

    # def _compute_amount_tax_line(self):
    #     for line in self:
    #         line_tax_id_amount = 0
    #         for tax_line in line.line_tax_id:
    #             line_tax_id_amount += tax_line.amount
    #         line.amount_tax_line = line.amount_line * (line_tax_id_amount / 100)
    #         return line_tax_id_amount

    # @api.depends('quantity', 'unit_price')
    # def _compute_subtotal(self):
    #     for total in self:
    #         total.subtotal = total.quantity * total.unit_price

    # @api.depends('subtotal', 'adjustment_line', 'discount_line')
    # def _compute_amount_line(self):
    #     for total in self:
    #         total.amount_line = total.subtotal + total.adjustment_line - total.discount_line

    # @api.depends('amount_line', 'amount_tax_line')
    # def _compute_total_amount(self):
    #     for total in self:
    #         total.total_amount = total.amount_line + total.amount_tax_line


class ScopeAdjustment(models.Model):
    _name = 'scope.adjustment'
    _description = 'Scope Adjustment'
    _order = 'sequence'

    @api.depends('order_id.scope_adjustment_ids', 'order_id.scope_adjustment_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.scope_adjustment_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    adjustment_method_scope = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_scope = fields.Float(string="Adjustment Amount")
    adjustment_subtotal_scope = fields.Float(string="Adjustment Subtotal")
    subtotal_scope = fields.Float(string='Subtotal')


class ScopeDiscount(models.Model):
    _name = 'scope.discount'
    _description = 'Scope Discount'
    _order = 'sequence'

    @api.depends('order_id.scope_discount_ids', 'order_id.scope_discount_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.scope_discount_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    discount_method_scope = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_scope = fields.Float(string="Discount Amount")
    discount_subtotal_scope = fields.Float(string="Discount Subtotal")
    subtotal_scope = fields.Float(string='Subtotal')
    adjustment_amount = fields.Float(string='Adjustment')


class SectionAdjustment(models.Model):
    _name = 'section.adjustment'
    _description = 'Section Adjustment'
    _order = 'sequence'

    @api.depends('order_id.section_adjustment_ids', 'order_id.section_adjustment_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.section_adjustment_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Char(string='Section')
    section = fields.Many2one('section.line', string='Section')
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    adjustment_method_section = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_section = fields.Float(string="Adjustment Amount")
    adjustment_subtotal_section = fields.Float(string="Adjustment Subtotal")
    subtotal_section = fields.Float(string='Subtotal')
            

class SectionDiscount(models.Model):
    _name = 'section.discount'
    _description = 'Section Discount'
    _order = 'sequence'

    @api.depends('order_id.section_discount_ids', 'order_id.section_discount_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.section_discount_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Char(string='Section')
    section = fields.Many2one('section.line', string='Section')
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    discount_method_section = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_section = fields.Float(string="Discount Amount")
    discount_subtotal_section = fields.Float(string="Discount Subtotal")
    subtotal_section = fields.Float(string='Subtotal')
    adjustment_amount = fields.Float(string='Adjustment')


class ProjectScopeIDS(models.Model):
    _name = 'scope.order.line'
    _description = 'Scope Order Line'
    _order = 'sequence,id'

    @api.depends('order_id.project_scope_ids', 'order_id.project_scope_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.project_scope_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', ondelete='cascade')
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    description = fields.Text(string="Description")
    adjustment_method_scope = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_scope = fields.Float(string="Adjustment Amount")
    adjustment_subtotal_scope = fields.Float(string="Adjustment Subtotal")
    scope_adjustment = fields.Float(string="Adjustment Line")
    discount_method_scope = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_scope = fields.Float(string="Discount Amount")
    discount_subtotal_scope = fields.Float(string="Discount Subtotal")
    scope_discount = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    subtotal_scope = fields.Float(string='Subtotal', compute="_amount_total")
    amount_line = fields.Float(string="Amount Line")
    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")

    @api.depends('order_id.material_line_ids', 'order_id.labour_line_ids',
                 'order_id.overhead_line_ids', 'order_id.internal_asset_line_ids',
                 'order_id.equipment_line_ids', 'order_id.subcon_line_ids',
                 'order_id.material_line_ids.subtotal', 'order_id.labour_line_ids.subtotal',
                 'order_id.overhead_line_ids.subtotal', 'order_id.internal_asset_line_ids.subtotal',
                 'order_id.equipment_line_ids.subtotal', 'order_id.subcon_line_ids.subtotal')
    def _amount_total(self):
        for scope in self:
            total_subtotal = 0.0
            material_ids = scope.order_id.material_line_ids.filtered(
                lambda m: m.project_scope.id == scope.project_scope.id)
            for mat in material_ids:
                total_subtotal += mat.subtotal
            labour_ids = scope.order_id.labour_line_ids.filtered(
                lambda l: l.project_scope.id == scope.project_scope.id)
            for lab in labour_ids:
                total_subtotal += lab.subtotal
            overhead_ids = scope.order_id.overhead_line_ids.filtered(
                lambda o: o.project_scope.id == scope.project_scope.id)
            for ove in overhead_ids:
                total_subtotal += ove.subtotal
            subcon_ids = scope.order_id.internal_asset_line_ids.filtered(
                lambda s: s.project_scope.id == scope.project_scope.id)
            for sub in subcon_ids:
                total_subtotal += sub.subtotal
            asset_ids = scope.order_id.equipment_line_ids.filtered(
                lambda e: e.project_scope.id == scope.project_scope.id)
            for ass in asset_ids:
                total_subtotal += ass.subtotal
            equipment_ids = scope.order_id.subcon_line_ids.filtered(
                lambda e: e.project_scope.id == scope.project_scope.id)
            for equ in equipment_ids:
                total_subtotal += equ.subtotal
            
            scope.subtotal_scope = total_subtotal


class SectionIDS(models.Model):
    _name = 'section.order.line'
    _description = 'Section Order Line'
    _order = 'sequence,id'

    @api.depends('order_id.section_ids', 'order_id.section_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.section_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', ondelete='cascade')
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    description = fields.Text(string="Description")
    quantity = fields.Float('Quantity')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float('Unit Price', compute='compute_unit_price')
    adjustment_method_section = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_section = fields.Float(string="Adjustment Amount")
    adjustment_subtotal_section = fields.Float(string="Adjustment Subtotal")
    section_adjustment = fields.Float(string="Adjustment Line")
    discount_method_section = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_section = fields.Float(string="Discount Amount")
    discount_subtotal_section = fields.Float(string="Discount Subtotal")
    section_discount = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    subtotal_section = fields.Float(string="Subtotal", compute="_amount_total_section")
    amount_line = fields.Float(string="Amount Line")
    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")


    @api.depends('order_id.material_line_ids', 'order_id.labour_line_ids',
                 'order_id.overhead_line_ids', 'order_id.internal_asset_line_ids',
                 'order_id.equipment_line_ids', 'order_id.subcon_line_ids',
                 'order_id.material_line_ids.subtotal', 'order_id.labour_line_ids.subtotal',
                 'order_id.overhead_line_ids.subtotal', 'order_id.internal_asset_line_ids.subtotal',
                 'order_id.equipment_line_ids.subtotal', 'order_id.subcon_line_ids.subtotal')
    def _amount_total_section(self):
        for section in self:
            total_subtotal = 0.0
            material_ids = section.order_id.material_line_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section.id)
            for mat in material_ids:
                total_subtotal += mat.subtotal
            labour_ids = section.order_id.labour_line_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section.id)
            for lab in labour_ids:
                total_subtotal += lab.subtotal
            overhead_ids = section.order_id.overhead_line_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section.id)
            for ove in overhead_ids:
                total_subtotal += ove.subtotal
            subcon_ids = section.order_id.internal_asset_line_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section.id)
            for sub in subcon_ids:
                total_subtotal += sub.subtotal
            asset_ids = section.order_id.equipment_line_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section.id)
            for ass in asset_ids:
                total_subtotal += ass.subtotal
            equipment_ids = section.order_id.subcon_line_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section.id)
            for equ in equipment_ids:
                total_subtotal += equ.subtotal

            section.subtotal_section = total_subtotal

    
    @api.depends('quantity', 'subtotal_section', 'section_adjustment', 'section_discount')
    def compute_unit_price(self):
        for line in self:
            line.unit_price = (line.subtotal_section + line.section_adjustment - line.section_discount) / line.quantity


class VariableIDS(models.Model):
    _name = 'variable.order.line'
    _description = 'Variable Order Line'
    _order = 'sequence'

    @api.depends('order_id.variable_ids', 'order_id.variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.variable_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string='Order Reference', ondelete='cascade')
    active = fields.Boolean(related='order_id.active', string='Active')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    quantity = fields.Float('Quantity')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float('Unit Price', compute='compute_unit_price')
    adjustment_method_variable = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Adjustment Method")
    adjustment_amount_variable = fields.Float(string="Adjustment Amount")
    adjustment_subtotal_variable = fields.Float(string="Adjustment Subtotal")
    variable_adjustment = fields.Float(string="Adjustment Line")
    discount_method_variable = fields.Selection([
                        ('fix', 'Fixed'),
                        ('per', 'Percentage')
                        ],string="Discount Method")
    discount_amount_variable = fields.Float(string="Discount Amount")
    discount_subtotal_variable = fields.Float(string="Discount Subtotal")
    variable_discount = fields.Float(string="Discount Line")
    discount_type = fields.Selection(related='order_id.discount_type', string="Discount Applies to")
    adjustment_type = fields.Selection(related='order_id.adjustment_type', string="Adjustment Applies to")
    subtotal_variable = fields.Float(string="Subtotal", compute='_amount_total_variable')
    amount_line = fields.Float(string="Amount Line")
    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
    state_line = fields.Selection(related='order_id.state', string='Order Status')
    project_id = fields.Many2one(related='order_id.project_id', string="Project")
    job_reference = fields.Many2one(related='order_id.job_reference', string="BOQ Reference")
    job_references = fields.Many2many(related='order_id.job_references', string="BOQ Reference")
    order_partner_id = fields.Many2one(related='order_id.partner_id', string='Customer')
    user_id = fields.Many2many(related='order_id.user_id', string='Salesperson')
    sequence_no = fields.Char(related='order_id.name', string="Sequence Number")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")

    @api.depends('order_id.material_line_ids', 'order_id.labour_line_ids',
                 'order_id.overhead_line_ids', 'order_id.internal_asset_line_ids',
                 'order_id.equipment_line_ids', 'order_id.subcon_line_ids',
                 'order_id.material_line_ids.subtotal', 'order_id.labour_line_ids.subtotal',
                 'order_id.overhead_line_ids.subtotal', 'order_id.internal_asset_line_ids.subtotal',
                 'order_id.equipment_line_ids.subtotal', 'order_id.subcon_line_ids.subtotal')
    def _amount_total_variable(self):
        for variable in self:
            total_subtotal = 0.0
            material_ids = variable.order_id.material_line_ids.filtered(
                lambda m: m.project_scope.id == variable.project_scope.id and
                          m.section_name.id == variable.section.id and
                          m.variable_ref.id == variable.variable.id)
            for mat in material_ids:
                total_subtotal += mat.subtotal
            labour_ids = variable.order_id.labour_line_ids.filtered(
                lambda m: m.project_scope.id == variable.project_scope.id and
                          m.section_name.id == variable.section.id and
                          m.variable_ref.id == variable.variable.id)
            for lab in labour_ids:
                total_subtotal += lab.subtotal
            overhead_ids = variable.order_id.overhead_line_ids.filtered(
                lambda m: m.project_scope.id == variable.project_scope.id and
                          m.section_name.id == variable.section.id and
                          m.variable_ref.id == variable.variable.id)
            for ove in overhead_ids:
                total_subtotal += ove.subtotal
            subcon_ids = variable.order_id.internal_asset_line_ids.filtered(
                lambda m: m.project_scope.id == variable.project_scope.id and
                          m.section_name.id == variable.section.id and
                          m.variable_ref.id == variable.variable.id)
            for sub in subcon_ids:
                total_subtotal += sub.subtotal
            equipment_ids = variable.order_id.equipment_line_ids.filtered(
                lambda m: m.project_scope.id == variable.project_scope.id and
                          m.section_name.id == variable.section.id and
                          m.variable_ref.id == variable.variable.id)
            for equ in equipment_ids:
                total_subtotal += equ.subtotal
            asset_ids = variable.order_id.subcon_line_ids.filtered(
                lambda m: m.project_scope.id == variable.project_scope.id and
                          m.section_name.id == variable.section.id and
                          m.variable_ref.id == variable.variable.id)
            for ass in asset_ids:
                total_subtotal += ass.subtotal

            variable.subtotal_variable = total_subtotal

    
    @api.depends('quantity', 'subtotal_variable', 'variable_adjustment', 'variable_discount')
    def compute_unit_price(self):
        for line in self:
            line.unit_price = (line.subtotal_variable + line.variable_adjustment - line.variable_discount) / line.quantity


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        if vals.get('model') and \
            vals.get('model') == 'sale.order.const' and vals.get('tracking_value_ids'):
            
            state_const = self.env['ir.model.fields']._get('sale.order.const', 'state_const').id
            state_1_const = self.env['ir.model.fields']._get('sale.order.const', 'state_1_const').id
            sale_state_const = self.env['ir.model.fields']._get('sale.order.const', 'sale_state_const').id
            approval_matrix_state_const = self.env['ir.model.fields']._get('sale.order.const', 'approval_matrix_state_const').id
            approval_matrix_state_1_const = self.env['ir.model.fields']._get('sale.order.const', 'approval_matrix_state_1_const').id
            vals['tracking_value_ids'] = [rec for rec in vals.get('tracking_value_ids') if 
                                        rec[2].get('field') not in (state_const, state_1_const, 
                                        sale_state_const, approval_matrix_state_const, approval_matrix_state_1_const)]
        return super(MailMessage, self).create(vals)


class ConstYear(models.Model):
    _name = 'const.year'
    _description = 'Construction Year'

    name = fields.Integer('Name')

    