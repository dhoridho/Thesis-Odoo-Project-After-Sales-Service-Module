
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sh_quality_check_ids = fields.One2many(
        'sh.quality.check', 'sh_picking', string="Quality Checks")
    is_all_qc_with_remaining_qty = fields.Boolean(
        string="Is All Qc Pass/Fail", compute='_compute_qc_line')
    is_all_checked = fields.Boolean(
        string="Is All Checked", compute='_compute_is_all_checked', store=False)
    is_status_fail_or_pass = fields.Boolean(
        string="Is Status Fail Or Pass", compute='_compute_is_all_checked')
    is_only_read_qc = fields.Boolean(string="Is Only Read QC", compute='_is_only_read_qc',
                                     help="Check is user have permission to read QC or not")

    filter_qc = fields.Boolean(
        string="Filter QC", compute='_compute_is_under_progress', default=False)
    is_pending_qc = fields.Boolean(string="Is Pending QC", compute='_compute_is_under_progress', store=False)
    is_under_progress = fields.Boolean(string="Is Under Progress", compute='_compute_is_under_progress', store=False)
    is_qc_fail = fields.Boolean(string="Is QC Fail", compute='_compute_is_under_progress', store=False)
    is_qc_pass = fields.Boolean(string="Is QC Pass", compute='_compute_is_under_progress', store=False)
    need_qc_and_under_progress = fields.Boolean(
        string="Need QC and Under Progress", compute='_compute_is_under_progress', store=False)
    qc_status = fields.Selection(string='QC Status', selection=[('pending', 'Pending QC'), (
        'failed', 'Failed QC'), ('progress', 'Under Progress QC'), ('passed', 'Passed QC')], compute='_compute_is_under_progress', store=False)
    picking_grade_id = fields.Many2one('stock.picking', string="Picking Grade")
    is_quality_point_grade = fields.Boolean(
        string="Is Quality Point Grade", compute='_compute_is_quality_point_grade')

    def _is_invisible_button_serialize(self):
        return super(StockPicking, self)._is_invisible_button_serialize() or self.is_all_qc_with_remaining_qty

    def _get_qc_point(self, product_ids, operation_id, is_mandatory=None, is_product_grade=None, team=None):

        self.ensure_one()
        domain = [('product_ids', 'in', product_ids), ('operation_ids', '=', operation_id)]

        if is_mandatory:
            domain.extend([('is_mandatory', '=', is_mandatory)])
        if is_product_grade:
            domain.extend([('is_product_grade', '=', is_product_grade)])
        if team:
            domain.extend(['|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '!=', False)])
        else:
            domain.extend(['|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)])

        return self.env['sh.qc.point'].sudo().search(domain, limit=1, order='create_date desc')


    @api.depends('move_ids_without_package')
    def _compute_is_quality_point_grade(self):
        for picking in self:
            picking.is_quality_point_grade = False
            product_ids = picking.move_ids_without_package.mapped('product_id.id')

            quality_point_id = self._get_qc_point(
                    product_ids=product_ids,
                    operation_id=picking.picking_type_id.id,
                    is_product_grade=True,
                    team=False
                    )
            if quality_point_id:
                picking.is_quality_point_grade = True

    @api.depends('move_ids_without_package.product_id', 'picking_type_id')
    def _check_need_qc(self):

        for record in self:
            record.qc_pass = False
            record.qc_fail = False
            record.need_qc = False
            record.full_pass = False


            if not record.move_ids_without_package:
                continue

            product_ids = record.move_ids_without_package.mapped('product_id.id')

            quality_point_id = self._get_qc_point(
                product_ids=product_ids,
                operation_id=record.picking_type_id.id,
                team=False
            )

            quality_point_id_not_in_team = self._get_qc_point(
                product_ids=product_ids,
                operation_id=record.picking_type_id.id,
                is_mandatory=True,
                team=True
            )

            if quality_point_id or quality_point_id_not_in_team:
                record.need_qc = True

                qc_fail = any(move.sh_last_qc_state == 'fail' for move in record.move_ids_without_package)
                qc_pass = not qc_fail and any(move.sh_last_qc_state == 'pass' for move in record.move_ids_without_package)

                record.qc_fail = qc_fail
                record.qc_pass = qc_pass

                if not qc_fail and record.sh_quality_check_ids.filtered(lambda x: x.sh_picking.id == record.id and x.state == 'pass'):
                    full_pass = all(
                        self.env['sh.quality.check'].sudo().search([
                            ('product_id', '=', move.product_id.id),
                            ('sh_picking', '=', record.id)
                        ], order='id desc', limit=1).state == 'pass'
                        for move in record.move_ids_without_package
                    )

                    if full_pass:
                        record.full_pass = True
                        record.qc_fail = False
                        record.qc_pass = False

            if not record.need_qc:
                record.qc_pass = True

    @api.depends('sh_quality_check_ids')
    def _compute_is_under_progress(self):
        """Compute if quality check is under progress or not."""
        for picking in self:
            picking.update({
                'filter_qc': False,
                'is_pending_qc': False,
                'is_under_progress': False,
                'is_qc_fail': False,
                'is_qc_pass': False,
                'need_qc_and_under_progress': False,
                'qc_status': False
            })

            move_product_ids = picking.move_ids_without_package.mapped('product_id.id')
            picking_type_id = picking.picking_type_id.id

            if not move_product_ids or not picking_type_id:
                continue

            quality_point_id = self._get_qc_point(
                product_ids=move_product_ids,
                operation_id=picking_type_id,
                team=False
            )

            quality_point_id_not_in_team = self._get_qc_point(
                product_ids=move_product_ids,
                operation_id=picking_type_id,
                is_mandatory=True,
                team=True
            )

            if not picking.picking_grade_id and (quality_point_id or quality_point_id_not_in_team):
                picking.update({
                    'filter_qc': True,
                    'is_pending_qc': True,
                    'qc_status': 'pending'
                })

            if picking.sh_quality_check_ids:
                remaining = sum(picking.sh_quality_check_ids.mapped('remaining_qty'))
                qc_states = picking.sh_quality_check_ids.mapped('state')

                if remaining == 0:
                    if 'fail' in qc_states or 'repair' in qc_states or 'transfer' in qc_states:
                        picking.update({
                            'is_under_progress': False,
                            'is_pending_qc': False,
                            'is_qc_fail': True,
                            'qc_status': 'failed'
                        })
                    elif 'pass' in qc_states:
                        picking.update({
                            'is_under_progress': False,
                            'is_pending_qc': False,
                            'is_qc_pass': True,
                            'qc_status': 'passed'
                        })
                else:
                    picking.update({
                        'is_under_progress': True,
                        'is_pending_qc': False,
                        'qc_status': 'progress'
                    })

            picking.need_qc_and_under_progress = picking.is_pending_qc or picking.is_under_progress


    @api.depends('move_ids_without_package', 'move_ids_without_package.remaining_checked_qty', 'move_ids_without_package.sh_quality_point')
    def _compute_qc_line(self):
        for record in self:
            filter_line = record.move_ids_without_package.filtered(
                lambda l: l.sh_quality_point)
            if any(line.remaining_checked_qty > 0 for line in filter_line):
                record.is_all_qc_with_remaining_qty = True
            else:
                record.is_all_qc_with_remaining_qty = False

    @api.depends('sh_quality_check_ids', 'sh_quality_check_ids.remaining_qty', 'sh_quality_check_ids.state')
    def _compute_is_all_checked(self):
        status_list = []
        for qc_lines in self.sh_quality_check_ids:
            if qc_lines.remaining_qty == 0:
                self.is_all_checked = True
            elif qc_lines.remaining_qty < 0:
                qc_lines.remaining_qty = 0
            else:
                self.is_all_checked = False
            status_list.append(qc_lines.state)
        if 'fail' not in status_list:
            self.is_status_fail_or_pass = True
        else:
            self.is_status_fail_or_pass = False

        for rec in self:
            if rec.is_all_checked:
                alerts = self.env['sh.quality.alert'].search(
                    [('piking_id', '=', rec.id)])
                if alerts:
                    for alert in alerts:
                        alert.stage_id = 3

    def _is_only_read_qc(self):
        if self:
            for picking in self:
                picking.is_only_read_qc = False
                if picking.move_ids_without_package:

                    product_ids = picking.move_ids_without_package.mapped('product_id.id')
                    quality_point_id = self._get_qc_point(
                            product_ids=product_ids,
                            operation_id=picking.picking_type_id.id,
                            is_mandatory=True,
                            team=True
                        )

                    if quality_point_id:
                        if self.env.uid not in quality_point_id.team.user_ids.ids:
                            picking.is_only_read_qc = True


    def _check_qc_mandatory(self):
        if self:
            for record in self:
                record.is_mandatory = False

                product_ids = record.move_ids_without_package.mapped('product_id.id')
                quality_point_id = self._get_qc_point(
                        product_ids=product_ids,
                        operation_id=record.picking_type_id.id,
                        team=False
                )

                quality_point_id_not_in_team = self._get_qc_point(
                    product_ids=product_ids,
                    operation_id=record.picking_type_id.id,
                    is_mandatory=True,
                    team=True
                )

                if quality_point_id.is_mandatory or quality_point_id_not_in_team.is_mandatory:
                    record.is_mandatory = True

    def quality_point(self):
        self.ensure_one()

        if self and self.move_ids_without_package:
            need_qc = False
            line_id = False

            product_ids = self.move_ids_without_package.mapped('product_id.id')
            picking_type_id = self.picking_type_id.id

            # Cache the quality point
            quality_point_id = self._get_qc_point(
                product_ids=product_ids,
                operation_id=picking_type_id,
                team=False
            )

            # Use the cached quality point in the loop
            if quality_point_id:
                is_quality_point_grade = True if quality_point_id.product_grade_ids else False
                for line in self.move_ids_without_package:
                    line.write(
                        {'sh_quality_point_id': quality_point_id.id, 'sh_quality_point': True})
                    if not need_qc and line.remaining_checked_qty > 0:
                        line_id = line.id
                        need_qc = True

            if need_qc:
                return {
                    'name': 'Quality Check',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.stock.move.global.check',
                    'context': {'default_move_id': line_id, 'default_is_quality_point_grade': is_quality_point_grade},
                    'target': 'new',
                }


    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        product_ids = self.move_ids_without_package.mapped('product_id.id')
        picking_type_id = self.picking_type_id.id

        quality_point_id = self._get_qc_point(
            product_ids=product_ids,
            operation_id=picking_type_id,
            team=False
            )

        if quality_point_id:
            for line in self.sh_quality_check_ids:
                if quality_point_id.block_failed:
                    if line.filtered(lambda l: l.state == 'fail'):
                        raise ValidationError('Product "%s" Failed the Quality Check.' % ((line.product_id.name)))

                if line.filtered(lambda l: l.is_quality_point_grade and not l.product_grade_id):
                    raise ValidationError('Please select product grade for "%s".' % ((line.product_id.name)))

        return res

    def _prepare_create_picking_qc(self):
        """Create 2 record of stock.picking for incoming and outgoing QC only if need_qc is True and picking_type_code is incoming or internal."""
        for picking in self:
            move_in = []
            move_out = []
            if picking.is_quality_point_grade and picking.need_qc and picking.picking_type_code == 'incoming' and not picking.picking_grade_id:

                # UNGRADE OUT > D0
                scrap_dest_id = self.env['stock.location'].search(
                    [('usage', '=', 'inventory'), ('name', '=', 'Scrap'), ('scrap_location', '=', True)], limit=1)

                product_ids = picking.move_ids_without_package.mapped('product_id.id')

                quality_point_id = self._get_qc_point(
                    product_ids=product_ids,
                    operation_id=picking.picking_type_id.id,
                    is_product_grade=True,
                    team=False
                )

                for move in picking.move_ids_without_package:
                    if move.product_id.id in quality_point_id.product_ids.ids:
                        # print('PRODUCT GRADE OUT', move.product_id.id)
                        vals_out = {
                            'name': move.name,
                            'product_id': move.product_id.id,
                            'product_uom_qty': move.product_uom_qty,
                            'quantity_done': move.product_uom_qty,
                            'product_uom': move.product_uom.id,
                            'location_id': picking.location_id.id,
                            'location_dest_id': scrap_dest_id.id,
                        }
                        move_out.append((0, 0, vals_out))

                warehouse_id = picking.picking_type_id.warehouse_id
                default_source_location_id = warehouse_id.lot_stock_id
                picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'),
                                                                        ('warehouse_id', '=',
                                                                         warehouse_id.id),
                                                                        ('default_location_src_id', '=', default_source_location_id.id)], limit=1)

                stock_out = self.env['stock.picking'].create({
                    'picking_grade_id': picking.id,
                    'partner_id': picking.partner_id.id,
                    'state': 'draft',
                    'picking_type_id': picking_type_id.id,
                    'picking_type_code': 'outgoing',
                    'location_id': picking_type_id.default_location_src_id.id,
                    'location_dest_id': scrap_dest_id.id,
                    'move_ids_without_package': move_out
                })
                # print('=== STOCK OUT ===', stock_out.name)
                if stock_out:
                    stock_out.action_confirm()
                    stock_out.action_assign()
                    stock_out.button_validate()

                # GRADE IN > RN
                product_grade_ids = self.env['product.product'].search(
                    [('id', 'in', self.mapped('sh_quality_check_ids.product_grade_id').ids)])
                for product in product_grade_ids:
                    vals_in = {
                        'name': product.name,
                        'product_id': product.id,
                        'product_uom_qty': sum(picking.sh_quality_check_ids.filtered(lambda l: l.product_grade_id.id == product.id).mapped('checked_qty')),
                        'quantity_done': sum(picking.sh_quality_check_ids.filtered(lambda l: l.product_grade_id.id == product.id).mapped('checked_qty')),
                        'product_uom': product.uom_id.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                    }
                    move_in.append((0, 0, vals_in))

                stock_in = self.env['stock.picking'].create({
                    'picking_grade_id': picking.id,
                    'partner_id': picking.partner_id.id,
                    'state': 'draft',
                    'picking_type_id': picking.picking_type_id.id,
                    'picking_type_code': 'incoming',
                    'location_id': scrap_dest_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'move_ids_without_package': move_in,
                })
                # print('=== STOCK IN ===', stock_in.name)
                if stock_in:
                    stock_in.action_confirm()
                    stock_in.action_assign()
                    stock_in.button_validate()

            if picking.is_quality_point_grade and picking.need_qc and picking.picking_type_code == 'internal' and not picking.picking_grade_id:
                # print('INTERNAL PICKING')
                # UNGRADE OUT > D0
                scrap_dest_id = self.env['stock.location'].search(
                    [('usage', '=', 'inventory'), ('name', '=', 'Scrap'), ('scrap_location', '=', True)], limit=1)


                product_ids = self.move_ids_without_package.mapped('product_id.id')
                quality_point_id = self._get_qc_point(
                        product_ids=product_ids,
                        operation_id=picking.picking_type_id.id,
                        is_product_grade=True,
                        team=False
                    )

                for move in picking.move_ids_without_package:
                    if move.product_id.id in quality_point_id.product_ids.ids:
                        # print('PRODUCT GRADE OUT', move.product_id.id)
                        vals_out = {
                            'name': move.name,
                            'product_id': move.product_id.id,
                            'product_uom_qty': move.product_uom_qty,
                            'quantity_done': move.product_uom_qty,
                            'product_uom': move.product_uom.id,
                            'location_id': picking.location_id.id,
                            'location_dest_id': scrap_dest_id.id,
                        }
                        move_out.append((0, 0, vals_out))

                warehouse_id = picking.picking_type_id.warehouse_id
                default_source_location_id = warehouse_id.lot_stock_id
                picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'),
                                                                        ('warehouse_id', '=',
                                                                         warehouse_id.id),
                                                                        ('default_location_src_id', '=', default_source_location_id.id)], limit=1)

                stock_out = self.env['stock.picking'].create({
                    'picking_grade_id': picking.id,
                    'partner_id': picking.partner_id.id,
                    'state': 'draft',
                    'picking_type_id': picking_type_id.id,
                    'picking_type_code': 'outgoing',
                    'location_id': picking_type_id.default_location_src_id.id,
                    'location_dest_id': scrap_dest_id.id,
                    'move_ids_without_package': move_out
                })
                # print('=== STOCK OUT ===', stock_out.name)
                if stock_out:
                    stock_out.action_confirm()
                    stock_out.action_assign()
                    stock_out.button_validate()

                # GRADE IN > RN
                product_grade_ids = self.env['product.product'].search(
                    [('id', 'in', self.mapped('sh_quality_check_ids.product_grade_id').ids)])
                warehouse_id = picking.picking_type_id.warehouse_id
                picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'),
                                                                        ('warehouse_id', '=',
                                                                         warehouse_id.id),
                                                                        ('default_location_dest_id', '=', self.location_dest_id.id)], limit=1)

                for product in product_grade_ids:
                    vals_in = {
                        'name': product.name,
                        'product_id': product.id,
                        'product_uom_qty': sum(picking.sh_quality_check_ids.filtered(lambda l: l.product_grade_id.id == product.id).mapped('checked_qty')),
                        'quantity_done': sum(picking.sh_quality_check_ids.filtered(lambda l: l.product_grade_id.id == product.id).mapped('checked_qty')),
                        'product_uom': product.uom_id.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                    }
                    move_in.append((0, 0, vals_in))

                stock_in = self.env['stock.picking'].create({
                    'picking_grade_id': picking.id,
                    'partner_id': picking.partner_id.id,
                    'state': 'draft',
                    'picking_type_id': picking_type_id.id,
                    'location_id': scrap_dest_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'move_ids_without_package': move_in,
                })
                # print('=== STOCK IN ===', stock_in.picking_type_code, stock_in.name)

                if stock_in:
                    stock_in.action_confirm()
                    stock_in.action_assign()
                    stock_in.button_validate()

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        self._prepare_create_picking_qc()
        return res

    def open_quality_check(self):
        po = self.env['sh.quality.check'].search(
            [('sh_picking', '=', self.id)])
        action = self.env.ref(
            'equip3_inventory_qc.quality_check_action_readonly').read()[0]
        action['context'] = {
            'domain': [('id', 'in', po.ids)]

        }
        action['domain'] = [('id', 'in', po.ids)]
        return action

    def open_quality_alert(self):
        alert_ids = self.env['sh.quality.alert'].search(
            [('piking_id', '=', self.id)])
        action = self.env.ref(
            'equip3_inventory_qc.quality_alert_action_readonly').read()[0]
        action['context'] = {
            'domain': [('id', 'in', alert_ids.ids)]
        }
        action['domain'] = [('id', 'in', alert_ids.ids)]
        return action

    def action_view_product_grade(self):
        picking_grade = self.env['stock.picking'].search(
            [('picking_grade_id', '=', self.id), ('picking_type_code', '=', 'incoming')], limit=1)
        # picking_grade = self.env['stock.picking'].search([('picking_grade_id', '=', self.id)], limit=1)
        return {
            'name': 'Product Grade',
            # 'domain': [('picking_grade_id', '=', self.id)],
            'res_model': 'stock.picking',
            'res_id': picking_grade.id,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
        }
