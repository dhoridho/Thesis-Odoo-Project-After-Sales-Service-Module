from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShMrpQcWizard(models.Model):
    _name = 'sh.mrp.qc.wizard'
    _description = 'Quality Check Wizard'

    def _compute_state(self):
        for record in self:
            quantitative_pass = all(q.status == 'pass' for q in record.quantitative_ids)
            qualitative_pass = all(q.status == 'pass' for q in record.qualitative_ids)
            if record.type_of_qc == 'quantitative':
                is_pass = quantitative_pass
            elif record.type_of_qc == 'qualitative':
                is_pass = qualitative_pass
            else:
                is_pass = quantitative_pass and qualitative_pass
            record.state = is_pass and 'pass' or 'fail'

    res_model = fields.Char(string='Model', required=True)
    res_id = fields.Integer(string='Record', required=True)
    move_point_id = fields.Many2one('sh.qc.move.point', string='Pair', required=True)
    remaining_check = fields.Integer(related='move_point_id.remaining_check')

    move_id = fields.Many2one('stock.move', string='Move', required=True)
    product_id = fields.Many2one('product.product', related='move_id.product_id', string='Product')
    product_image = fields.Image(related='product_id.image_1920')

    point_id = fields.Many2one('sh.qc.point', string='Quality Point', required=True)
    type_of_qc = fields.Selection(related='point_id.type_of_qc')

    quantitative_ids = fields.One2many('sh.mrp.qc.wizard.quantitative', 'wizard_id', string='Quantitatives')
    qualitative_ids = fields.One2many('sh.mrp.qc.wizard.qualitative', 'wizard_id', string='Qualitatives')

    check_id = fields.Many2one('sh.mrp.quality.check', string='Quality Check')
    state = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')], string='Status', compute=_compute_state)

    @api.onchange('point_id')
    def _onchange_quality_point(self):
        if not self.point_id:
            return

        if self.point_id.type_of_qc in ('both', 'quantitative'):
            self.quantitative_ids = [(0, 0, {
                'quantitative_id': q.id
            }) for q in self.point_id.quantitative_ids]

        if self.point_id.type_of_qc in ('both', 'qualitative'):
            self.qualitative_ids = [(0, 0, {
                'qualitative_id': q.id
            }) for q in self.point_id.qualitative_ids]

    def action_confirm(self):
        self.ensure_one()

        context = self.env.context
        if not context.get('from_recheck_line'):
            
            if self.remaining_check <= 0:
                return

            quantitative_ids = []
            for line in self.quantitative_ids:
                quantitative_ids.append((0 ,0, {
                    'sequence': line.sequence,
                    'dimansion_id': line.dimansion_id.id,
                    'norm_qc': line.norm_qc,
                    'tolerance_from_qc': line.tolerance_from_qc,
                    'tolerance_to_qc': line.tolerance_to_qc,
                    'actual_value': line.actual_value,
                    'text': line.text,
                    'status': line.status,
                }))

            qualitative_ids = []
            for line in self.qualitative_ids:
                qualitative_ids.append((0 ,0, {
                    'sequence': line.sequence,
                    'item_id': line.item_id.id,
                    'answer': line.answer.id,
                    'text': line.text,
                    'status': line.status,
                }))

            record_id = self.env[self.res_model].browse(self.res_id)
            check_values = {
                record_id.qc_check_field_name() : self.res_id,
                'product_id' : self.product_id.id,
                'sh_date': fields.Date.today(),
                'move_id': self.move_id.id,
                'control_point_id': self.point_id.id,
                'state': self.state,
                'quantitative_ids': quantitative_ids if self.type_of_qc in ('quantitative', 'both') else False,
                'qualitative_ids': qualitative_ids if self.type_of_qc in ('qualitative', 'both') else False
            }
            
            self.check_id = self.env['sh.mrp.quality.check'].create(check_values)
            self.move_point_id.remaining_check -= 1

            return {
                'name': 'Quality Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('equip3_manuf_qc.view_sh_mrp_qc_wizard_form_confirmed').id,
                'res_model': 'sh.mrp.qc.wizard',
                'res_id': self.id,
                'target': 'new',
            }

        else:
            wizard_id = self.env['sh.mrp.qc.wizard'].sudo().search([
                ('move_id', '=', self.move_id.id),
                ('check_id','=', self.check_id.id)
            ])

            status = 'pass' if self.state == 'pass' else 'fail'

            if self.quantitative_ids:
                for line in self.quantitative_ids:
                    for x in self.check_id.quantitative_ids:
                        x.status = status
                        x.actual_value = line.actual_value
            
            if self.qualitative_ids:
                for line in self.qualitative_ids:
                    for x in self.check_id.qualitative_ids:
                        x.status = status
                        x.answer = line.answer
                        
            self.check_id.state = status

            return {
                'name': 'Quality Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('equip3_manuf_qc.view_sh_mrp_qc_wizard_form_confirmed').id,
                'res_model': 'sh.mrp.qc.wizard',
                'res_id': wizard_id.id,
                'target': 'new',
            }



    def action_recheck(self):
        self.ensure_one()
        self.move_point_id.remaining_check -= 1
        return {
            'name': 'Quality Check',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_manuf_qc.view_sh_mrp_qc_wizard_form').id,
            'res_model': 'sh.mrp.qc.wizard',
            'res_id': self.id,
            'target': 'new',
        }

    def action_scrap(self):
        self.ensure_one()
        scrap_obj = self.env['stock.scrap'].search([
            ('mrp_quality_check_id', '=', self.check_id.id)
        ], limit=1)
        if scrap_obj:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Stock Scrap',
                'res_model': 'stock.scrap',
                'res_id': scrap_obj.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            stock_scrap_location = self.env['stock.scrap']._get_default_scrap_location_id()
            ctx = {
                'default_product_id': self.product_id.id,
                'default_scrap_qty': 1.0,
                'default_product_uom_id': self.product_id.uom_id.id,
                'default_location_id': self.move_id.location_dest_id.id,
                'default_scrap_location_id': stock_scrap_location,
                'default_mrp_quality_check_id': self.check_id.id,
            }
            
            return {
                'type': 'ir.actions.act_window',
                'name': 'Stock Scrap',
                'res_model': 'stock.scrap',
                'view_type': 'form',
                'view_mode': 'form',
                'context': ctx,
                'target': 'new',
            }

    def action_repair(self):
        self.ensure_one()
        repair_obj = self.env['repair.order'].search([
            ('mrp_quality_check_id', '=', self.check_id.id)
        ], limit=1)
        if repair_obj:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Repair Order',
                'res_model': 'repair.order',
                'res_id': repair_obj.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            ctx = {
                'default_mrp_quality_check_id': self.check_id.id,
                'default_product_id': self.product_id.id,
                'default_product_qty': 1.0,
                'default_location_id': self.move_id.location_dest_id.id,
                'default_repair_type': 'internal_repair'
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Repair Order',
                'res_model': 'repair.order',
                'view_type': 'form',
                'view_mode': 'form',
                'context': ctx,
                'target': 'new',
            }

    def action_transfer(self):
        self.ensure_one()
        itr_obj = self.env['internal.transfer'].search([
            ('mrp_quality_check_id', '=', self.check_id.id)
        ], limit=1)
        if itr_obj:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Internal Transfer',
                'res_model': 'internal.transfer',
                'res_id': itr_obj.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            location_id = self.move_id.location_dest_id
            warehouse_id = location_id.get_warehouse()
            ctx = {
                'default_mrp_quality_check_id': self.check_id.id,
                'default_product_id': self.product_id.id,
                'default_scheduled_date': fields.Datetime.now(),
                'default_product_qty': 1.0,
                'default_destination_warehouse_id': warehouse_id.id,
                'default_destination_location_id': location_id.id,
                'default_product_line_ids': [(0, 0, {
                    'product_id': self.product_id.id,
                    'description': self.product_id.name,
                    'uom': self.product_id.uom_id.id,
                    'qty': 1.0,
                    'scheduled_date': fields.Datetime.now(),
                })]
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Internal Transfer',
                'res_model': 'internal.transfer',
                'view_type': 'form',
                'view_mode': 'form',
                'context': ctx,
                'target': 'new',
            }

    def action_next_check(self):
        self.ensure_one()
        self.move_point_id.remaining_check = 0
        return self.env[self.res_model].browse(self.res_id).button_quality_check()


class ShMrpQcWizardQuantitative(models.TransientModel):
    _name = 'sh.mrp.qc.wizard.quantitative'
    _description = 'Quality Check Wizard Quantitative'

    @api.depends('tolerance_from_qc', 'actual_value', 'tolerance_to_qc')
    def _compute_status(self):
        for record in self:
            record.status = 'pass' if record.tolerance_from_qc <= record.actual_value <= record.tolerance_to_qc else 'fail'

    wizard_id = fields.Many2one('sh.mrp.qc.wizard', string='Wizard', required=True, ondelete='cascade')
    quantitative_id = fields.Many2one('qp.quantitative.lines', string='Quantitative', required=True)
    sequence = fields.Integer(related='quantitative_id.sequence')
    dimansion_id = fields.Many2one(related='quantitative_id.dimansion_id')
    norm_qc = fields.Float(related='quantitative_id.norm_qc')
    tolerance_from_qc = fields.Float(related='quantitative_id.tolerance_from_qc')
    tolerance_to_qc = fields.Float(related='quantitative_id.tolerance_to_qc')

    actual_value = fields.Float(string='Actual')
    text = fields.Char(string='Text')
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')], string='Status', compute=_compute_status)


class ShMrpQcWizardQualitative(models.TransientModel):
    _name = 'sh.mrp.qc.wizard.qualitative'
    _description = 'Quality Check Wizard Qualitative'

    @api.depends('answer')
    def _compute_status(self):
        for record in self:
            record.status = 'pass' if record.answer.is_answer else 'fail'

    wizard_id = fields.Many2one('sh.mrp.qc.wizard', string='Wizard', required=True, ondelete='cascade')
    qualitative_id = fields.Many2one('qp.qualitative.lines', string='Qualitative', required=True)
    sequence = fields.Integer(related='qualitative_id.sequence')
    item_id = fields.Many2one(related='qualitative_id.item_id')

    answer = fields.Many2one('qc.checksheet.answer', string="Answer", domain="[('item_id', '=', item_id)]")
    text = fields.Char(string='Text')
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')], string='Status', compute=_compute_status)
