from odoo import models, fields, api

class AfterSales(models.Model):
    _name = 'after.sales'

    name = fields.Char('Name')


class ServiceDashboard(models.AbstractModel):
    _name = 'service.dashboard'

    total_service_requests = fields.Integer(compute="_compute_totals", string="Total Service Requests")
    total_warranty_claims = fields.Integer(compute="_compute_totals", string="Total Warranty Claims")

    def _compute_totals(self):
        for record in self:
            record.total_service_requests = self.env['service.request'].search_count([])
            record.total_warranty_claims = self.env['warranty.claim'].search_count([])

    @api.model
    def get_service_request_stats(self):
        """Retrieve service request statistics"""
        return {
            'total_requests': self.env['service.request'].search_count([]),
            'in_progress': self.env['service.request'].search_count([('state', '=', 'in_progress')]),
            'completed': self.env['service.request'].search_count([('state', '=', 'done')]),
            'cancelled': self.env['service.request'].search_count([('state', '=', 'cancel')]),
        }

    @api.model
    def get_warranty_claim_stats(self):
        """Retrieve warranty claim statistics"""
        return {
            'total_claims': self.env['warranty.claim'].search_count([]),
            'in_warranty': self.env['warranty.claim'].search_count([('is_in_warranty', '=', True)]),
            'rejected': self.env['warranty.claim'].search_count([('state', '=', 'rejected')]),
            'completed': self.env['warranty.claim'].search_count([('state', '=', 'completed')]),
        }

    @api.model
    def get_service_type_distribution(self):
        """Get distribution of service types"""
        return self.env['service.request'].read_group(
            [],
            ['service_type', 'id:count'],
            ['service_type']
        )

    @api.model
    def get_monthly_service_trend(self):
        """Get monthly service request trend"""
        return self.env['service.request'].read_group(
            [],
            ['request_month', 'id:count'],
            ['request_month']
        )
