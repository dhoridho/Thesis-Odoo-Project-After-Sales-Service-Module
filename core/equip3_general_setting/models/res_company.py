from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    branch_ids = fields.One2many('res.branch', 'company_id', string='Branches')

    @api.model
    def create(self, vals):
        companies = super(ResCompany, self).create(vals)

        """ Create and assign branch to user (if not exists) for newly created company """
        companies._create_and_assign_branch(self.env['res.users'].sudo().search([]))
        companies._assign_warehouse_and_location_branch(
            self.env['stock.warehouse'].sudo().search(
                [('company_id', '=', companies.id)], limit=1),
            companies.branch_ids[0].id if companies.branch_ids else False)

        self._set_required_branch()
        partner_id = self.env['res.partner'].sudo().browse(vals.get('partner_id'))
        if partner_id:
            branch_id = companies.branch_ids[0].id if companies.branch_ids else False
            companies._assign_branch_partner(branch_id, partner_id, companies)
        return companies

    def _assign_branch_partner(self, branch_id, partner_id, company_id):
        partner_id.company_id = company_id
        partner_id.branch_id = branch_id

    def unlink(self):
        result = super(ResCompany, self).unlink()
        self._set_required_branch()
        return result

    @api.model
    def _set_required_branch(self):
        companies = self.sudo().search([])
        companies.write({'show_branch': len(companies) > 1})

    def _create_and_assign_branch(self, users):
        """ Each user at least must have 1 branch active for each company """
        for company in self:
            branch = self.env['res.branch'].search([('company_id', '=', company.id)], limit=1)
            if not branch:
                branch = self.env['res.branch'].create({
                    'name': '%s Branch' % company.name,
                    'company_id': company.id
                })
            for user in users:
                user_branches = user.branch_ids
                if not user_branches.filtered(lambda b: b.company_id == company):
                    user.with_context(bypass_constrains=True).write({'branch_ids': [(4, branch.id)]})

    def _assign_warehouse_and_location_branch(self, warehouses_id, branch_id):
        warehouses_id.branch_id = branch_id
        location_id = self.env['stock.location'].search([
            ('warehouse_id', '=', warehouses_id.id),
            ('active', 'in', [True, False])
        ])
        if location_id:
            location_id.branch_id = branch_id
        return True
