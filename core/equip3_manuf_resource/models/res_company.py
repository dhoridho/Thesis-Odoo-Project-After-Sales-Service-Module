from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    mrp_resource_calendar_ids = fields.One2many(
        'resource.calendar', 'mrp_company_id', 'MRP Working Hours')
    mrp_resource_calendar_id = fields.Many2one(
        'resource.calendar', 'MRP Default Working Hours')

    @api.model
    def _init_data_resource_calendar(self):
        res = super(ResCompany, self)._init_data_resource_calendar()
        self._init_data_mrp_resource_calendar()
        return res

    @api.model
    def _init_data_mrp_resource_calendar(self):
        self.search([('mrp_resource_calendar_id', '=', False)])._create_mrp_resource_calendar()

    def _create_mrp_resource_calendar(self):
        for company in self:
            calendar = company.resource_calendar_id
            if not calendar:
                continue
            
            company.mrp_resource_calendar_id = self.env['resource.calendar'].with_context(
                default_calendar_type='mrp',
                default_source_calendar_id=calendar.id
            ).create({
                'name': _('MRP %s' % (calendar.display_name, )),
                'company_id': company.id,
                'mrp_company_id': company.id,
                'tz': calendar.tz
            }).id

    @api.model
    def create(self, values):
        company = super(ResCompany, self).create(values)
        if not company.mrp_resource_calendar_id:
            company.sudo()._create_mrp_resource_calendar()
        # calendar created from form view: no company_id set because record was still not created
        if not company.mrp_resource_calendar_id.company_id:
            company.mrp_resource_calendar_id.company_id = company.id
        if not company.mrp_resource_calendar_id.mrp_company_id:
            company.mrp_resource_calendar_id.mrp_company_id = company.id
        return company
