from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError

class MaintenanceFuelLogs(models.Model):
    _name = 'maintenance.fuel.logs'
    _description = 'Maintenance Fuel Logs'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    @api.depends('fuel_type','liter')
    def _total_price(self):
        for line in self:
            total_price = 0
            if line.fuel_type and line.liter:
                total_price = line.fuel_type.standard_price * line.liter
            line.total_price = total_price

    name = fields.Char("Fuel Logs",default='New')
    vehicle = fields.Many2one('maintenance.equipment', string='Vehicle', domain="[('vehicle_checkbox', '=', True)]", required=True)
    date = fields.Datetime(string='Date', required=True)
    createon = fields.Date('Created On', tracking=True, default=fields.Date.context_today,
                               help="Date requested for the maintenance to happen")
    createby = fields.Many2one(comodel_name='res.users', string='Created By', default=lambda self: self.env.user)
    liter = fields.Float(string='Cumulative Fuel Liter', required=True)
    total_price = fields.Float(string='Total Price', compute='_total_price', store=True)
    fuel_type = fields.Many2one('product.product', string='Fuel Type',
                                domain="[('type','=','product')]")
    current_fuel = fields.Float(string=' Current Fuel Meter', required=True)
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    refueling_schema = fields.Selection([('fuel_stock', 'Fuel Stock'), ('gas_station', 'Gas Station')], string='Refueling Schema')
    location_id = fields.Many2one('stock.location', string="Source Location", domain="[('usage', '=', 'internal')]")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location", domain="[('usage', '=', 'internal')]")
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], string='State', default='draft')
    create_bill_or_invoice = fields.Selection([('bill', 'Create Bill'), ('invoice', 'Create Invoice')], string='Create Bill or Invoice', default='bill')

    delivery_order_count = fields.Integer(compute='_compute_delivery_order_count', string='Delivery Orders')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice')
    odometer = fields.Integer(string='Odometer')
    hour_meter = fields.Integer(string='Hourmeter')
    fuel_usage = fields.Integer(string='Fuel Usage')
    before_refill = fields.Float(string='Before Refill')
    after_refill = fields.Float(string='After Refill')
    not_fueling = fields.Boolean(string='Not Fueling', default=False)

    @api.onchange('before_refill', 'after_refill')
    def _onchange_compute_fuel_usage(self):
        for record in self:
            record.liter = record.after_refill - record.before_refill
            record.current_fuel = record.after_refill

    def _compute_delivery_order_count(self):
        for record in self:
            record.delivery_order_count = self.env['stock.picking'].search_count([('fuel_log_id', '=', record.id)])

    def _compute_invoice_count(self):
        for record in self:
            if record.create_bill_or_invoice:
                record.invoice_count = self.env['account.move'].search_count([('fuel_log_id', '=', record.id)])
            else:
                record.invoice_count = False

    def action_show_delivery_order(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('fuel_log_id', '=', self.id)]
        return action

    def action_show_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['domain'] = [('fuel_log_id', '=', self.id)]
        return action

    @api.depends('vehicle')
    def _compute_fuel_type(self):
        if self.vehicle:
            self.fuel_type = self.vehicle.fuel_type.id

    # def name_get(self):
    #     res = []
    #     for rec in self:
    #         res.append((rec.id, 'FUL / %s' % (rec.date)))
    #     return res

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('maintenance.fuel.logs.sequence')
        return super(MaintenanceFuelLogs, self).create(vals)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Fuel Logs'),
            'template': '/equip3_asset_fms_masterdata/static/xls/fuel_logs_template.xls'
        }]

    def action_confirm(self):
        if self.refueling_schema == 'fuel_stock':
            self.state = 'confirm'
            available_quantity = 0
            stock_quants = self.env['stock.quant'].search([('location_id','=',self.location_id.id),('product_id','=',self.fuel_type.id)])
            for stock in stock_quants:
                available_quantity += stock.available_quantity
            if self.liter > available_quantity:
                raise UserError(_("There\'s not enough stock of %s in %s", self.fuel_type.display_name, self.location_id.display_name))
            else:
                try:
                    stock_picking = self.env['stock.picking'].create({
                        'fuel_log_id': self.id,
                        'picking_type_id': self.env.ref('stock.picking_type_out').id,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.location_dest_id.id,
                        'analytic_account_group_ids': [(6, 0, self.analytic_group.ids)],
                        'origin': self.name,
                        'company_id': self.env.user.company_id.id,
                        'branch_id': self.vehicle.branch_id.id,
                        'scheduled_date': fields.Datetime.now(),
                    })
                    self.env['stock.move'].create({
                        'picking_id': stock_picking.id,
                        'name': self.name,
                        'product_id': self.fuel_type.id,
                        'product_uom_qty': self.liter,
                        'product_uom': self.fuel_type.uom_id.id,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.location_dest_id.id,
                        'analytic_account_group_ids': [(6, 0, self.analytic_group.ids)],
                        'date': fields.Datetime.now(),
                        'quantity_done': self.liter,
                    })
                    self.state = 'confirm'
                except Exception as e:
                    raise UserError(_('Error!\n%s') % (e))
        if self.refueling_schema == 'gas_station':
            move_line = []
            self.state = 'confirm'
            # invoice
            if self.create_bill_or_invoice == 'invoice':
                move_line.append((0, 0, {
                            'name': self.fuel_type.name,
                            'product_id': self.fuel_type.id,
                            'account_id': self.fuel_type.categ_id.property_account_income_categ_id.id,
                            'quantity': self.liter,
                            'price_unit': self.fuel_type.standard_price,
                        }))
                move_id = self.env['account.move'].create({
                        'partner_id' : self.create_uid.partner_id.id,
                        'fuel_log_id': self.id,
                        'invoice_date' : fields.datetime.today(),
                        'journal_id' : self.env['account.journal'].search([('type', '=', 'sale')], limit=1).id,
                        'move_type' : 'out_invoice',
                        'invoice_line_ids' : move_line
                    })
            # vbill
            if self.create_bill_or_invoice == 'bill':
                move_line.append((0, 0, {
                            'name': self.fuel_type.name,
                            'product_id': self.fuel_type.id,
                            'account_id': self.fuel_type.categ_id.property_account_expense_categ_id.id,
                            'quantity': self.liter,
                            'price_unit': self.fuel_type.standard_price,
                        }))
                move_id = self.env['account.move'].create({
                        'partner_id' : self.create_uid.partner_id.id,
                        'fuel_log_id': self.id,
                        'invoice_date' : fields.datetime.today(),
                        'journal_id' : self.env['account.journal'].search([('type', '=', 'purchase')], limit=1).id,
                        'move_type' : 'in_invoice',
                        'invoice_line_ids' : move_line
                    })

            maintenance_hour_meter = []
            maintenance_odometer = []
            for record in self:
                if record.odometer:
                    odometer_vals_vehicle = self._prepare_maintenance_odometer(record.vehicle.id, record.date, record.odometer)
                    maintenance_odometer.append(odometer_vals_vehicle)

                if record.hour_meter:
                    hour_meter_vals_vehicle = self._prepare_maintenance_hour_meter(record.vehicle.id, record.date, record.hour_meter)
                    maintenance_hour_meter.append(hour_meter_vals_vehicle)

            if maintenance_hour_meter:
                self.env['maintenance.hour.meter'].create(maintenance_hour_meter)

            if maintenance_odometer:
                self.env['maintenance.vehicle'].create(maintenance_odometer)


    def _prepare_maintenance_hour_meter(self, equipment_id, end_time, hour_meter_value):
        """
        Prepare a maintenance hour meter record for the given asset with the given values
        """
        if hour_meter_value > 0:
            vals = {
                'maintenance_asset': equipment_id,
                'date': end_time,
                'total_value': hour_meter_value,
            }
            return vals

    def _prepare_maintenance_odometer(self, equipment_id, end_time, odometer_value):
        """
        Prepare a maintenance odometer record for the given vehicle with the given values
        """
        if odometer_value > 0:
            vals = {
                'maintenance_vehicle': equipment_id,
                'date': end_time,
                'total_value': odometer_value,
            }
            return vals

    @api.model
    def default_get(self, fields):
        vals = super(MaintenanceFuelLogs, self).default_get(fields)
        location_dest_id = self.env['stock.location'].search([('name','ilike','Scrap')],limit =1)
        if location_dest_id:
            vals['location_dest_id'] = location_dest_id.id
        return vals

    @api.onchange('vehicle')
    def _onchange_vehicle(self):
        for rec in self:
            if rec.vehicle.fuel_type:
                rec.fuel_type = rec.vehicle.fuel_type
            else:
                rec.fuel_type = False

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fuel_log_id = fields.Many2one('maintenance.fuel.logs', string='Fuel Logs')

class AccountMove(models.Model):
    _inherit = 'account.move'

    fuel_log_id = fields.Many2one('maintenance.fuel.logs', string='Fuel Logs')
