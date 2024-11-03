import math
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockScrapRequestLog(models.Model):
    _name = 'stock.scrap.request.log'
    _description = 'Product Usage Logs'
    _rec_name = 'scrap_request_id'

    scrap_request_id = fields.Many2one('stock.scrap.request', string='Product Usage', required=True)
    total_lines = fields.Integer(string='Total Lines', compute='_compute_lines')
    lines_processed = fields.Integer(string='Processed Lines', compute='_compute_lines')

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('queue', 'Queue'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], string='Status', default='draft', required=True, compute='_compute_state', store=True)

    line_ids = fields.One2many('stock.scrap.request.log.line', 'log_id', string='Batch', readonly=True)
    next_line_id = fields.Many2one('stock.scrap.request.log.line', compute='_compute_next_line')

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

    @api.depends('scrap_request_id', 'scrap_request_id.scrap_ids', 'scrap_request_id.scrap_ids.is_validated')
    def _compute_lines(self):
        for record in self:
            lines = record.scrap_request_id.scrap_ids
            record.total_lines = len(lines)
            record.lines_processed = len(lines.filtered(lambda o: o.is_validated))

    def run(self):
        self.ensure_one()

        request = self.scrap_request_id
        batch = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_control.stock_scrap_validation_per_batch', '500'))
        request_lines = request.scrap_ids.sorted(key=lambda o: o.id)

        for i in range(math.ceil(len(request_lines) / batch)):
            self.env['stock.scrap.request.log.line'].create({
                'sequence': i + 1,
                'log_id': self.id,
                'name': _('Batch %s' % (i + 1)),
                'request_line_ids_str': request_lines[i * batch: (i + 1) * batch].ids
            })

        if self.next_line_id:
            self.next_line_id.run()

    def action_view_cron(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('base.ir_cron_act')
        crons = self.env['ir.cron'].with_context(active_test=False).search([('scrap_log_line_id', 'in', self.line_ids.ids)])
        action['domain'] = [('id', 'in', crons.ids)]
        return action

    def refresh(self):
        pass


class StockScrapRequestLogLine(models.Model):
    _name = 'stock.scrap.request.log.line'
    _description = 'Product Usage Logs Line'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(required=True)
    log_id = fields.Many2one('stock.scrap.request.log', required=True, ondelete='cascade')

    cron_id = fields.Many2one('ir.cron', string='Scheduled Action', required=False)
    cron_active = fields.Boolean(related='cron_id.active')

    request_line_ids = fields.One2many('stock.scrap', compute='_compute_stock_scrap_request_lines')
    total_lines = fields.Integer(string='Total Lines', compute='_compute_stock_scrap_request_lines')
    lines_processed = fields.Integer(string='Processed Lines', compute='_compute_stock_scrap_request_lines')
    request_line_ids_display = fields.Char(compute='_compute_stock_scrap_request_lines')

    state = fields.Selection(selection=[
        ('queue', 'Queue'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], string='Status', default='queue', required=True)

    error_message = fields.Text(readonly=True)

    # technical fields
    request_line_ids_str = fields.Char()

    @api.depends('request_line_ids_str')
    def _compute_stock_scrap_request_lines(self):
        for record in self:
            request_line_ids = eval(record.request_line_ids_str or '[]')
            request_lines = self.env['stock.scrap'].browse(request_line_ids)
            record.request_line_ids = [(6, 0, request_lines.ids)]
            record.total_lines = len(request_lines)
            record.lines_processed = len(request_lines.filtered(lambda o: o.is_validated))

            id_from = request_line_ids and request_line_ids[0] or False
            id_to = request_line_ids and request_line_ids[-1] or False
            record.request_line_ids_display = '[%s - %s]' % (id_from, id_to)

    def _prepare_cron_values(self):
        self.ensure_one()
        request = self.log_id.scrap_request_id
        return {
            'scrap_log_line_id': self.id,
            'priority': 0,
            'name': _('Validate Product Usage (%s) %s' % (request.display_name, self.name)),
            'model_id': self.env.ref('equip3_inventory_control.model_stock_scrap_request_log_line').id,
            'model_name': 'stock.scrap.request.log.line',
            'state': 'code',
            'code': "model.browse(%s).do_validation_batch()" % (self.id, ),
            'user_id': self.env.ref('base.user_root').id,
            'numbercall': 1,
            'interval_type': 'days',
            'interval_number': 1,
            'doall': False,
            'nextcall': fields.Datetime.now()
        }

    def run(self):
        self.cron_id = self.env['ir.cron'].create(self._prepare_cron_values()).id

    def do_validation_batch(self):
        self.request_line_ids._request(log_line=self)
        self.state = 'done'

        next_line = self.log_id.next_line_id
        if next_line:
            next_line.run()
        else:
            self.log_id.scrap_request_id._done_request()

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
