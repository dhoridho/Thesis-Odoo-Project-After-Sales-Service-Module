
from odoo import models, fields, api, _
from datetime import datetime
from lxml import etree


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_commission_calc(self):
        return self.env['ir.config_parameter'].sudo().get_param('equip3_sale_team_commission.commission_calc') or ''

    def _get_commission_pay(self):
        return self.env['ir.config_parameter'].sudo().get_param('equip3_sale_team_commission.commission_pay_on') or ''

    def job_related_users(self, jobid):
        if jobid:
            empids = self.env['hr.employee'].search([('user_id', '!=', False), ('job_id', '=', jobid.id)])
            return [emp.user_id.id for emp in empids]
        return False

    @api.depends('partner_id', 'team_id', 'user_id', 'commission_calc', 'amount_total')
    def _compute_commission_data(self):
        for res in self:
            member_lst = []
            commission_pay_on = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_sale_team_commission.commission_pay_on') or ''
            if res.user_id and commission_pay_on == 'order_confirm':
                emp_id = self.env['hr.employee'].search([('user_id', '=', res.user_id.id)], limit=1)
                if emp_id:
                    if res.commission_calc == 'product':
                        for soline in res.order_line:
                            for lineid in soline.product_id.product_comm_ids:
                                lines = {'user_id': res.user_id.id, 'job_id': emp_id.job_id.id}
                                if lineid.user_ids and res.user_id.id in [user.id for user in lineid.user_ids]:
                                    lines['commission'] = soline.price_subtotal * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission * soline.product_uom_qty
                                    member_lst.append(lines)
                                    break
                                elif lineid.job_id and not lineid.user_ids:
                                    if res.user_id.id in res.job_related_users(lineid.job_id):
                                        lines[
                                            'commission'] = soline.price_subtotal * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission * soline.product_uom_qty
                                        member_lst.append(lines)
                                        break
                    elif res.commission_calc == 'product_categ':
                        for soline in res.order_line:
                            for lineid in soline.product_id.categ_id.prod_categ_comm_ids:
                                lines = {'user_id': res.user_id.id, 'job_id': emp_id.job_id.id}
                                if lineid.user_ids and res.user_id.id in [user.id for user in lineid.user_ids]:
                                    lines[
                                        'commission'] = soline.price_subtotal * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission * soline.product_uom_qty
                                    member_lst.append(lines)
                                    break
                                elif lineid.job_id and not lineid.user_ids:
                                    if res.user_id.id in res.job_related_users(lineid.job_id):
                                        lines[
                                            'commission'] = soline.price_subtotal * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission * soline.product_uom_qty
                                        member_lst.append(lines)
                                        break
                    elif res.commission_calc == 'customer' and res.partner_id:
                        for lineid in res.partner_id.comm_ids:
                            lines = {'user_id': res.user_id.id, 'job_id': emp_id.job_id.id}
                            if lineid.user_ids and res.user_id.id in [user.id for user in lineid.user_ids]:
                                lines[
                                    'commission'] = res.amount_total * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission
                                member_lst.append(lines)
                                break
                            elif lineid.job_id and not lineid.user_ids:
                                if res.user_id.id in res.job_related_users(lineid.job_id):
                                    lines[
                                        'commission'] = res.amount_total * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission
                                    member_lst.append(lines)
                                    break
                    elif res.commission_calc == 'sale_team' and res.team_id:
                        for lineid in res.team_id.sale_team_comm_ids:
                            lines = {'user_id': res.user_id.id, 'job_id': emp_id.job_id.id}
                            if lineid.user_ids and res.user_id.id in [user.id for user in lineid.user_ids]:
                                lines[
                                    'commission'] = res.amount_total * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission
                                member_lst.append(lines)
                                break
                            elif lineid.job_id and not lineid.user_ids:
                                if res.user_id.id in res.job_related_users(lineid.job_id):
                                    lines[
                                        'commission'] = res.amount_total * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission
                                    member_lst.append(lines)
                                    break
            userby = {}
            for member in member_lst:
                if member['user_id'] in userby:
                    userby[member['user_id']]['commission'] += member['commission']
                else:
                    userby.update({member['user_id']: member})
            member_lst = []
            for user in userby:
                member_lst.append((0, 0, userby[user]))
            res.sale_order_comm_ids = member_lst

    sale_order_comm_ids = fields.One2many('sales.order.commission', 'order_id', string="Sale Order Commission")
    commission_calc = fields.Selection([('sale_team', 'Sales Team'), ('customer', 'Customer'),
                                        ('product_categ', 'Product Category'),
                                        ('product', 'Product')], string="Commission Calculation", copy=False)
    commission_pay_on = fields.Selection([('order_confirm', 'Sales Order Confirmation'),
                                          ('invoice_validate', 'Customer Invoice Validation'),
                                          ('invoice_pay', 'Customer Invoice Payment')], string="Commission Pay On",
                                         readonly=True, copy=False)

class SalesOrderCommission(models.Model):
    _name = 'sales.order.commission'
    _description = 'Sale Order Commission'

    user_id = fields.Many2one('res.users', string="User", required=True)
    job_id = fields.Many2one('hr.job', string="Job Position")
    commission = fields.Float(string="Commission")
    order_id = fields.Many2one('sale.order', string="Order")
    invoice_id = fields.Many2one('account.move', string="Invoice")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        param_obj = self.env['ir.config_parameter']
        res.update({'commission_pay_on': param_obj.sudo().get_param('commission_pay_on'),
                    'commission_calc': param_obj.sudo().get_param('commission_calc'),
                    'commission_pay_by': param_obj.sudo().get_param('commission_pay_by'),
                })
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        param_obj = self.env['ir.config_parameter']
        param_obj.sudo().set_param('commission_pay_on', self.commission_pay_on)
        param_obj.sudo().set_param('commission_calc', self.commission_calc)
        param_obj.sudo().set_param('commission_pay_by', self.commission_pay_by)

    commission_pay_on = fields.Selection([('order_confirm', 'Sales Order Confirmation'),
                                          ('invoice_validate', 'Customer Invoice Validation'),
                                          ('invoice_pay', 'Customer Invoice Payment')], string="Commission Pay On")
    commission_calc = fields.Selection([('sale_team', 'Sales Team'), ('customer', 'Customer'),
                                        ('product_categ', 'Product Category'),
                                        ('product', 'Product')], string="Commission Calculation")
    commission_pay_by = fields.Selection([('invoice', 'Invoice'), ('salary', 'Salary')], string="Commission Pay By")
