# -*- coding:utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class VendorEvaluation(models.Model):
    _name = 'vendor.evaluation'
    _description = 'Vendor Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _rec_name = 'name'

    name = fields.Char('Document number', default='/', readonly=True, copy=False)
    point = [
        ('0', 'Not Use'),
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Satisfied'),
        ('4', 'Good'),
        ('5', 'Excellent')
    ]

    state = fields.Selection([('draft', 'Draft'), ('request', 'Request Approval'), ('approved', 'Approved'),
                              ('rejected', 'Rejected'), ('cancelled', 'Cancelled')],
                             string='State', default="draft", track_visibility='onchange')

    def draft_request(self):
        for rec in self:
            rec.state = 'request'
        self.calculate()

    def request_draft(self):
        for rec in self:
            rec.state = 'draft'

    def request_approved(self):
        for rec in self:
            rec.state = 'approved'

    def request_rejected(self):
        for rec in self:
            rec.state = 'rejected'

    def approved_cancelled(self):
        for rec in self:
            rec.state = 'cancelled'

    # Supplier Information
    vendor = fields.Many2one('res.partner', string="Vendor", required=True, ondelete='cascade', readonly=True,
                             states={'draft': [('readonly', False)]})
    business = fields.Char('Business Title', readonly=True, states={'draft': [('readonly', False)],
                                                                    'request': [('readonly', False)]})
    email = fields.Char('Email', readonly=True, states={'draft': [('readonly', False)],
                                                        'request': [('readonly', False)]})
    date = fields.Date('Date Entry', default=lambda self: fields.Date.today(), readonly=True,
                       states={'draft': [('readonly', False)], 'request': [('readonly', False)]})
    period_start = fields.Date('Review Period', required=True, readonly=True, states={'draft': [('readonly', False)]})
    period_end = fields.Date(required=True, readonly=True, states={'draft': [('readonly', False)]})
    manager = fields.Many2one('res.users', string="Manager", required=True, readonly=True,
                              states={'draft': [('readonly', False)]})
    is_manager = fields.Boolean(compute='check_manager')
    user_id = fields.Many2one('res.users', 'Current User', compute='_get_current_user')

    def _get_current_user(self):
        self.user_id = self.env.uid

    @api.depends('manager')
    def check_manager(self):
        for rec in self:
            if rec.manager.id == rec.user_id.id:
                rec.is_manager = True
            else:
                rec.is_manager = False

    @api.onchange('vendor')
    def onchange_vendor_email(self):
        self.email = self.vendor.email

    _sql_constraints = [
        ('period_constraint', 'CHECK(period_start <= period_end)', 'End Period can not be lower than Start Period!'),
        ('name_unique', 'unique(name)', "Document number must be unique!")
    ]

    # Evaluation Criteria
    # Criteria 1
    price_check = fields.Boolean(string="1. Price policy, terms of payment, discount", default=1, readonly=True,
                                 states={'draft': [('readonly', False)]})
    price_factor = fields.Integer(string="Factor", default=1, readonly=True,
                                  states={'draft': [('readonly', False)]})
    price = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                             states={'draft': [('readonly', False)]})
    price_cmt = fields.Char(string="Comment", readonly=True,
                            states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('price_factor', 'price')
    def check1_price_factor(self):
        for rec in self:
            if rec.price_check and rec.price_factor <= 0:
                raise ValidationError('Factor of criteria 1 must be higher than 0!')
            if rec.price_check and not rec.price:
                raise ValidationError('Criteria 1 has not been evaluated yet!')

    # Criteria 2
    delivery_check = fields.Boolean(string="2. Delivery on schedule, exact quantity & transportation service",
                                    default=1, readonly=True, states={'draft': [('readonly', False)]})
    delivery_factor = fields.Integer(string="Factor", default=1, readonly=True, states={'draft': [('readonly', False)]})
    delivery = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                                states={'draft': [('readonly', False)]})
    delivery_cmt = fields.Char("Comment", readonly=True,
                               states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('delivery_factor', 'delivery')
    def check2_delivery_factor(self):
        for rec in self:
            if rec.delivery_check and rec.delivery_factor <= 0:
                raise ValidationError('Factor of criteria 2 must be higher than 0!')
            if rec.delivery_check and not rec.delivery:
                raise ValidationError('Criteria 2 has not been evaluated yet!')

    # Criteria 3
    quality_check = fields.Boolean(string="3. Quality of goods, services & conformance to specifications", default=1,
                                   readonly=True, states={'draft': [('readonly', False)]})
    quality_factor = fields.Integer(string="Factor", default=1, readonly=True, states={'draft': [('readonly', False)]})
    quality = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                               states={'draft': [('readonly', False)]})
    quality_cmt = fields.Char(string="Comment", readonly=True,
                              states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('quality_factor', 'quality')
    def check3_quality_factor(self):
        for rec in self:
            if rec.quality_check and rec.quality_factor <= 0:
                raise ValidationError('Factor of criteria 3 must be higher than 0!')
            if rec.quality_check and not rec.quality:
                raise ValidationError('Criteria 3 has not been evaluated yet!')

    # Criteria 4
    document_check = fields.Boolean(string="4. Punctuality & accuracy of documents, ", default=1, readonly=True,
                                    states={'draft': [('readonly', False)]})
    document_factor = fields.Integer(string="Factor", default=1, readonly=True, states={'draft': [('readonly', False)]})
    document = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                                states={'draft': [('readonly', False)]})
    document_cmt = fields.Char(string="Comment", readonly=True,
                               states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('document_factor', 'document')
    def check4_document_factor(self):
        for rec in self:
            if rec.document_check and rec.document_factor <= 0:
                raise ValidationError('Factor of criteria 4 must be higher than 0!')
            if rec.document_check and not rec.document:
                raise ValidationError('Criteria 4 has not been evaluated yet!')

    # Criteria 5
    commitment_check = fields.Boolean(string="5. Commitments for distributorship, commitments towards improvement",
                                      default=1, readonly=True, states={'draft': [('readonly', False)]})
    commitment_factor = fields.Integer(string="Factor", default=1, readonly=True,
                                       states={'draft': [('readonly', False)]})
    commitment = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                                  states={'draft': [('readonly', False)]})
    commitment_cmt = fields.Char(string="Comment", readonly=True,
                                 states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('commitment_factor', 'commitment')
    def check5_commitment_factor(self):
        for rec in self:
            if rec.commitment_check and rec.commitment_factor <= 0:
                raise ValidationError('Factor of criteria 5 must be higher than 0!')
            if rec.commitment_check and not rec.commitment:
                raise ValidationError('Criteria 5 has not been evaluated yet!')

    # Criteria 6
    dependability_check = fields.Boolean(string="6. Experience, dependability & reputation of vendor", default=1,
                                         readonly=True, states={'draft': [('readonly', False)]})
    dependability_factor = fields.Integer(string="Factor", default=1, readonly=True,
                                          states={'draft': [('readonly', False)]})
    dependability = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                                     states={'draft': [('readonly', False)]})
    dependability_cmt = fields.Char(string="Comment", readonly=True,
                                    states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('dependability_factor', 'dependability')
    def check6_dependability_factor(self):
        for rec in self:
            if rec.dependability_check and rec.dependability_factor <= 0:
                raise ValidationError('Factor of criteria 6 must be higher than 0!')
            if rec.dependability_check and not rec.dependability:
                raise ValidationError('Criteria 6 has not been evaluated yet!')

    # Criteria 7
    skill_check = fields.Boolean(string="7. Communication & Listening skills", default=1, readonly=True,
                                 states={'draft': [('readonly', False)]})
    skill_factor = fields.Integer(string="Factor", default=1, readonly=True, states={'draft': [('readonly', False)]})
    skill = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                             states={'draft': [('readonly', False)]})
    skill_cmt = fields.Char(string="Comment", readonly=True,
                            states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('skill_factor', 'skill')
    def check7_dependability_factor(self):
        for rec in self:
            if rec.skill_check and rec.skill_factor <= 0:
                raise ValidationError('Factor of criteria 7 must be higher than 0!')
            if rec.skill_check and not rec.skill:
                raise ValidationError('Criteria 7 has not been evaluated yet!')

    # Criteria 8
    support_check = fields.Boolean(string="8. Support & solve the problems, responsiveness to claims", default=1,
                                   readonly=True, states={'draft': [('readonly', False)]})
    support_factor = fields.Integer(string="Factor", default=1, readonly=True, states={'draft': [('readonly', False)]})
    support = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                               states={'draft': [('readonly', False)]})
    support_cmt = fields.Char(string="Comment", readonly=True,
                              states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('support_factor', 'support')
    def check8_support_factor(self):
        for rec in self:
            if rec.support_check and rec.support_factor <= 0:
                raise ValidationError('Factor of criteria 8 must be higher than 0!')
            if rec.support_check and not rec.support:
                raise ValidationError('Criteria 8 has not been evaluated yet!')

    # Criteria 9
    relation_check = fields.Boolean(string="9. Business relationship & historical transactions", default=1,
                                    readonly=True, states={'draft': [('readonly', False)]})
    relation_factor = fields.Integer(string="Factor", default=1, readonly=True, states={'draft': [('readonly', False)]})
    relation = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                                states={'draft': [('readonly', False)]})
    relation_cmt = fields.Char(string="Comment", readonly=True,
                               states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('relation_factor', 'relation')
    def check9_support_factor(self):
        for rec in self:
            if rec.relation_check and rec.relation_factor <= 0:
                raise ValidationError('Factor of criteria 9 must be higher than 0!')
            if rec.relation_check and not rec.relation:
                raise ValidationError('Criteria 9 has not been evaluated yet!')

    # Criteria 10
    other_check = fields.Boolean(string="10. Other", default=1, readonly=True, states={'draft': [('readonly', False)]})
    other_factor = fields.Integer(string="Factor", default=1, readonly=True, states={'draft': [('readonly', False)]})
    other = fields.Selection(point, string="Rate", default=point[0][0], readonly=True,
                             states={'draft': [('readonly', False)]})
    other_cmt = fields.Char(string="Comment", readonly=True,
                            states={'draft': [('readonly', False)], 'request': [('readonly', False)]})

    @api.constrains('other_factor', 'other')
    def check9a_other_factor(self):
        for rec in self:
            if rec.other_check and rec.other_factor <= 0:
                raise ValidationError('Factor of criteria 10 must be higher than 0!')
            if rec.other_check and not rec.other:
                raise ValidationError('Criteria 10 has not been evaluated yet!')

    # Evaluation Report
    final_point = fields.Float(readonly=True, store=True, string="Final Point")
    final_rate = fields.Selection(point, readonly=True, store=True, string="Final Evaluated")
    final_cmt = fields.Char(string="Final Comment", states={'cancelled': [('readonly', True)]})

    def calculate(self):
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
            if count == 0:
                pass
                # raise ValidationError('Error division by 0!')
            else:
                rec.final_point = sum_total/count
                rec.final_rate = str(round(sum_total/count))

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError('You can not delete record when status is not draft')
        return super(VendorEvaluation, self).unlink()

    @api.model
    def create(self, vals):
        rec = super(VendorEvaluation, self).create(vals)
        number = self.env['ir.sequence'].next_by_code('vendor_eval_seq')
        rec.name = number
        rec.calculate()
        return rec

    def write(self, vals):
        rec = super(VendorEvaluation, self).write(vals)
        if 'final_point' not in vals and 'final_rate' not in vals:
            self.calculate()
        return rec
