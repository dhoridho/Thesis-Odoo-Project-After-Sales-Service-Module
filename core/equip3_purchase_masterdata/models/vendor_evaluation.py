# -*- coding:utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, date


class VendorEvaluation(models.Model):
    _inherit = 'vendor.evaluation'

    point = [
        ('0', 'Not Use'),
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Satisfied'),
        ('4', 'Good'),
        ('5', 'Excellent')
    ]

    @api.onchange('vendor', 'on_time_rate')
    def _compute_star(self):
        for res in self:
            if res.on_time_rate >= 1 and res.on_time_rate <= 20:
                res.on_time_rate_star = '1'
            elif res.on_time_rate >= 21 and res.on_time_rate <= 40:
                res.on_time_rate_star = '2'
            elif res.on_time_rate >= 41 and res.on_time_rate <= 60:
                res.on_time_rate_star = '3'
            elif res.on_time_rate >= 61 and res.on_time_rate <= 80:
                res.on_time_rate_star = '4'
            elif res.on_time_rate >= 81:
                res.on_time_rate_star = '5'
            else:
                res.on_time_rate_star = '0'
            res.calculate()

    @api.onchange('vendor')
    def _compute_star_fulfillment(self):
        for res in self:
            if res.fulfillment <= 20:
                res.fulfillment_star = '1'
            elif res.fulfillment <= 40:
                res.fulfillment_star = '2'
            elif res.fulfillment <= 60:
                res.fulfillment_star = '3'
            elif res.fulfillment <= 80:
                res.fulfillment_star = '4'
            elif res.fulfillment <= 100:
                res.fulfillment_star = '5'
            else:
                res.fulfillment_star = '0'
            res.calculate()


    on_time_rate = fields.Float(related='vendor.on_time_rate', compute_sudo=False)

    on_time_rate_check = fields.Boolean(string="1. Delivery on Schedule", default=1, readonly=True,
                                 states={'draft': [('readonly', False)]})
    on_time_rate_factor = fields.Integer(string="Factor", default=1, readonly=True,
                                  states={'draft': [('readonly', False)]})
    on_time_rate_star = fields.Selection(point, string="Rate", readonly=True,
                             states={'draft': [('readonly', False)]})
    on_time_rate_cmt = fields.Char(string="Comment", readonly=True,
                            states={'draft': [('readonly', False)]})

    fulfillment = fields.Float(string="2. Fulfillment", compute='_get_fulfillment')
    fulfillment_check = fields.Boolean(string="2. Fulfillment", default=1, readonly=True,
                                        states={'draft': [('readonly', False)]})
    fulfillment_factor = fields.Integer(string="Factor", default=1, readonly=True,
                                         states={'draft': [('readonly', False)]})
    fulfillment_star = fields.Selection(point, string="Rate", readonly=True,
                                         states={'draft': [('readonly', False)]})
    fulfillment_cmt = fields.Char(string="Comment", readonly=True,
                                   states={'draft': [('readonly', False)]})
    fulfillment_avg = fields.Float(string='Fulfillment Average')
    on_time_rate_avg = fields.Float(string='On Time Rate Average')
    final_point_avg = fields.Float(string='Final Point Average')
    vendor_evaluation_count = fields.Integer(string='Count')

    evaluation_template_id = fields.Many2one('vendor.evaluation.template', string='Evaluation Template')
    evaluation_eval_ids = fields.One2many('vendor.evaluation.template.eval', 'evaluation_id', string='Evaluation Line', states={'draft': [('readonly', False)]})


    branch_id = fields.Many2one('res.branch', "Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', "Company", default=lambda self:self.env.company.id, readonly=True)

    email = fields.Char('Email', readonly=True, states={'draft': [('readonly', False)]})
    business = fields.Char('Business Title', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Date Entry', default=lambda self: fields.Date.today(), readonly=True,
                       states={'draft': [('readonly', False)]})
    final_cmt = fields.Char(string="Final Comment", states={'cancelled': [('readonly', True)],'draft': [('readonly', False)]})



    branch_id = fields.Many2one('res.branch', "Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    company_id = fields.Many2one('res.company', "Company", default=lambda self:self.env.company.id, readonly=True)
    
    @api.onchange('evaluation_template_id')
    def _onchange_evaluation_template_id(self):
        if self.evaluation_template_id:
            evaluation_eval_ids = []
            for line in self.evaluation_template_id.evaluation_lines:
                vals = {
                    'name': line.name,
                }
                evaluation_eval_ids.append((0, 0, vals))
            self.evaluation_eval_ids = None
            self.evaluation_eval_ids = evaluation_eval_ids
        else:
            self.evaluation_eval_ids = None

    @api.onchange('date')
    def _onchange_date_entry(self):
        # start_day_of_month = self.date.replace(day=1)
        # last_day_of_month = start_day_of_month + relativedelta(months=1, day=1, days=-1)

        last_day_of_prev_month = self.date.replace(day=1) - timedelta(days=1)
        start_day_of_prev_month = self.date.replace(day=1) - timedelta(days=last_day_of_prev_month.day)

        self.period_start = start_day_of_prev_month
        self.period_end = last_day_of_prev_month

    @api.depends('vendor', 'user_id')
    def _get_fulfillment(self):
        for rec in self:
            lines = self.env['purchase.order.line'].search([
                ('partner_id', '=', rec.vendor.id),
                ('date_order', '>', fields.Date.today() - timedelta(365))
            ])
            res = 0
            if lines:
                for line in lines:
                    if line.product_qty > 0:
                        res += line.qty_received / line.product_qty * 100
                rec.fulfillment = res / len(lines)
            else:
                rec.fulfillment = 0
            rec._compute_star_fulfillment()

    @api.model
    def _calculate_vendor_evaluation_rating(self):
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        vendor_evaluation_ids = self.search([('period_start', '>=', start_date), 
                                ('period_end', '<=', end_date), ('state', '=', 'approved')])
        vendors = vendor_evaluation_ids.mapped('vendor')
        for vendor in vendors:
            vendor_evaluations = vendor_evaluation_ids.filtered(lambda r:r.vendor.id == vendor.id)
            if len(vendor_evaluations) > 0:
                total_fullfillment = sum(vendor_evaluations.mapped('fulfillment')) / len(vendor_evaluations)
                total_on_time_rate = sum(vendor_evaluations.mapped('on_time_rate')) / len(vendor_evaluations)
                total_final_point = sum(vendor_evaluations.mapped('final_point')) / len(vendor_evaluations)
                vendor_evaluations.write({
                    'vendor_evaluation_count': len(vendor_evaluations),
                    'fulfillment_avg': total_fullfillment if total_fullfillment > 0 else 0,
                    'on_time_rate_avg': total_on_time_rate if total_on_time_rate > 0 else 0,
                    'final_point_avg': total_final_point if total_final_point > 0 else 0,
                })

    @api.constrains('on_time_rate_factor', 'on_time_rate_star')
    def check11_on_time_factor(self):
        for rec in self:
            if rec.on_time_rate_check and rec.on_time_rate_factor <= 0:
                raise ValidationError('Factor of criteria 11 must be higher than 0!')
            if rec.on_time_rate_check and not rec.on_time_rate_star:
                raise ValidationError('Criteria 11 has not been evaluated yet!')

    @api.constrains('fulfillment_factor', 'fulfillment_star')
    def check_fulfillment_factor(self):
        for rec in self:
            if rec.fulfillment_check and rec.fulfillment_factor <= 0:
                raise ValidationError('Factor of criteria 11 must be higher than 0!')
            if rec.fulfillment_check and not rec.fulfillment_star:
                raise ValidationError('Criteria 11 has not been evaluated yet!')

    def calculate(self):
        res = super(VendorEvaluation, self).calculate()
        for rec in self:
            count = 0
            sum_total = 0
            for eval_line in self.evaluation_eval_ids:
                count += eval_line.eval_factor
                sum_total += (int(eval_line.eval_rate) * eval_line.eval_factor)

                # if rec.price_check:
                #     count += rec.price_factor
                #     sum_total += (int(rec.price) * rec.price_factor)
                # if rec.delivery_check:
                #     count += rec.delivery_factor
                #     sum_total += (int(rec.delivery) * rec.delivery_factor)
                # if rec.quality_check:
                #     count += rec.quality_factor
                #     sum_total += (int(rec.quality) * rec.quality_factor)
                # if rec.document_check:
                #     count += rec.document_factor
                #     sum_total += (int(rec.document) * rec.document_factor)
                # if rec.commitment_check:
                #     count += rec.commitment_factor
                #     sum_total += (int(rec.commitment) * rec.commitment_factor)
                # if rec.dependability_check:
                #     count += rec.dependability_factor
                #     sum_total += (int(rec.dependability) * rec.dependability_factor)
                # if rec.skill_check:
                #     count += rec.skill_factor
                #     sum_total += (int(rec.skill) * rec.skill_factor)
                # if rec.support_check:
                #     count += rec.support_factor
                #     sum_total += (int(rec.support) * rec.support_factor)
                # if rec.relation_check:
                #     count += rec.relation_factor
                #     sum_total += (int(rec.relation) * rec.relation_factor)
                # if rec.other_check:
                #     count += rec.other_factor
                #     sum_total += (int(rec.other) * rec.other_factor)
            if rec.on_time_rate_check:
                count += rec.on_time_rate_factor
                sum_total += (int(rec.on_time_rate_star) * rec.on_time_rate_factor)
            if rec.fulfillment_check:
                count += rec.fulfillment_factor
                sum_total += (int(rec.fulfillment_star) * rec.fulfillment_factor)

            if count == 0:
                pass
                # raise ValidationError('Error division by 0!')
            else:
                rec.final_point = sum_total/count
                rec.final_rate = str(round(sum_total/count))
        return res

class VendorEvaluationTemplateEvaluation(models.Model):
    _name = 'vendor.evaluation.template.eval'
    _description = 'Vendor Evaluation Template Evaluation'

    point = [
        ('0', 'Not Use'),
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Satisfied'),
        ('4', 'Good'),
        ('5', 'Excellent')
    ]

    evaluation_id = fields.Many2one(comodel_name='vendor.evaluation', string='Evaluation')
    state = fields.Selection(related='evaluation_id.state')

    name = fields.Char(string='Evaluation Name', required=True)
    eval_factor = fields.Integer(string="Factor", default=1)
    eval_rate = fields.Selection(point, string="Rate", default=point[0][0])
    eval_comment = fields.Char(string="Comment")
