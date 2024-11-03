from odoo import models, fields, api


class MrpWizLines(models.Model):
    _name = 'mrp.wiz.lines'
    _description = 'MRP Wiz Lines'

    move_id = fields.Many2one('stock.move', string='Stock Move')
    consumption_id = fields.Many2one('mrp.consumption', string='Production Record')
    point_id = fields.Many2one('sh.qc.point', string='Name')
    alert_id = fields.Many2one('sh.mrp.quality.alert', string='Quality Alert')
    point_number_of_test = fields.Integer(string='Max. Test')
    point_name = fields.Char(string='Reference')
    point_type = fields.Char(string='Point Type')
    pass_count = fields.Integer('Pass')
    fail_count = fields.Integer('Fail')
    pending_count = fields.Integer('Pending')
    state = fields.Char('State')
    product_id = fields.Many2one('product.product', string='Product')
    point_name = fields.Char(string='Point Name')
    product_type = fields.Char(string='Product Type')
    wiz_line_id = fields.Many2one('mrp.qc.wizard', string="Wiz Line")

class QuantitativeLines(models.Model):
    _name = 'wiz.manuf.qc.quantitative.lines'
    _description = 'Quantitative Lines'

    sequence = fields.Integer("No")
    dimansion_id = fields.Many2one('checksheet.dimensions', string="Dimensions")
    norm_qc = fields.Float(string="Norm")
    tolerance_from_qc = fields.Float(string="Tolerance From")
    tolerance_to_qc = fields.Float(string="Tolerance To")
    actual_value = fields.Float(string="Actual")
    text = fields.Char(string="Text")
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    wiz_line_id = fields.Many2one('mrp.qc.wizard', string="Wiz Line")
    is_result = fields.Boolean(string='Is Result', related='wiz_line_id.is_result')

class QuantitativeLines(models.Model):
    _name = 'wiz.manuf.qc.qualitative.lines'
    _description = 'Qualitative Lines'

    sequence = fields.Integer("No")
    item_id = fields.Many2one('qc.checksheet.items', string="Item")
    answer = fields.Many2one('qc.checksheet.answer', string="Answer", domain="[('item_id', '=', item_id)]")
    text = fields.Char(string="Text")
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    wiz_line_id = fields.Many2one('mrp.qc.wizard', string="Wiz Line")
    is_result = fields.Boolean(string='Is Result', related='wiz_line_id.is_result') 


class QuantitativeLines(models.Model):
    _name = 'qc.quantitative.lines'
    _description = 'Quantitative Lines'

    sequence = fields.Integer("No")
    dimansion_id = fields.Many2one('checksheet.dimensions', string="Dimensions")
    norm_qc = fields.Float(string="Norm")
    tolerance_from_qc = fields.Float(string="Tolerance From")
    tolerance_to_qc = fields.Float(string="Tolerance To")
    actual_value = fields.Float(string="Actual")
    text = fields.Char(string="Text")
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    quantitative_lines_ids = fields.Many2one('sh.quality.check', string="Check Line")

class QuantitativeLines(models.Model):
    _name = 'qc.qualitative.lines'
    _description = 'Qualitative Lines'

    sequence = fields.Integer("No")
    item_id = fields.Many2one('qc.checksheet.items', string="Item")
    answer = fields.Many2one('qc.checksheet.answer', string="Answer", domain="[('item_id', '=', item_id)]")
    text = fields.Char(string="Text")
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    qualitative_lines_ids = fields.Many2one('sh.quality.check', string="Check Line Quality")
    

class ShQualityCheck(models.Model):
    _inherit = 'sh.quality.check'

    type_of_qc = fields.Selection([('quantitative', 'Quantitative'), ('qualitative', 'Qualitative')], 'QC Type')
    checked_qty = fields.Float(string="Checked Qty")
    quantitative_line_ids = fields.One2many('qc.quantitative.lines', 'quantitative_lines_ids', string="Quantitative Lines")
    qualitative_line_ids = fields.One2many('qc.qualitative.lines', 'qualitative_lines_ids', string="Qualitative Lines")
    image_128 = fields.Image('Image', max_width=128, max_height=128)
    is_recheck = fields.Boolean(string='Is Recheck',compute='compute_is_recheck')
    remaining_qty = fields.Float(string='Remaining Qty')
    state = fields.Selection(selection_add=[('fail',),('repair', 'Under Repair'),('scrap','Under Scrap'),('transfer','Under ITR')])

    @api.depends('is_recheck')
    def compute_is_recheck(self):
        for rec in self:
            wizard_id = self.env['sh.stock.move.global.check'].sudo().search([
                ('picking_id', '=', rec.sh_picking.id),
                ('is_all_pass', '!=', True),
                ('quality_check_id','=', rec.id)
                ], limit=1, order='id desc')
            if wizard_id.recheck_max_number != 0:
                rec.is_recheck = True
            else:
                rec.is_recheck = False


    def recheck(self):
        is_recheck = False
        wizard_id = self.env['sh.stock.move.global.check'].sudo().search([
            ('picking_id', '=', self.sh_picking.id),
            ('is_all_pass', '!=', True),
            ('quality_check_id','=', self.id)
            ], limit=1, order='id desc')
        for qc in wizard_id.picking_id:
            for move in qc.move_ids_without_package:
                move_id = move.id
            for rec in qc.sh_quality_check_ids:
                if rec.id == self.id:
                    is_recheck = True
                    break
        ctx = {
            'default_id': wizard_id.id,
            'default_product_id': wizard_id.product_id.id,
            'default_image_128': wizard_id.image_128,
            'default_sh_message': wizard_id.sh_message,
            'default_sh_quality_point_id': wizard_id.sh_quality_point_id.id,
            'default_picking_id': wizard_id.picking_id.id,
            'default_quantitative_line_ids': wizard_id.quantitative_line_ids.ids,
            'default_qualitative_line_ids': wizard_id.qualitative_line_ids.ids,
            'default_move_id': move_id,
            'default_is_result': wizard_id.is_result,
            'default_is_all_pass': wizard_id.is_all_pass,
            'default_is_result': wizard_id.is_result,
            'default_is_recheck': wizard_id.is_recheck,
            'default_recheck_max_number': wizard_id.recheck_max_number,
            'default_is_from_recheck_line': True,
            'default_quality_check_id': wizard_id.quality_check_id.id,
            'default_recheck_line': True,
        }
        if is_recheck:
            return {
                'name': 'Self Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.stock.move.global.check',
                'context': ctx,
                'target': 'new',
            }
