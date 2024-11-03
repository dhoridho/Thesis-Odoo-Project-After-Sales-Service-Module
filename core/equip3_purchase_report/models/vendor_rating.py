# -*- coding:utf-8 -*-

from odoo import tools
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class VendorEvaluationRating(models.Model):
    _name = 'vendor.evaluation.rating'
    _description = "Vendor Evaluation Rating"
    _auto = False

    partner_id = fields.Many2one('res.partner', 'Vendor')
    fulfillment_avg = fields.Float(string="Fulfillment")
    on_time_rate_avg = fields.Float(string="On Time Rate")
    final_point_avg = fields.Float(string="Final Point")
    vendor_evaluation_count = fields.Integer(string='Count')
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(ve.id) as id,
            ve.vendor as partner_id,
            ve.vendor_evaluation_count as vendor_evaluation_count,
            ve.fulfillment_avg as fulfillment_avg,
            ve.on_time_rate_avg as on_time_rate_avg,
            ve.final_point_avg as final_point_avg,
            ve.branch_id as branch_id
        """

        for field in fields.values():
            select_ += field

        from_ = """
                vendor_evaluation ve
                where ve.state = 'approved'
        """

        groupby_ = """
            ve.vendor,
            ve.vendor_evaluation_count,
            ve.fulfillment_avg,
            ve.on_time_rate_avg,
            ve.final_point_avg,
            ve.branch_id
        """

        return '%s (SELECT %s FROM %s GROUP BY %s)' % (with_, select_, from_, groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

class VendorEvaluation(models.Model):
    _inherit = 'vendor.evaluation'

    on_time_rate_res = fields.Float(related='on_time_rate', string="On-Time Delivery Rate (0-100)")
    fulfillment_res = fields.Float(related='fulfillment', string="Fulfillment (0-100)")
    vendor_res = fields.Many2one('res.partner', related='vendor')
    final_point_res = fields.Float(related='final_point', string="Final Point (0-5)")
