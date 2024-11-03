import math
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockInventoryLog(models.Model):
    _name = 'stock.inventory.log'
    _description = 'Inventory Adjustment Logs'
    _rec_name = 'inventory_id'

    inventory_id = fields.Many2one('stock.inventory', string='Inventory Adjustment', required=True)
    total_lines = fields.Integer(string='Total Lines', compute='_compute_lines')
    lines_processed = fields.Integer(string='Processed Lines', compute='_compute_lines')

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('queue', 'Queue'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], string='Status', default='draft', required=True, compute='_compute_state', store=True)

    line_ids = fields.One2many('stock.inventory.log.line', 'log_id', string='Batch', readonly=True)
    next_line_id = fields.Many2one('stock.inventory.log.line', compute='_compute_next_line')

    @api.depends('line_ids', 'line_ids.sequence', 'line_ids.state')
    def _compute_next_line(self):
        for record in self:
            next_line_id = False
            for line in record.line_ids:
                if line.state == 'queue':
                    next_line_id = line.id
                    break
            record.next_line_id = next_line_id

    @api.depends('line_ids', 'line_ids.state')
    def _compute_state(self):
        for record in self:
            lines = record.line_ids

            if not lines:
                state = 'draft'
            else:
                state = 'running'
                if any(line.state == 'failed' for line in lines):
                    state = 'failed'
                elif all(line.state == 'queue' for line in lines):
                    state = 'queue'
                elif all(line.state == 'done' for line in lines):
                    state = 'done'

            record.state = state

    @api.depends('inventory_id', 'inventory_id.line_ids', 'inventory_id.line_ids.is_validated')
    def _compute_lines(self):
        for record in self:
            lines = record.inventory_id.line_ids
            record.total_lines = len(lines)
            record.lines_processed = len(lines.filtered(lambda o: o.is_validated))

    def run(self):
        self.ensure_one()

        inventory = self.inventory_id
        batch = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.stock_inventory_validation_per_batch', '500'))
        inventory_lines = inventory.line_ids.sorted(key=lambda o: o.id)

        inventory.line_ids.cost_adjustment()

        for i in range(math.ceil(len(inventory_lines) / batch)):
            self.env['stock.inventory.log.line'].create({
                'sequence': i + 1,
                'log_id': self.id,
                'name': _('Batch %s' % (i + 1)),
                'inventory_line_ids_str': inventory_lines[i * batch: (i + 1) * batch].ids
            })

        if self.next_line_id:
            self.next_line_id.run()

    def action_view_cron(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('base.ir_cron_act')
        crons = self.env['ir.cron'].with_context(active_test=False).search([('inventory_log_line_id', 'in', self.line_ids.ids)])
        action['domain'] = [('id', 'in', crons.ids)]
        return action

    def refresh(self):
        pass


class StockInventoryLogLine(models.Model):
    _name = 'stock.inventory.log.line'
    _description = 'Inventory Adjustment Logs Line'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(required=True)
    log_id = fields.Many2one('stock.inventory.log', required=True, ondelete='cascade')

    cron_id = fields.Many2one('ir.cron', string='Scheduled Action', required=False)
    cron_active = fields.Boolean(related='cron_id.active')

    inventory_line_ids = fields.One2many('stock.inventory.line', compute='_compute_inventory_lines')
    total_lines = fields.Integer(string='Total Lines', compute='_compute_inventory_lines')
    lines_processed = fields.Integer(string='Processed Lines', compute='_compute_inventory_lines')
    inventory_line_ids_display = fields.Char(compute='_compute_inventory_lines')

    state = fields.Selection(selection=[
        ('queue', 'Queue'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], string='Status', default='queue', required=True)

    error_message = fields.Text(readonly=True)

    # technical fields
    inventory_line_ids_str = fields.Char()

    @api.depends('inventory_line_ids_str')
    def _compute_inventory_lines(self):
        for record in self:
            inventory_line_ids = eval(record.inventory_line_ids_str or '[]')
            inventory_lines = self.env['stock.inventory.line'].browse(inventory_line_ids)
            record.inventory_line_ids = [(6, 0, inventory_lines.ids)]
            record.total_lines = len(inventory_lines)
            record.lines_processed = len(inventory_lines.filtered(lambda o: o.is_validated))

            id_from = inventory_line_ids and inventory_line_ids[0] or False
            id_to = inventory_line_ids and inventory_line_ids[-1] or False
            record.inventory_line_ids_display = '[%s - %s]' % (id_from, id_to)

    def _prepare_cron_values(self):
        self.ensure_one()
        inventory = self.log_id.inventory_id
        return {
            'inventory_log_line_id': self.id,
            'priority': 0,
            'name': _('Validate Inventory Adjustment (%s) %s' % (inventory.display_name, self.name)),
            'model_id': self.env.ref('equip3_inventory_base.model_stock_inventory_log_line').id,
            'model_name': 'stock.inventory.log.line',
            'state': 'code',
            'code': "model.browse(%s).do_valuations_batch()" % (self.id, ),
            'user_id': self.env.ref('base.user_root').id,
            'numbercall': 1,
            'interval_type': 'days',
            'interval_number': 1,
            'doall': False,
            'nextcall': fields.Datetime.now()
        }

    def run(self):
        self.cron_id = self.env['ir.cron'].create(self._prepare_cron_values()).id

    def do_valuations_batch(self):
        self.inventory_line_ids.stock_adjustment(log_line=self)
        self.state = 'done'

        next_line = self.log_id.next_line_id
        if next_line:
            next_line.run()
        else:
            self.log_id.inventory_id._done_inventory()

    def run_manually(self):
        self.ensure_one()
        if self != self.log_id.next_line_id:
            raise UserError(_('Previous line must be executed first!'))

        if self.state != 'queue':
            raise UserError(_('Cron is already running/executed!'))
        
        if self.cron_id.active:
            self.cron_id.method_direct_trigger()
        
    def re_run(self):
        self.ensure_one()
        self.write({'state': 'queue'})
        self.cron_id.write({
            'nextcall': fields.Datetime.now(),
            'active': True
        })
