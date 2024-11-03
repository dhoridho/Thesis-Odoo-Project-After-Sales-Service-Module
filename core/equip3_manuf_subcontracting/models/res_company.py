from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    use_subcontracting = fields.Boolean(string='Use Subcontracting')
    subcontracting_warehouse_id = fields.Many2one('stock.warehouse')

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        company._create_per_company_subcontracting_warehouse()
        return company

    @api.model
    def create_missing_subcontracting_warehouse(self):
        companies = self.env['res.company'].sudo().search([])
        company_with_subcontracting_wh = companies.filtered(lambda c: c.subcontracting_warehouse_id)
        company_without_subcontracting_wh = companies - company_with_subcontracting_wh

        company_with_subcontracting_wh._check_subcontracting_warehouse_code()
        company_without_subcontracting_wh._create_or_update_subcontracting_warehouse()

    def _create_per_company_subcontracting_warehouse(self):
        self._create_or_update_subcontracting_warehouse()

    def _get_subcontracting_warehouse_code(self):
        self.ensure_one()
        if not self.company_code:
            return False
        return '%sS' % ''.join(self.company_code[:4])

    def _check_subcontracting_warehouse_code(self):
        for company in self:
            subcontracting_warehouse_code = company._get_subcontracting_warehouse_code()
            if subcontracting_warehouse_code is False:
                continue
            if company.subcontracting_warehouse_id.code != subcontracting_warehouse_code:
                company.subcontracting_warehouse_id.write({'code': subcontracting_warehouse_code})

    def _create_or_update_subcontracting_warehouse(self):
        for company in self:
            subcontracting_warehouse_code = company._get_subcontracting_warehouse_code()

            if subcontracting_warehouse_code is False:
                continue

            warehouse_with_same_code = self.env['stock.warehouse'].sudo().search([
                ('company_id', '!=', company.id),
                ('code', '=', subcontracting_warehouse_code)], limit=1)

            if warehouse_with_same_code:
                raise ValidationError(_('There is already a warehouse with the same name (%s), Please change the warehouse name first.' % warehouse_with_same_code.display_name))

            subcontracting_warehouse = self.env['stock.warehouse'].sudo().search([
                ('company_id', '=', company.id),
                ('code', '=', subcontracting_warehouse_code)], limit=1)
                
            if not subcontracting_warehouse:
                subcontracting_warehouse = self.env['stock.warehouse'].sudo().create({
                    'name': "Subcontracting Warehouse",
                    'code': subcontracting_warehouse_code,
                    'company_id': company.id,
                    'partner_id': company.partner_id.id})
            
            if subcontracting_warehouse.code != subcontracting_warehouse_code:
                subcontracting_warehouse.code = subcontracting_warehouse_code
            
            company.subcontracting_warehouse_id = subcontracting_warehouse.id
