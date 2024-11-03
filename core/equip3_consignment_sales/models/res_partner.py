# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import json


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def update_partner_company_and_branch(self):
        company_ids = self.env['res.company'].search([])
        for company in company_ids:
            partner_company = self.env['res.partner'].search([('name', '=', company.name), ('company_id', '=', company.id)], limit=1)
            if partner_company:
                print(f"➡ BEFORE | partner: {partner_company.name} | company name: {company.name} | branch name: {partner_company.branch_id.name}➡{partner_company.branch_id.id} | branch company: {partner_company.branch_id.company_id.name}")
                branch_company = self.env['res.branch'].search([('company_id', '=', company.id)], order='id asc',limit=1)
                partner_company.write({'company_id': company.id, 'branch_id': branch_company.id})
                print(f"➡ AFTER | partner: {partner_company.name} | company name: {company.name} | branch name: {partner_company.branch_id.name}➡{partner_company.branch_id.id} | branch company: {partner_company.branch_id.company_id.name}")


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 and 'from_company' not in self.env.context else False




    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        default = _default_branch,
        readonly=False)

    filter_branch = fields.Char("filter branch", compute='_compute_filter_branch', store=False)

    is_a_consign = fields.Boolean("Is a Consignee")
    # branch_id = fields.Many2one('res.branch', string="Branch", required=True, default=lambda self: self.env.branch.id if len(
    #     self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    sale_consignment_location_id = fields.Many2one(
        comodel_name='stock.location', string='Location')

    @api.depends('company_id')
    def _compute_filter_branch(self):
        for rec in self:
            rec.filter_branch = json.dumps([('id', 'in', self.env.branches.ids), ('company_id','=', self.company_id.id)])

    @api.model
    def create(self, vals):
        if vals.get('is_a_consign'):
            warehouse_id = self.env['stock.warehouse'].sudo().search([
                ('is_consignment_warehouse', '=', True),
                ('company_id', '=', vals['company_id'])], limit=1)
            usage_view_location = self.env['stock.location'].sudo().search([
                ('usage', '=', 'view'), ('warehouse_id', '=', warehouse_id.id)], limit=1)

            location_vals = {
                'name': "Stock",
                'usage': 'internal',
                'company_id': vals['company_id'],
                'branch_id': vals['branch_id'],
                'location_id': usage_view_location.id,
                'warehouse_id': warehouse_id.id,
            }
            consignment_location = self.env['stock.location'].sudo().create(
                location_vals)
            vals['sale_consignment_location_id'] = consignment_location.id
        return super(ResPartner, self).create(vals)

    def write(self, vals):
        for record in self:
            new_name = vals.get('name', record.name)
            is_a_consign = vals.get('is_a_consign', record.is_a_consign)
            if new_name and is_a_consign:
                sale_consignment_location = record.sale_consignment_location_id
                if not sale_consignment_location:
                    warehouse_id = self.env['stock.warehouse'].sudo().search([
                        ('is_consignment_warehouse', '=', True),
                        ('company_id', '=', self.company_id.id)], limit=1)
                    usage_view_location = self.env['stock.location'].sudo().search(
                        [('usage', '=', 'view'), ('warehouse_id', '=', warehouse_id.id)], limit=1)

                    location_vals = {
                        'name': "Stock",
                        'usage': 'internal',
                        'company_id': record.company_id.id,
                        'branch_id': record.branch_id.id,
                        'location_id': usage_view_location.id,
                        'warehouse_id': warehouse_id.id,
                    }
                    consignment_location = self.env['stock.location'].sudo().create(
                        location_vals)
                    consignment_location.complete_name = f'{new_name}/Stock'
                    vals['sale_consignment_location_id'] = consignment_location.id
                else:
                    sale_consignment_location.complete_name = f'{new_name}/Stock'
        return super(ResPartner, self).write(vals)
