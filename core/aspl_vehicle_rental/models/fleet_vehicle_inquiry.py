# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import models, fields, api, _

class CrmLead(models.Model):
    _inherit = "crm.lead"

    vehicle_model = fields.Many2one("fleet.vehicle", string="Vehicle Model")
    from_date = fields.Datetime("From Date")
    to_date = fields.Datetime("To Date")
    sale_number = fields.Integer(compute='_compute_sale_amount_total', string="Number of Quotations", default="5")
    fleet_order_ids = fields.One2many('fleet.vehicle.order', 'opportunity_id', string='Orders')
    vehicle_type = fields.Many2one("fleet.vehicle.type", string="Vehicle Type")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    @api.depends('fleet_order_ids')
    def _compute_sale_amount_total(self):
        for lead in self:
            total = 0.0
            nbr = 0
            company_currency = lead.company_currency or self.env.user.company_id.currency_id
            for order in lead.fleet_order_ids:
                if order.state in ('draft', 'confirm',):
                    nbr += 1
                if order.state not in ('draft', 'sent', 'cancel'):
                    total += order.currency_id.compute(order.amount_untaxed, company_currency)
            lead.sale_amount_total = total
            lead.sale_number = nbr
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: