from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import Warning, ValidationError

class InternalTransferWizard(models.TransientModel):
    _name = 'mr.internal_transfer'
    _description = 'MR Internal Transfer'

    source_warehouse_id = fields.Many2one('stock.warehouse', 'Source Warehouse')
    ir_wizard_line = fields.One2many('mr.internal_transfer_line', 'mr_ir_wizard')

    def create_ir(self):
        mr_id = self.ir_wizard_line[0].mr_id
        # mr_id._check_processed_record(mr_id.id)
        self.ir_wizard_line[0].mr_id._check_processed_record(self.ir_wizard_line[0].mr_id.id)
        source_warehouse = []
        for line in self.ir_wizard_line:
            if line.source_warehouse_id.id not in source_warehouse:
                source_warehouse.append(line.source_warehouse_id.id)
            if not line.source_warehouse_id.id:
                raise ValidationError("Please Add Warehouse For Internal Transfer")
            # quantity = line.qty_transfer + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
            # if quantity > line.mr_line_id.quantity:
            #     raise ValidationError(_('You cannot create a ITR for %s with more quantity then you Requested.') %
            #     (line.product_id.name))
        ir_id_list = []
        for loc in source_warehouse:
            ir_line = []
            source_location_id = self.env['stock.location'].search([('warehouse_id', '=', loc), ('usage', '=', 'internal')], limit=1, order="id")
            # mr_id = self.ir_wizard_line.mapped('mr_id')
            destination_location_id = self.env['stock.location'].search([('warehouse_id', '=', mr_id.destination_warehouse_id.id), ('usage', '=', 'internal')], limit=1, order="id")
            for line in self.ir_wizard_line:
                if loc == line.source_warehouse_id.id:
                    # if line.qty_transfer > line.current_qty:
                    #     raise ValidationError('Quantity to transfer can’t exceed the current quantity in source location')
                    vals = {
                        'product_id' : line.product_id.id,
                        'uom' : line.uom_id.id,
                        'qty' : line.qty_transfer,
                        'scheduled_date' : self.ir_wizard_line.mr_id.schedule_date,
                        'destination_location_id': destination_location_id.id,
                        'source_location_id': source_location_id.id,
                        'description': line.description or line.product_id.display_name,
                        'source_document': self.ir_wizard_line.mr_id.name,
                        'requested_by': self.ir_wizard_line.mr_id.requested_by.id,
                        'company_id': self.ir_wizard_line.mr_id.company_id.id,
                        'mr_line_id': line.mr_line_id.id
                    }
                    ir_line.append((0,0, vals))


            #compute eexpiry date
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            itr_expiry_days = IrConfigParam.get_param('mr_expiry_days', 'before')
            itr_ex_period = IrConfigParam.get_param('ex_period', 0)
            # if self.scheduled_date:
            if itr_expiry_days == 'before':
                expiry_date = self.ir_wizard_line.mr_id.schedule_date - timedelta(days=int(itr_ex_period))
            else:
                expiry_date = self.ir_wizard_line.mr_id.schedule_date + timedelta(days=int(itr_ex_period))
            ir_line_id = self.env['internal.transfer'].create({'product_line_ids': ir_line,
                                                        # 'mr_id': self.ir_wizard_line.mr_id.id,
                                                        'source_document': self.ir_wizard_line.mr_id.name,
                                                        'scheduled_date': self.ir_wizard_line.mr_id.schedule_date,
                                                        'expiry_date': expiry_date,
                                                        'source_location_id': source_location_id.id,
                                                        'analytic_account_group_ids': [(6, 0, self.ir_wizard_line.mr_id.analytic_account_group_ids.ids)],
                                                        'destination_location_id': destination_location_id.id,
                                                        'source_warehouse_id' : loc,
                                                        'destination_warehouse_id': self.ir_wizard_line.mr_id.destination_warehouse_id.id
                                                        })
            ir_line_id.write({'mr_id': [(4, self.ir_wizard_line.mr_id.id)], 
                              'branch_id': self.ir_wizard_line.mr_id.branch_id.id})
            ir_id_list.append(ir_line_id)
            ir_line_id.onchange_source_loction_id()
            ir_line_id.onchange_dest_loction_id()


        # print('iel', ir_line_id)
        # for line in ir_id_list:
        #     for ir_line in line.product_line_ids:
        #         mr_lines_id = self.env['material.request.line'].search([('material_request_id','=',self.ir_wizard_line.mr_id.id),('product', '=', ir_line.product_id.id)])
        #         if mr_lines_id:
        #             mr_lines_id.write({'ir_lines_ids': [(4, ir_line.id)]})

        return ir_id_list




