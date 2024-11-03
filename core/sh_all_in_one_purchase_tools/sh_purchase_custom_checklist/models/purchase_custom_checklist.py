# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api
from odoo.osv import expression
from datetime import datetime


class PurchaseCustomChecklist(models.Model):
    _name = "purchase.custom.checklist"
    _description = "Purchase Custom Checklist"
    _order = "id desc"

    name = fields.Char("Name", required=True)
    description = fields.Char("Description")
    company_id = fields.Many2one("res.company",
                                 string="Company",
                                 default=lambda self: self.env.company)


class CRMCustomChecklistLine(models.Model):
    _name = "purchase.custom.checklist.line"
    _description = "Purchase Custom Checklist Line"
    _order = "id desc"

    name = fields.Many2one("purchase.custom.checklist", "Name", required=True)
    description = fields.Char("Description")
    updated_date = fields.Date("Date",
                               readonly=True,
                               default=datetime.now().date())
    state = fields.Selection([("new", "New"), ("completed", "Completed"),
                              ("cancelled", "Cancelled")],
                             string="State",
                             default="new",
                             readonly=True,
                             index=True)

    order_id = fields.Many2one("purchase.order")

    def btn_check(self):
        for rec in self:
            rec.write({"state": "completed"})

    def btn_close(self):
        for rec in self:
            rec.write({"state": "cancelled"})

    @api.onchange("name")
    def onchange_custom_chacklist_name(self):
        self.description = self.name.description


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    complete_state = fields.Selection([("completed", "Completed"),
                                       ("cancelled", "Cancelled")],
                                      compute="_compute_complete_check",
                                      string="State",
                                      readonly=True,
                                      index=True,
                                      search="_search_state")

    def _search_state(self, operator, value):
        if operator in ["="]:
            # In case we search against anything else than new, we have to invert the operator
            complete_so_list = []
            incomplete_so_list = []

            for rec in self.sudo().search([]):
                total_cnt = self.env[
                    "purchase.custom.checklist.line"].search_count([
                        ("order_id", "=", rec.id)
                    ])
                compl_cnt = self.env[
                    "purchase.custom.checklist.line"].search_count([
                        ("order_id", "=", rec.id), ("state", "=", "completed")
                    ])

                if total_cnt > 0:
                    rec.custom_checklist = (100.0 * compl_cnt) / total_cnt
                    if rec.custom_checklist == 100:
                        complete_so_list.append(rec.id)
                    else:
                        incomplete_so_list.append(rec.id)
                else:
                    incomplete_so_list.append(rec.id)

        if value:
            return [("id", "in", complete_so_list)]
        else:
            return [("id", "in", incomplete_so_list)]

        return expression.TRUE_DOMAIN

    @api.depends("custom_checklist_ids")
    def _compute_custom_checklist(self):
        if self:
            for rec in self:
                total_cnt = self.env[
                    "purchase.custom.checklist.line"].search_count([
                        ("order_id", "=", rec.id)
                    ])
                compl_cnt = self.env[
                    "purchase.custom.checklist.line"].search_count([
                        ("order_id", "=", rec.id), ("state", "=", "completed")
                    ])

                if total_cnt > 0:
                    rec.custom_checklist = (100.0 * compl_cnt) / total_cnt
                else:
                    rec.custom_checklist = 0

    @api.depends("custom_checklist")
    def _compute_complete_check(self):
        if self:
            for data in self:
                if data.custom_checklist >= 100:
                    data.complete_state = "completed"
                else:
                    data.complete_state = "cancelled"

    custom_checklist_ids = fields.One2many("purchase.custom.checklist.line",
                                           "order_id", "Checklist")
    custom_checklist = fields.Float("Checklist Completed",
                                    compute="_compute_custom_checklist")

    custom_checklist_template_ids = fields.Many2many(
        'purchase.custom.checklist.template')

    @api.onchange('custom_checklist_template_ids')
    def onchange_custom_checklist_template_ids(self):
        update_ids = []
        for i in self.custom_checklist_template_ids:
            for j in i._origin.checklist_template:
                new_id = self.env["purchase.custom.checklist.line"].create({
                    'name':
                    j.id,
                    'description':
                    j.description
                })
                update_ids.append(new_id.id)

        self.custom_checklist_ids = [(6, 0, update_ids)]
