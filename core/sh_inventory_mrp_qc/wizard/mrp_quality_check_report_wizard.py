# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class MrpQualityCheckReport(models.AbstractModel):
    _name = 'report.sh_inventory_mrp_qc.mrp_quality_check_doc'
    _description = "Mrp quality check report abstract model"

    @api.model
    def _get_report_values(self, docids, data=None):
        quality_check_obj = self.env['sh.mrp.quality.check']
        product_obj = self.env['product.product']
        qc_list = []
        if data.get('is_mrp'):
            if data.get('state') == 'both':
                if data.get('product_ids'):
                    for product in product_obj.sudo().search([('id', 'in', data.get('product_ids'))]):
                        domain = [("sh_mrp","!=",False),("product_id", "=", product.id), ('state', 'in', ['pass', 'fail']), (
                            'sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_mrp.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
                else:
                    for product in product_obj.sudo().search([]):
                        domain = [("sh_mrp","!=",False),("product_id", "=", product.id), ('state', 'in', ['pass', 'fail']), (
                            'sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_mrp.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
            elif data.get('state') == 'pass':
                if data.get('product_ids'):
                    for product in product_obj.sudo().search([('id', 'in', data.get('product_ids'))]):
                        domain = [("sh_mrp","!=",False),("product_id", "=", product.id), ('state', 'in', [
                            'pass']), ('sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_mrp.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
                else:
                    for product in product_obj.sudo().search([]):
                        domain = [("sh_mrp","!=",False),("product_id", "=", product.id), ('state', 'in', [
                            'pass']), ('sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_mrp.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
            elif data.get('state') == 'fail':
                if data.get('product_ids'):
                    for product in product_obj.sudo().search([('id', 'in', data.get('product_ids'))]):
                        domain = [("sh_mrp","!=",False),("product_id", "=", product.id), ('state', 'in', [
                            'fail']), ('sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_mrp.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
                else:
                    for product in product_obj.sudo().search([]):
                        domain = [("sh_mrp","!=",False),("product_id", "=", product.id), ('state', 'in', [
                            'fail']), ('sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_mrp.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
    
            picking_qc_list = {}
            product_qc_list = {}
            group_by = ''
            if data.get('group_by') == 'sh_mrp':
                group_by = 'sh_mrp'
    
                # Here ignore empty sh_mrp
                qc_list_new = []
                for i in range(len(qc_list)):
                    if qc_list[i]['sh_mrp'] != False:
                        qc_list_new.append(qc_list[i])
                qc_list = qc_list_new
    
                for data_dic in sorted(qc_list, key=lambda i: i['sh_mrp']):
                    if data_dic['sh_mrp'] not in picking_qc_list:
                        picking_qc_list[data_dic['sh_mrp']] = [data_dic]
                    else:
                        temp_list = picking_qc_list[data_dic['sh_mrp']]
                        temp_list.append(data_dic)
                        picking_qc_list[data_dic['sh_mrp']] = temp_list
    
            if data.get('group_by') == 'product':
                group_by = 'product'
                for prod_dic in sorted(qc_list, key=lambda i: i['product']):
                    if prod_dic['product'] not in product_qc_list:
                        product_qc_list[prod_dic['product']] = [prod_dic]
                    else:
                        temp_list = product_qc_list[prod_dic['product']]
                        temp_list.append(prod_dic)
                        product_qc_list[prod_dic['product']] = temp_list
    
            data = {
                'qc_list': qc_list,
                'date_from': data['date_from'],
                'date_to': data['date_to'],
                'group_by': group_by,
                'picking_qc_list': picking_qc_list,
                'product_qc_list': product_qc_list
            }
    
            return data
        else:
            if data.get('state') == 'both':
                if data.get('product_ids'):
                    for product in product_obj.sudo().search([('id', 'in', data.get('product_ids'))]):
                        domain = [("sh_workorder_id","!=",False),("product_id", "=", product.id), ('state', 'in', ['pass', 'fail']), (
                            'sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_workorder_id.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
                else:
                    for product in product_obj.sudo().search([]):
                        domain = [("sh_workorder_id","!=",False),("product_id", "=", product.id), ('state', 'in', ['pass', 'fail']), (
                            'sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_workorder_id.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
            elif data.get('state') == 'pass':
                if data.get('product_ids'):
                    for product in product_obj.sudo().search([('id', 'in', data.get('product_ids'))]):
                        domain = [("sh_workorder_id","!=",False),("product_id", "=", product.id), ('state', 'in', [
                            'pass']), ('sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_workorder_id.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
                else:
                    for product in product_obj.sudo().search([]):
                        domain = [("sh_workorder_id","!=",False),("product_id", "=", product.id), ('state', 'in', [
                            'pass']), ('sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_workorder_id.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
            elif data.get('state') == 'fail':
                if data.get('product_ids'):
                    for product in product_obj.sudo().search([('id', 'in', data.get('product_ids'))]):
                        domain = [("sh_workorder_id","!=",False),("product_id", "=", product.id), ('state', 'in', [
                            'fail']), ('sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_workorder_id.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
                else:
                    for product in product_obj.sudo().search([]):
                        domain = [("sh_workorder_id","!=",False),("product_id", "=", product.id), ('state', 'in', [
                            'fail']), ('sh_date', '>=', data.get('date_from')), ('sh_date', '<=', data.get('date_to'))]
                        search_quality_checks = quality_check_obj.sudo().search(domain)
                        if search_quality_checks:
                            for quality_check in search_quality_checks:
                                qc_dic = {
                                    'product': quality_check.product_id.name,
                                    'sh_mrp': quality_check.sh_workorder_id.name,
                                    'date': quality_check.sh_date,
                                    'control_point': quality_check.sh_control_point,
                                    'norm': quality_check.sh_norm,
                                    'state': quality_check.state,
                                }
                                qc_list.append(qc_dic)
    
            picking_qc_list = {}
            product_qc_list = {}
            group_by = ''
            if data.get('group_by') == 'sh_mrp':
                group_by = 'sh_mrp'
    
                # Here ignore empty sh_mrp
                qc_list_new = []
                for i in range(len(qc_list)):
                    if qc_list[i]['sh_mrp'] != False:
                        qc_list_new.append(qc_list[i])
                qc_list = qc_list_new
    
                for data_dic in sorted(qc_list, key=lambda i: i['sh_mrp']):
                    if data_dic['sh_mrp'] not in picking_qc_list:
                        picking_qc_list[data_dic['sh_mrp']] = [data_dic]
                    else:
                        temp_list = picking_qc_list[data_dic['sh_mrp']]
                        temp_list.append(data_dic)
                        picking_qc_list[data_dic['sh_mrp']] = temp_list
    
            if data.get('group_by') == 'product':
                group_by = 'product'
                for prod_dic in sorted(qc_list, key=lambda i: i['product']):
                    if prod_dic['product'] not in product_qc_list:
                        product_qc_list[prod_dic['product']] = [prod_dic]
                    else:
                        temp_list = product_qc_list[prod_dic['product']]
                        temp_list.append(prod_dic)
                        product_qc_list[prod_dic['product']] = temp_list
    
            data = {
                'qc_list': qc_list,
                'date_from': data['date_from'],
                'date_to': data['date_to'],
                'group_by': group_by,
                'picking_qc_list': picking_qc_list,
                'product_qc_list': product_qc_list
            }
    
            return data

class MrpQualityCheckReportWizard(models.TransientModel):
    _name = 'mrp.quality.check.report'
    _description = 'MRP Quality Check Report'

    date_from = fields.Date("Start Date", required=True,
                            default=fields.Date.today())
    date_to = fields.Date("End Date", required=True,
                          default=fields.Date.today())
    product_ids = fields.Many2many('product.product', string='Product')
    state = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail'), ('both', 'Both')], default='pass', string="Status")
    group_by = fields.Selection(
        [('sh_mrp', 'Operation'), ('product', 'Product')], string="Group By")
    
    is_mrp = fields.Boolean("Is MRP")

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref('sh_inventory_mrp_qc.report_mrp_quality_check_action').report_action([], data=datas)
