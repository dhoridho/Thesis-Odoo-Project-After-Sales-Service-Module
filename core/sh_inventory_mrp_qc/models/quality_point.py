# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ShQcPoint(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'sh.qc.point'
    _description = "Quality Point"

    product_id = fields.Many2one("product.product", "Product")
    type_id = fields.Boolean(string="Type Id")
    logged_user = fields.Many2one(
        'res.users', 'Responsible', readonly=True, default=lambda self: self.env.user)
    company_id = fields.Many2one(
        'res.company', string="Company", default=lambda self: self.env.company)
    name = fields.Char(string="Name", default='New', readonly=True, copy=False)
    operation = fields.Many2one("stock.picking.type", "Picking Type")
    team = fields.Many2one("sh.qc.team", "Team")
    sh_message = fields.Text("Message if Fail")
    sh_instruction = fields.Text("Instruction")
    type = fields.Selection([('type1', 'Pass Fail'), ('type2', 'Measurement'),
                             ('type3', 'Take a Picture'), ('type4', 'Text')], 'Type')
    sh_norm = fields.Float("Norm")
    sh_unit_to = fields.Float("From")
    sh_unit_from = fields.Float("To")
    sh_signature = fields.Text(string="")
    is_mandatory = fields.Boolean("QC Mandatory ?")
    number_of_test = fields.Integer(
        "Maximum number of tests allowed.", default=1)
    product_ids = fields.Many2many("product.product", "qc_product_rel", "qc_id", "product_id", "Products")
    operation_ids = fields.Many2many("stock.picking.type", "qc_operation_rel", "qc_id", "operation_id", "Picking Types")


    @api.model
    def create(self, vals):
        if 'company_id' in vals and vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].with_context(
                with_company=vals['company_id']).next_by_code('quality.point')
        return super(ShQcPoint, self).create(vals)

    @api.onchange('type')
    def _onchange_marital(self):
        if self.type and self.type == "type2":
            self.type_id = True
        else:
            self.type_id = False
