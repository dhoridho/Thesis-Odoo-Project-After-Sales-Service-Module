# -*- coding: utf-8 -*-
from odoo import models, fields


class PosOrderReport(models.Model):
    _inherit = "report.pos.order"

    log_adult_male_count = fields.Integer(string='Adult Male')
    log_adult_female_count = fields.Integer(string='Adult Female')
    log_child_male_count = fields.Integer(string='Child Male')
    log_child_female_count = fields.Integer(string='Child Female')
    log_adult_count = fields.Integer(string='Adult')
    log_child_count = fields.Integer(string='Child')
    log_male_count = fields.Integer(string='Male')
    log_female_count = fields.Integer(string='Female')
    log_total_count = fields.Integer(string='Total Customer')

    def _select(self):
        select = ','.join(['s.%s AS %s' % (field, field) for field in [
            'log_adult_male_count',
            'log_adult_female_count',
            'log_child_male_count',
            'log_child_female_count',
            'log_adult_count',
            'log_child_count',
            'log_male_count',
            'log_female_count',
            'log_total_count',
        ]])
        return super(PosOrderReport, self)._select() + ',' + select

    def _group_by(self):
        select = ','.join(['s.%s' % field for field in [
            'log_adult_male_count',
            'log_adult_female_count',
            'log_child_male_count',
            'log_child_female_count',
            'log_adult_count',
            'log_child_count',
            'log_male_count',
            'log_female_count',
            'log_total_count',
        ]])
        return super(PosOrderReport, self)._group_by() + ',' + select