class InternalTransferWizardLine(models.TransientModel):
    _name = 'mr.internal_transfer_line'
    _description = 'MR Internal Transfer Line'

    @api.model
    def default_get(self, fields):
        res = super(InternalTransferWizardLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'ir_wizard_line' in context_keys:
                if len(self._context.get('ir_wizard_line')) > 0:
                    next_sequence = len(self._context.get('ir_wizard_line')) + 1
            res.update({'no': next_sequence})
        return res
    
    @api.model
    def _get_source_warehouse_domain(self):
        return [('branch_id', 'in', self.env.branches.ids)]

    mr_id = fields.Many2one('material.request', 'Material Request')
    no = fields.Integer('No', readonly='1')
    product_id = fields.Many2one('product.product', 'Product')
    description = fields.Char()
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    source_location = fields.Many2one('stock.location', 'Source Location')
    source_warehouse_id = fields.Many2one('stock.warehouse', 'Source Warehouse', domain=_get_source_warehouse_domain)
    current_qty = fields.Float('Available Quantity')
    virtual_available = fields.Float('Forecasted Quantity', readonly='1')
    qty_transfer = fields.Float('Quantity To Transfer', required='1')
    mr_ir_wizard = fields.Many2one('mr.internal_transfer')
    mr_line_id = fields.Many2one('material.request.line')
    filter_warehouse_ids = fields.Many2many('stock.warehouse', compute='_get_locations', store=False)
    filter_location_ids = fields.Many2many('stock.location', compute='_get_locations', store=False)
    dest_warehouse_id = fields.Many2one(related='mr_id.destination_warehouse_id')

    @api.onchange('source_warehouse_id')
    def _onchange_warehouse_id(self):
        if self.source_warehouse_id and self.mr_id.destination_warehouse_id.id == self.source_warehouse_id.id:
            warning_mess = {
                'title': _('Same Warehouse!'),
                'message' : _('You have selected the same warehouse for source warehouse in internal transfer request as destination warehouse in material request.'),
            }
            return {'warning': warning_mess, 'value' : {'source_warehouse_id': self.source_warehouse_id.id}}

    @api.depends('current_qty')
    def _get_locations(self):
        for record in self:
            data_ids = []
            location_ids = []
            stock_quant = record.env['stock.quant'].search([('product_id','=', record.product_id.id)])
            for quant in stock_quant:
                if quant.available_quantity > 0:
                    if quant.location_id.usage == 'internal':
                        if quant.location_id.id != record.mr_id.destination_location_id.id:
                            warehouse_id = quant.location_id.get_warehouse().id
                            if warehouse_id:
                                data_ids.append(warehouse_id)
                            location_ids.append(quant.location_id.id)
            record.filter_warehouse_ids = [(6, 0, data_ids)]
            record.filter_location_ids = [(6, 0, location_ids)]

    @api.onchange('source_warehouse_id')
    def calculate_current_qty(self):
        for record in self:
            location_ids = record.filter_location_ids.ids
            stock_quant_ids = self.env['stock.quant'].search([('location_id', 'in', location_ids), ('product_id', '=', record.product_id.id)])
            avl_qty = sum(stock_quant_ids.mapped('available_quantity'))
            stock_moves_in = self.env['stock.move'].search([('product_id', '=', record.product_id.id), ('location_dest_id', 'in', location_ids), ('state','in', ['done', 'assigned'])])
            stock_moves_out = self.env['stock.move'].search([('product_id', '=', record.product_id.id), ('location_id', 'in', location_ids), ('state','in', ['done', 'assigned'])])
            forecast_qty = sum(stock_moves_in.mapped('product_uom_qty')) - sum(stock_moves_out.mapped('product_uom_qty')) + avl_qty
            record.virtual_available = forecast_qty
            record.current_qty = avl_qty


class ITRWizard(models.TransientModel):
    _name = 'mr_line.internal_transfer'
    _description = 'MR Line Internal Transfer'

    def _default_ir_wizard_line(self):
        mr_lines_id = self.env['material.request.line'].browse(self._context.get('active_ids'))
        ir_line = []
        count = 1
        error_lines = []
        counter = 1
        message = ''
        for line in mr_lines_id:
            if line.status != 'confirm':
                if line.status == 'draft':
                    message = "- Product %s in Material Request %s  must be confirmed to create Internal Transfer Request" % (line.product.name, line.material_request_id.name)
                    error_lines.append(message)
                if line.status == 'done':
                    message = "- Product %s in Material Request %s  request was done" % (line.product.name, line.material_request_id.name)
                    error_lines.append(message)
            qty = line.quantity - line.done_qty
            if qty < 0:
                qty = 0
            ir_line.append((0, 0, {
                'no': count,
                'mr_id': line.material_request_id.id,
                'product_id' : line.product.id,
                'description' : line.product.description,
                'uom_id' : line.product.uom_id.id,
                'qty_transfer' : qty,
                'mr_line_id': line.id,
            }))
            count = count+1
        if error_lines:
            raise ValidationError("%s" % ('\n'.join(error_lines)))
        return ir_line

    ir_wizard_line = fields.One2many('mr_line.internal_transfer_line', 'mr_ir_wizard', default=_default_ir_wizard_line)

    def create_ir(self):
        dest_loc = []
        for line in self.ir_wizard_line:
            if line.mr_id.destination_warehouse_id not in dest_loc:
                dest_loc.append(line.mr_id.destination_warehouse_id)
            quantity = line.qty_transfer + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
            if quantity > line.mr_line_id.quantity:
                raise ValidationError(_('You cannot create a ITR for %s with more quantity then you Requested.') %
                (line.product_id.name))
        ir_id_list = []
        for loc in dest_loc:
            source_loc = []
            for line in self.ir_wizard_line:
                if loc.id == line.mr_id.destination_warehouse_id.id:
                    if line.source_warehouse_id not in source_loc:
                        source_loc.append(line.source_warehouse_id)
            for sloc in source_loc:
                ir_line = []
                mr_list = []
                origin = []
                material_request_id = False
                for line in self.ir_wizard_line:
                    if loc.id == line.mr_id.destination_warehouse_id.id:
                        if sloc.id == line.source_warehouse_id.id:
                            vals = {
                                'product_id' : line.product_id.id,
                                'uom' : line.uom_id.id,
                                'qty' : line.qty_transfer,
                                'scheduled_date' : line.mr_id.schedule_date,
                                'destination_location_id': line.mr_id.destination_location_id.id,
                                'source_location_id': line.source_location.id,
                                'description': line.description or line.product_id.display_name,
                                'source_document': line.mr_id.name,
                                'requested_by': line.mr_id.requested_by.id,
                                'company_id': line.mr_id.company_id.id,
                                'mr_line_id': line.mr_line_id.id,
                            }
                            ir_line.append((0,0, vals))
                            material_request_id = line.mr_id
                            mr_list.append(line.mr_id.id)
                            if line.mr_id.name not in origin:
                                origin.append(line.mr_id.name)
                            warehouse_id = line.mr_id.destination_warehouse_id
                            warehouse_id_source = self.env['stock.warehouse'].search([('lot_stock_id','=',line.source_location.id)])

                #compute eexpiry date
                IrConfigParam = self.env['ir.config_parameter'].sudo()
                itr_expiry_days = IrConfigParam.get_param('mr_expiry_days', 'before')
                itr_ex_period = IrConfigParam.get_param('ex_period', 0)
                # if self.scheduled_date:
                material_request_id = self.ir_wizard_line.filtered(lambda r:r.source_warehouse_id.id == sloc.id).mapped('mr_id')
                if material_request_id:
                    material_request_id = material_request_id[0]
                if itr_expiry_days == 'before':
                    expiry_date = material_request_id.schedule_date - timedelta(days=int(itr_ex_period))
                else:
                    expiry_date = material_request_id.schedule_date + timedelta(days=int(itr_ex_period))
                source_loc_id = self.env['stock.location'].search([("warehouse_id", '=', sloc.id), ('usage', '=', 'internal')], limit=1, order='id')
                dest_loc_id = self.env['stock.location'].search([("warehouse_id", '=', loc.id), ('usage', '=', 'internal')], limit=1, order='id')
                ir_line_id = self.env['internal.transfer'].create({'product_line_ids': ir_line,
                                                                   # 'mr_id': material_request_id.id,
                                                                   'source_document': ','.join(origin),
                                                                   'scheduled_date': material_request_id.schedule_date,
                                                                   'expiry_date': expiry_date,
                                                                   'source_warehouse_id' : sloc.id,
                                                                   'destination_warehouse_id': loc.id,
                                                                   'source_location_id': source_loc_id.id,
                                                                   'destination_location_id': dest_loc_id.id
                                                                   })
                ir_line_id._onchange_warehouse_id_for_location()
                ir_line_id.onchange_source_loction_id()
                ir_line_id.onchange_dest_loction_id()
                ir_line_id.write({
                    'mr_id': [(6, False, mr_list)]
                })
                count = 1
                ir_id_list.append(ir_line_id)
                for ir in ir_line_id.product_line_ids:
                    ir.write({
                        'sequence': count,
                        'source_location_id': source_loc_id.id,
                        'destination_location_id': dest_loc_id.id
                    })
                    count += 1
                    mr_lines_id = self.env['material.request.line'].search([('id','=',ir.mr_line_id.id),('product','=', ir.product_id.id)])
                    for rec in mr_lines_id:
                        rec.write({'ir_lines_ids': [(4, ir.id)]})
        return


class ITRWizardLine(models.TransientModel):
    _name = 'mr_line.internal_transfer_line'
    _description = 'MR Line Internal Transfer'

    @api.model
    def default_get(self, fields):
        res = super(ITRWizardLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'ir_wizard_line' in context_keys:
                if len(self._context.get('ir_wizard_line')) > 0:
                    next_sequence = len(self._context.get('ir_wizard_line')) + 1
            res.update({'no': next_sequence})
        return res

    mr_id = fields.Many2one('material.request', 'Reference')
    mr_line_id = fields.Many2one('material.request.line')
    no = fields.Integer('No', readonly='1')
    product_id = fields.Many2one('product.product', 'Product')
    description = fields.Char()
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    source_location = fields.Many2one('stock.location', 'Source Location')
    source_warehouse_id = fields.Many2one('stock.warehouse', 'Source Warehouse')
    current_qty = fields.Float('Available Quantity')
    virtual_available = fields.Float('Forecasted Quantity', readonly='1')
    qty_transfer = fields.Float('Quantity To Transfer', required='1')
    mr_ir_wizard = fields.Many2one('mr_line.internal_transfer')
    filter_warehouse_ids = fields.Many2many('stock.warehouse', compute='_get_locations', store=False)
    filter_location_ids = fields.Many2many('stock.location', compute='_get_locations', store=False)
    dest_warehouse_id = fields.Many2one(related='mr_id.destination_warehouse_id')

    @api.onchange('source_warehouse_id')
    def _onchange_warehouse_id(self):
        if self.source_warehouse_id and self.mr_id.destination_warehouse_id.id == self.source_warehouse_id.id:
            warning_mess = {
                'title': _('Same Warehouse!'),
                'message' : _('You have selected the same warehouse for source warehouse in internal transfer request as destination warehouse in material request.'),
            }
            return {'warning': warning_mess, 'value' : {'source_warehouse_id': self.source_warehouse_id.id}}

    @api.depends('current_qty')
    def _get_locations(self):
        for record in self:
            data_ids = []
            location_ids = []
            stock_quant = record.env['stock.quant'].search([('product_id','=', record.product_id.id)])
            if stock_quant:
                for quant in stock_quant:
                    if quant.available_quantity > 0 and \
                        quant.location_id.usage == 'internal' and \
                        quant.location_id.id != record.mr_id.destination_location_id.id:
                        warehouse_id = quant.location_id.get_warehouse().id
                        if warehouse_id and warehouse_id not in data_ids:
                            data_ids.append(warehouse_id)
                        location_ids.append(quant.location_id.id)
            record.filter_warehouse_ids = [(6, 0, data_ids)]
            record.filter_location_ids = [(6, 0, location_ids)]

    @api.onchange('source_warehouse_id')
    def calculate_current_qty(self):
        for record in self:
            location_ids = record.filter_location_ids.ids
            stock_quant_ids = self.env['stock.quant'].search([('location_id', 'in', location_ids), ('product_id', '=', record.product_id.id)])
            avl_qty = sum(stock_quant_ids.mapped('available_quantity'))
            stock_moves_in = self.env['stock.move'].search([('product_id', '=', record.product_id.id), ('location_dest_id', 'in', location_ids), ('state','in', ['done', 'assigned'])])
            stock_moves_out = self.env['stock.move'].search([('product_id', '=', record.product_id.id), ('location_id', 'in', location_ids), ('state','in', ['done', 'assigned'])])
            forecast_qty = sum(stock_moves_in.mapped('product_uom_qty')) - sum(stock_moves_out.mapped('product_uom_qty')) + avl_qty
            record.virtual_available = forecast_qty
            record.current_qty = avl_qty

