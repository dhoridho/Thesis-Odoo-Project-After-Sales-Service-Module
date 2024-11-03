from odoo import models, fields, api
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, ValidationError
import json


class LabourCostRate(models.Model):
    _name = "labour.cost.rate"
    _inherit = ['mail.thread', 'mail.activity.mixin',]
    _description = "Labour Cost Rate"

    name = fields.Char(string='Name', tracking=True)
    labour_cost_key = fields.Char(string='Labour Cost Key')
    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Position', tracking=True)
    group_of_product_domain_dump = fields.Char(string='Group of Position Domain Dump', compute='_compute_group_of_product_domain_dump')
    product_id = fields.Many2one('product.product', string='Position', tracking=True)
    product_domain_dump = fields.Char(string='Position Domain Dump', compute='_compute_product_domain_dump')
    active_location_id = fields.Many2one('project.location', string='Location', tracking=True)
    active_location_domain_dump = fields.Char(string='Location Domain Dump', compute='_compute_active_location_domain_dump')
    uom_id_domain_dump = fields.Char(string='UOM Domain Dump')
    uom_id = fields.Many2one('uom.uom', string='Periodic')
    rate_amount = fields.Float(string='Amount', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ], string='Status', default='draft', tracking=True)
    rate_periodic = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
        ], string='Periodic', default='hourly', tracking=True)

    _sql_constraints = [
        ('labour_cost_rate_unique_name',
         'unique(name)',
         'Labour cost rate name has to be unique!'),
    ]
    hourly_rate = fields.Float(string='Hourly Rate', compute='_compute_hourly_rate')

    @api.depends('rate_amount', 'rate_periodic')
    def _compute_hourly_rate(self):
        for record in self:
            if record.rate_periodic == 'hourly':
                record.hourly_rate = record.rate_amount
            elif record.rate_periodic == 'daily':
                record.hourly_rate = record.rate_amount / record.project_id.working_hour_hours
            elif record.rate_periodic == 'monthly':
                record.hourly_rate = record.rate_amount / (record.project_id.working_hour_hours * 30)

    @api.constrains('labour_cost_key')
    def _check_labour_cost_key(self):
        for record in self:
            self.env.cr.execute("SELECT COUNT(*) FROM labour_cost_rate WHERE labour_cost_key = %s", (record.labour_cost_key,))
            result = self.env.cr.fetchone()
            if result[0] > 1:
                raise ValidationError('Labour cost rate already exists for this combination of Project, Group of Position, Position and Location!')

    @api.model
    def create(self, vals):
        vals['labour_cost_key'] = str(vals['project_id']) + '_' + str(vals['group_of_product_id']) + '_' + str(vals['product_id']) + '_' + str(vals['active_location_id'])
        return super(LabourCostRate, self).create(vals)

    @api.depends('project_id', 'group_of_product_id')
    def _compute_product_domain_dump(self):
        for record in self:
            if record.project_id:
                if record.project_id.cost_sheet:
                    product_ids = record.project_id.cost_sheet.material_labour_ids.product_id.ids
                    if len(product_ids) > 0:
                        record.product_domain_dump = json.dumps([("id", "in", product_ids)])
                    else:
                        record.product_domain_dump = json.dumps([("id", "=", 0)])
                else:
                    record.product_domain_dump = json.dumps([("id", "=", 0)])
            else:
                record.product_domain_dump = json.dumps([("id", "=", 0)])

    @api.depends('project_id', 'active_location_id')
    def _compute_active_location_domain_dump(self):
        for record in self:
            if record.project_id:
                location_ids = record.project_id.project_location_ids.ids
                if len(location_ids) > 0:
                    record.active_location_domain_dump = json.dumps([("id", "in", location_ids)])
                else:
                    record.active_location_domain_dump = json.dumps([("id", "=", 0)])
            else:
                record.active_location_domain_dump = json.dumps([("id", "=", 0)])

    def _compute_uom_id_domain_dump(self):
        for record in self:
            return

    @api.depends('project_id', 'group_of_product_id')
    def _compute_group_of_product_domain_dump(self):
        for record in self:
            if record.project_id:
                if record.project_id.cost_sheet:
                    gop_ids = record.project_id.cost_sheet.material_labour_ids.group_of_product.ids
                    if len(gop_ids) > 0:
                        record.group_of_product_domain_dump = json.dumps([("id", "in", gop_ids)])
                    else:
                        record.group_of_product_domain_dump = json.dumps([("id", "=", 0)])
                else:
                    record.group_of_product_domain_dump = json.dumps([("id", "=", 0)])
            else:
                record.group_of_product_domain_dump = json.dumps([("id", "=", 0)])

    def update_employee_project_information(self):
        for record in self:
            employee_project_information = self.env['construction.project.information'].search([
                ('project_id', '=', record.project_id.id),
                ('group_of_product_id', '=', record.group_of_product_id.id),
                ('product_id', '=', record.product_id.id),
                ('active_location_id', '=', record.active_location_id.id),
            ])
            if len(employee_project_information) > 0:
                for information in employee_project_information:
                    information.write({
                        'uom_id': record.uom_id.id,
                        'rate_amount': record.rate_amount,
                        'labour_cost_rate_id': record.id,
                    })

    def button_confirm(self):
        for record in self:
            record.write({'state': 'confirmed'})
            record.update_employee_project_information()

    def button_synchronize_rate(self):
        for record in self:
            record.update_employee_project_information()
