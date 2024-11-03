# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class QualityAlertReport(models.AbstractModel):
    _name = 'report.sh_inventory_mrp_qc.quality_alert_doc'
    _description = "quality alert report abstract model"

    @api.model
    def _get_report_values(self, docids, data=None):
        quality_alert_obj = self.env['sh.quality.alert']
        product_obj = self.env['product.product']
        quality_alert_dic = {}
        if data.get('user_ids'):
            if data.get('product_ids'):
                for user_id in data.get('user_ids'):
                    alert_list = []
                    domain = [
                        ("create_date", ">=", data['date_from']),
                        ("create_date", "<=", data['date_to']),
                        ("user_id", "=", user_id), ('stage_id', '=', data.get('stage_id')[0]), ('product_id', 'in', data.get('product_ids'))]
                    search_alerts = quality_alert_obj.sudo().search(domain)
                    if search_alerts:
                        for alert in search_alerts:
                            alert_dic = {
                                'name': alert.name,
                                'title': alert.title,
                                'product': alert.product_id.name,
                                'partner_id': alert.partner_id.name,
                                'picking': alert.piking_id.name,
                                'team': alert.team_id.name,
                                'create_date': alert.create_date,
                            }
                            alert_list.append(alert_dic)
                    search_users = self.env['res.users'].search([
                        ('id', '=', user_id)
                    ], limit=1)
                    if search_users:
                        quality_alert_dic.update(
                            {search_users.name: alert_list})
            else:
                for user_id in data.get('user_ids'):
                    alert_list = []
                    domain = [
                        ("create_date", ">=", data['date_from']),
                        ("create_date", "<=", data['date_to']),
                        ("user_id", "=", user_id), ('stage_id', '=', data.get('stage_id')[0]), ('product_id', 'in', product_obj.sudo().search([]).ids)]
                    search_alerts = quality_alert_obj.search(domain)
                    if search_alerts:
                        for alert in search_alerts:
                            alert_dic = {
                                'name': alert.name,
                                'title': alert.title,
                                'product': alert.product_id.name,
                                'partner_id': alert.partner_id.name,
                                'picking': alert.piking_id.name,
                                'team': alert.team_id.name,
                                'create_date': alert.create_date,
                            }
                            alert_list.append(alert_dic)
                    search_users = self.env['res.users'].search([
                        ('id', '=', user_id)
                    ], limit=1)
                    if search_users:
                        quality_alert_dic.update(
                            {search_users.name: alert_list})
        else:
            if data.get('product_ids'):
                for user_id in self.env['res.users'].sudo().search([]):
                    alert_list = []
                    domain = [
                        ("create_date", ">=", data['date_from']),
                        ("create_date", "<=", data['date_to']),
                        ("user_id", "=", user_id.id), ('stage_id', '=', data.get('stage_id')[0]), ('product_id', 'in', data.get('product_ids'))]
                    search_alerts = quality_alert_obj.search(domain)
                    if search_alerts:
                        for alert in search_alerts:
                            alert_dic = {
                                'name': alert.name,
                                'title': alert.title,
                                'product': alert.product_id.name,
                                'partner_id': alert.partner_id.name,
                                'picking': alert.piking_id.name,
                                'team': alert.team_id.name,
                                'create_date': alert.create_date,
                            }
                            alert_list.append(alert_dic)
                    search_users = self.env['res.users'].search([
                        ('id', '=', user_id.id)
                    ], limit=1)
                    if search_users:
                        quality_alert_dic.update(
                            {search_users.name: alert_list})
            else:
                for user_id in self.env['res.users'].sudo().search([]):
                    alert_list = []
                    domain = [
                        ("create_date", ">=", data['date_from']),
                        ("create_date", "<=", data['date_to']),
                        ("user_id", "=", user_id.id), ('stage_id', '=', data.get('stage_id')[0]), ('product_id', 'in', product_obj.sudo().search([]).ids)]
                    search_alerts = quality_alert_obj.search(domain)
                    if search_alerts:
                        for alert in search_alerts:
                            alert_dic = {
                                'name': alert.name,
                                'title': alert.title,
                                'product': alert.product_id.name,
                                'partner_id': alert.partner_id.name,
                                'picking': alert.piking_id.name,
                                'team': alert.team_id.name,
                                'create_date': alert.create_date,
                            }
                            alert_list.append(alert_dic)
                    search_users = self.env['res.users'].search([
                        ('id', '=', user_id.id)
                    ], limit=1)
                    if search_users:
                        quality_alert_dic.update(
                            {search_users.name: alert_list})

        data = {
            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'quality_alert_dic': quality_alert_dic,
        }
        return data


class QualityAlertReportWizard(models.TransientModel):
    _name = 'quality.alert.report'
    _description = 'Quality Alert Report'

    date_from = fields.Date("Start Date", required=True,
                            default=fields.Date.today())
    date_to = fields.Date("End Date", required=True,
                          default=fields.Date.today())
    product_ids = fields.Many2many('product.product', string='Product')
    user_ids = fields.Many2many('res.users', string='Responsible Users')
    stage_id = fields.Many2one('sh.qc.alert.stage', 'Stage', required=True)

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref('sh_inventory_mrp_qc.report_quality_alert_action').report_action([], data=datas)
