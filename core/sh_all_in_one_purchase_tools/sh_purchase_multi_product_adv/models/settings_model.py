# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    sh_pmps_pro_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        relation="sh_pmps_pro_field_ids_rel_comp_table",
        string="Purchase Product Fields",
    )
    sh_pmps_pro_attr_ids = fields.Many2many(
        comodel_name="product.attribute",
        relation="sh_pmps_pro_attr_ids_rel_comp_table",
        string="Purchase Product Attributes",
    )

class PmpsAdvSettings(models.TransientModel):
    _name = "pmps.adv.settings"
    _description = "Purchase Multi Product Selection Advanced Wizard Settings"

    @api.model
    def sh_get_user_company(self):
        if self.env.user.company_id:
            return self.env.user.company_id.id
        return False

    @api.model
    def get_sh_pmps_pro_field_ids(self):
        if(
            self.env.user.company_id and
            self.env.user.company_id.sh_pmps_pro_field_ids
        ):
            return self.env.user.company_id.sh_pmps_pro_field_ids.ids
        return False

    @api.model
    def get_sh_pmps_pro_attr_ids(self):
        if(
            self.env.user.company_id and
            self.env.user.company_id.sh_pmps_pro_attr_ids
        ):
            return self.env.user.company_id.sh_pmps_pro_attr_ids.ids
        return False

    company_id = fields.Many2one(
        "res.company",
        default=sh_get_user_company
    )
    name = fields.Char(
        string="Name",
        default="Search Products Settings"
    )

    sh_pmps_pro_field_ids = fields.Many2many(
        "ir.model.fields",
        string="Product Fields",
        related="company_id.sh_pmps_pro_field_ids",
        domain=[('model_id.model', 'in', ['product.product','product.template']),
                ('ttype', 'in', ['integer', 'char', 'float', 'boolean', 'many2one', 'selection']),
                ('store', '=', True)
                ],
        default=get_sh_pmps_pro_field_ids,
        readonly=False
    )

    sh_pmps_pro_attr_ids = fields.Many2many(
        "product.attribute",
        string="Product Attributes",
        related="company_id.sh_pmps_pro_attr_ids",
        default=get_sh_pmps_pro_attr_ids,
        readonly=False
    )
