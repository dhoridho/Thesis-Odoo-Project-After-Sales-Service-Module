import json
import pytz
from odoo import models, fields, api, _
from odoo.addons.equip3_manuf_other_operations.models.mrp_mps import convert_tz, read_m2o


class MrpMPSDetail(models.TransientModel):
    _name = 'mrp.mps.detail'
    _description = 'Master Production Schedule Detail'

    @api.model
    def tz(self):
        return self.env.context.get('tz', False) or self.env.user.tz

    mps_id = fields.Many2one('mrp.mps', string='MPS', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)

    period = fields.Text(required=True)

    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', 
        domain="""[
        '&',
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id),
            '&',
                '|',
                    ('product_id', '=', product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids', '=', product_id),
                        ('product_id', '=', False),
        ('type', '=', 'normal'),
        ('equip_bom_type', '=', 'mrp')]""")

    bom_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='bom_id.product_uom_id')

    to_produce = fields.Float(string='To Produce', digits='Product Unit of Measure')
    
    expected_duration = fields.Float(string='Expected Duration', digits='Product Unit of Measure')
    workcenter_ids = fields.Many2many('mrp.workcenter', string='Workcenters')

    expected_end_date = fields.Datetime(string='Expected End Date')
    suggested_start_date = fields.Datetime(string='Suggested Start Date')
    suggested_end_date = fields.Datetime(string='Suggested End Date')
    estimated_start_date = fields.Datetime(string='Estimated Start Date')
    estimated_end_date = fields.Datetime(string='Estimated End Date')
    resource_id = fields.Many2one('resource.calendar', string='Resource')
    material_ids = fields.One2many('mrp.mps.detail.material', 'detail_id', string='Materials')

    date_from = fields.Date(string='Period Date From')
    date_to = fields.Date(string='Period Date To')

    # technical fields
    forecasted_data = fields.Text()

    @api.onchange('bom_id')
    def onchange_bom_id(self):
        material_values = [(5,)]
        if self.bom_id:
            for bom_line in self.bom_id.bom_line_ids:
                material_values += [(0, 0, {
                    'detail_id': self.id,
                    'bom_line_id': bom_line.id
                })]
        self.material_ids = material_values

    @api.onchange('bom_id', 'product_id', 'mps_id')
    def _set_mps_bom(self):
        datas = json.loads(self.mps_id.datas or '{}')
        try:
            datas['states'][str(self.product_id.id)]['bom'] = read_m2o(self.bom_id)
        except KeyError:
            return
        self.mps_id.datas = json.dumps(datas, default=str)

    @api.onchange('forecasted_data', 'period')
    def _onchange_forecasted_data(self):
        if not self.forecasted_data or not self.period:
            return
        selected_period = json.loads(self.period or '{}').get('selected', False)
        forecasted = json.loads(self.forecasted_data).get(selected_period, {})
        
        self.date_from = forecasted['date_from']
        self.date_to = forecasted['date_to']

        self.to_produce = forecasted['to_produce']

        self.expected_duration = forecasted['expected_duration']
        self.expected_end_date = convert_tz(forecasted['expected_end_date'].replace('T', ' '), self.tz(), pytz.utc) if forecasted['expected_end_date'] else forecasted['expected_end_date']
        self.suggested_start_date = convert_tz(forecasted['scheduled_date'].replace('T', ' '), self.tz(), pytz.utc) if forecasted['scheduled_date'] else forecasted['scheduled_date']
        self.suggested_end_date = convert_tz(forecasted['scheduled_end_date'].replace('T', ' '), self.tz(), pytz.utc) if forecasted['scheduled_end_date'] else forecasted['scheduled_end_date']
        self.estimated_start_date = convert_tz(forecasted['estimated_date'].replace('T', ' '), self.tz(), pytz.utc) if forecasted['estimated_date'] else forecasted['estimated_date']
        self.estimated_end_date = convert_tz(forecasted['estimated_end_date'].replace('T', ' '), self.tz(), pytz.utc) if forecasted['estimated_end_date'] else forecasted['estimated_end_date']


class MrpMPSDetailMaterial(models.TransientModel):
    _name = 'mrp.mps.detail.material'
    _description = 'Master Production Schedule Detail Material'

    @api.depends('detail_id', 'bom_line_id')
    def _compute_quantities(self):
        for record in self:
            qty_available = 0.0
            incoming_qty = 0.0
            outgoing_qty = 0.0
            virtual_available = 0.0
            free_qty = 0.0

            if record.detail_id and record.bom_line_id:
                warehouse_id = record.detail_id.warehouse_id

                product_id = record.bom_line_id.product_id
                product_id = product_id.with_context(warehouse=warehouse_id.id, location=False)

                res = product_id._compute_quantities_dict(None, None, None)
                qty_available = res[product_id.id]['qty_available']
                incoming_qty = res[product_id.id]['incoming_qty']
                outgoing_qty = res[product_id.id]['outgoing_qty']
                virtual_available = res[product_id.id]['virtual_available']
                free_qty = res[product_id.id]['free_qty']
            
            record.qty_available = qty_available
            record.incoming_qty = incoming_qty
            record.outgoing_qty = outgoing_qty
            record.virtual_available = virtual_available
            record.free_qty = free_qty

    @api.depends('to_consume_qty', 'free_qty')
    def _compute_to_purchase(self):
        for record in self:
            record.to_purchase_qty = max([0.0, record.to_consume_qty - record.free_qty])

    @api.depends('bom_line_id', 'detail_id', 'detail_id.to_produce')
    def _compute_to_consume(self):
        for record in self:
            to_consume_qty = 0.0
            if record.bom_line_id and record.detail_id:
                to_consume_qty = (record.detail_id.to_produce / record.bom_line_id.bom_id.product_qty) * record.bom_line_id.product_qty
            record.to_consume_qty = to_consume_qty

    @api.depends('to_consume_qty', 'free_qty')
    def _compute_needs(self):
        for record in self:
            record.needs_qty = max([record.to_consume_qty - record.free_qty, 0.0])


    detail_id = fields.Many2one('mrp.mps.detail', string='MPS Detail', required=True, ondelete='cascade')
    bom_line_id = fields.Many2one('mrp.bom.line', string='BoM Line', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='detail_id.warehouse_id')

    qty_available = fields.Float(string='On Hand', digits='Product Unit of Measure', compute=_compute_quantities)
    incoming_qty = fields.Float(string='Forecasted Incoming', digits='Product Unit of Measure', compute=_compute_quantities)
    outgoing_qty = fields.Float(string='Forecasted Outgoing', digits='Product Unit of Measure', compute=_compute_quantities)
    virtual_available = fields.Float(string='Virtual Available', digits='Product Unit of Measure', compute=_compute_quantities)
    free_qty = fields.Float(string='Available', digits='Product Unit of Measure', compute=_compute_quantities)
    needs_qty = fields.Float(string='Forecasted Needs', digits='Product Unit of Measure', compute=_compute_needs)
    to_purchase_qty = fields.Float(string='To Purchase', digits='Product Unit of Measure', compute=_compute_to_purchase, store=True, readonly=False)

    product_id = fields.Many2one('product.product', string='Material', related='bom_line_id.product_id')
    to_consume_qty = fields.Float(string='To Consume', digits='Product Unit of Measure', compute=_compute_to_consume)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='bom_line_id.product_uom_id')
