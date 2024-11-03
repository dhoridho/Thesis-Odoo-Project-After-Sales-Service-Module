
from odoo import api, fields, models, _
from odoo.exceptions import UserError , ValidationError
from datetime import timedelta, datetime, date


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    is_purchase_tender = fields.Boolean(string="Purchase Tender", compute="_compute_is_purchase_order", store=False)
    analytic_account_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Account Group")
    request_date = fields.Date(string="Request date")
    is_single_request_date = fields.Boolean(string="Single Request Date")
    is_pr_to_pt = fields.Boolean(compute="_compute_pr_to_pt", string="Purchase Tender", store=True)
    purchase_tender_count = fields.Integer(compute="_compute_purchase_tender_count", string="Purchase Tender Count")
    amount_total = fields.Monetary(string='Estimated Total', readonly=True,compute='_amount_total')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
        
    @api.depends('line_ids','line_ids.estimated_cost', 'line_ids.product_qty')    
    def _amount_total(self):
        for order in self:
            amount_total=0
            for line in order.line_ids:
                amount_total += line.estimated_cost * line.product_qty
            order.update({
                'amount_total': amount_total,
            })
    
    def _compute_purchase_tender_count(self):
        for record in self:
            record.purchase_tender_count = self.env["purchase.agreement"].search_count(
                [("purchase_request_id", "=", record.id)]
            )

    def action_view_purchase_tender(self):
        self.ensure_one()
        context = dict(self.env.context) or {}
        return {
            "name": _("Purchase Tender"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.agreement",
            "view_mode": "tree,form",
            "domain": [("purchase_request_id", "=", self.id)],
            "target": "current",
            "context": context,
        }

    @api.depends('requested_by')
    def _compute_pr_to_pt(self):
        for record in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            is_purchase_tender = IrConfigParam.get_param('is_purchase_tender', False)
            # is_purchase_tender = self.env.company.is_purchase_tender
            record.is_pr_to_pt = is_purchase_tender

    @api.onchange('request_date', 'is_single_request_date')
    def onchange_request_date(self):
        for record in self:
            for line in record.line_ids:
                if record.is_single_request_date and record.request_date:
                    line.date_required = record.request_date

    @api.onchange('requested_by')
    def get_requested_by(self):
        self._compute_is_purchase_order()
    
    def _compute_is_purchase_order(self):
        purchase_tender = self.env['ir.config_parameter'].sudo().get_param('is_purchase_tender')
        # purchase_tender = self.env.company.is_purchase_tender
        for record in self:
            record.is_purchase_tender = purchase_tender

    blanket_order_count = fields.Integer(
        string="Blanket Order count",
        compute="_compute_blanket_order_count",
        readonly=True,
    )

    purchase_tender_count = fields.Integer(
        string="Purchase Tender",
        compute="_compute_purchase_tender_count",
        readonly=True,
    )

    @api.depends("line_ids")
    def _compute_blanket_order_count(self):
        for record in self:
            id = record.id or False
            if id:
                self.env.cr.execute("""
                    SELECT count(id)
                      FROM purchase_requisition
                     WHERE purchase_request_id = %s
                """ % record.id or False)
                purchase_bo = self.env.cr.fetchall()
                record.blanket_order_count = purchase_bo[0][0]
            else:
                record.blanket_order_count = 0

    def action_view_blanket_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Blanket Order',
            'view_mode': 'tree,form',
            'res_model': 'purchase.requisition',
            'domain' : [('purchase_request_id','=',self.id)],
            'target': 'current'
        }    

    def create_purchase_tender(self):
        data = []
        for record in self:
            # sh_source = record.origin
            sh_source = ",".join(record.line_ids.mapped('request_id.name'))
            for rec in record.line_ids:
                data.append((0, 0, {
                    'product_id' : rec.product_id.id,
                    'product_description': rec.name,
                    'remaning_qty': 0 if rec.remaning_qty < 0 else rec.remaning_qty,
                    'pr_line_id': rec.id,
                    'tender_qty': 0 if rec.remaning_qty < 0 else rec.remaning_qty,
                    'uom': rec.product_uom_id.id,
                    'destination_warehouse': rec.dest_loc_id.id,
                    'analytics_tag_ids': [(6, 0, rec.analytic_account_group_ids.ids)],
                    'schedule_date': rec.date_required,
                    }))
        context = {'default_product_line_ids': data, 'default_sh_source': sh_source}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Purchase Tender',
            'view_mode': 'form',
            'res_model': 'purchase.tender.create.wizard',
            'target': 'new',
            'context': context,
        }
        # data = []
        # for record in self:
        #     record.purchase_req_state = 'in_progress'
        #     branch_id = False
        #     if record.branch_id:
        #         branch_id = record.branch_id.id
        #     for line_id in record.line_ids:
        #         data.append((0, 0, {'sh_product_id' : line_id.product_id.id,
        #                             'sh_qty' : line_id.product_qty,
        #                             'sh_ordered_qty' : line_id.purchased_qty,
        #                             'sh_price_unit' : line_id.estimated_cost,
        #                             'sh_product_uom_id': line_id.product_uom_id.id,
        #                             'company_id' : line_id.company_id.id,
        #                             'dest_warehouse_id': line_id.dest_loc_id.id,
        #                             'analytic_tag_ids': [(6, 0, line_id.analytic_account_group_ids.ids)]
        #         }))
        #     purchase_tender = self.env['purchase.agreement'].create({
        #             'sh_purchase_user_id' : record.requested_by.id,
        #             'sh_source' : record.name,
        #             'company_id' : record.company_id.id,
        #             'sh_purchase_agreement_line_ids' : data,
        #             'purchase_request_id' : record.id,
        #             'branch_id': branch_id
        #     })
        #     record.line_ids.write({'agreement_id': purchase_tender})
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'name': 'Purchase Tender',
        #         'view_mode': 'form',
        #         'res_model': 'purchase.agreement',
        #         'res_id' : purchase_tender.id,
        #         'target': 'current'
        #     }

    # def create_blanket_order(self):
    #     data = []
    #     for record in self:
    #         record.purchase_req_state = 'in_progress'
    #         for line_id in record.line_ids:
    #             data.append((0, 0, {'product_id' : line_id.product_id.id,
    #                                 'product_qty' : line_id.product_qty,
    #                                 'price_unit' : line_id.estimated_cost,
    #             }))
    #         blanket_order = self.env['purchase.requisition'].create({
    #                 'user_id' : record.requested_by.id,
    #                 'origin' : record.name,
    #                 'company_id' : record.company_id.id,
    #                 'line_ids' : data,
    #                 'purchase_request_id' : record.id
    #         })
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': 'Blanket Order',
    #             'view_mode': 'form',
    #             'res_model': 'purchase.requisition',
    #             'res_id' : blanket_order.id,
    #             'target': 'current'
    #         }

class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    analytic_account_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Account Group")
    purchase_order = fields.Char(string="Purchase Order", compute="_compute_purchase_order", store=False)
    agreement_id = fields.Many2one('purchase.agreement', string="Purchase Tender")
    agreement_state = fields.Selection(related='agreement_id.state', string="Purchase Tender Status")
    tender_qty = fields.Float(string="Tender Qty", compute='_compute_tender_qty', store=True)
    tender_line_ids = fields.One2many('purchase.agreement.line', 'request_line_id', string='Agreement Lines')
    purchase_order_line_ids = fields.One2many('purchase.order.line', 'request_line_id', string='Purchase Order Line')
    qty_received = fields.Float(string='Received Qty', compute='_compute_qty_received', store=True)

    @api.depends('purchase_order_line_ids', 'purchase_order_line_ids.qty_received')
    def _compute_qty_received(self):
        for record in self:
            record.qty_received = sum(record.purchase_order_line_ids.filtered(lambda r: r.order_id.state != 'cancel').mapped('qty_received'))

    @api.depends('purchase_order_line_ids', 'purchase_order_line_ids.product_qty', 'purchase_order_line_ids.order_id.state')
    def _compute_purchased_qty(self):
        for record in self:
            record.purchased_qty = sum(record.purchase_order_line_ids.filtered(lambda r: r.order_id.state == 'purchase').mapped('product_qty'))

    @api.depends('tender_line_ids', 'tender_line_ids.sh_qty', 'tender_line_ids.agreement_id.state2')
    def _compute_tender_qty(self):
        for record in self:
            record.tender_qty = sum(record.tender_line_ids.filtered(lambda r: r.agreement_id.state2 != 'cancel').mapped('sh_qty'))

    @api.depends('product_qty', 'purchased_qty', 'tender_qty', 'request_id', 'qty_received')
    def _compute_remaning_qty(self):
        for record in self:
            purchased_qty = record.qty_received
            if record.request_id.is_pr_to_pt:
                purchased_qty += record.tender_qty
            record.remaning_qty = record.product_qty - purchased_qty

    def _compute_purchase_order(self):
        for record in self:
            name = ",".join(record.purchase_lines.mapped('order_id.name'))
            record.purchase_order = name

    @api.model
    def create_purchase_tender(self):
        data = []
        context = dict(self.env.context) or {}
        purchase_request_line_ids = self.browse(self._context.get('active_ids'))
        is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
        # is_good_services_order = self.env.company.is_good_services_order
        if is_good_services_order:
            if all(line.is_goods_orders for line in purchase_request_line_ids):
                context.update({'is_goods_orders': True, 'goods_order': True})
            elif all(line.is_services_orders for line in purchase_request_line_ids):
                context.update({'is_services_orders': True, 'services_good': True})
            if purchase_request_line_ids and 'is_assets_orders' in purchase_request_line_ids[0]._fields and \
                all(line.is_assets_orders for line in purchase_request_line_ids):
                context.update({'is_assets_orders': True, 'assets_orders': True})
            if purchase_request_line_ids and 'is_rental_orders' in purchase_request_line_ids[0]._fields and \
                all(line.is_rental_orders for line in purchase_request_line_ids):
                context.update({'is_rental_orders': True, 'rentals_orders': True})
        requested_by = purchase_request_line_ids.mapped('requested_by')
        if len(requested_by) > 1:
            raise ValidationError("Requested By should be same for all record!")
        sh_source = ",".join(purchase_request_line_ids.mapped('request_id.name'))
        company_id = purchase_request_line_ids.mapped('company_id').id
        for purchase_req_line in purchase_request_line_ids:
            if purchase_req_line.request_id.state != 'approved' and purchase_req_line.request_id.purchase_req_state not in ('pending','in_progress'):
                raise UserError(_("Purchase Request %s Is Not Approved") % (purchase_req_line.request_id.name)) 
            else:
                for rec in purchase_req_line:
                    data.append((0, 0, {
                        'product_id' : rec.product_id.id,
                        'product_description': rec.name,
                        'remaning_qty': rec.remaning_qty,
                        'pr_line_id': rec.id,
                        'tender_qty': rec.remaning_qty,
                        'uom': rec.product_uom_id.id,
                        'destination_warehouse': rec.dest_loc_id.id,
                        'analytics_tag_ids': [(6, 0, rec.analytic_account_group_ids.ids)],
                        'schedule_date': rec.date_required,
                    }))
        context.update({'default_product_line_ids': data, 'default_sh_source': sh_source})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Purchase Tender',
            'view_mode': 'form',
            'res_model': 'purchase.tender.create.wizard',
            'target': 'new',
            'context': context,
        }
        #         data.append((0, 0, {'sh_product_id' : purchase_req_line.product_id.id,
        #                             'sh_qty' : purchase_req_line.product_qty,
        #                             'sh_ordered_qty' : purchase_req_line.purchased_qty,
        #                             'sh_price_unit' : purchase_req_line.estimated_cost,
        #                             'company_id' : purchase_req_line.company_id.id,
        #         }))
        # purchase_tender = self.env['purchase.agreement'].create({
		# 		'sh_purchase_user_id' : requested_by.id,
        #         'sh_source' : sh_source,
        #         'is_goods_orders': is_goods_orders,
        #         'company_id' : company_id,
        #         'sh_purchase_agreement_line_ids' : data
        # })
        # purchase_request_line_ids.write({'agreement_id': purchase_tender})
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Purchase Tender',
        #     'view_mode': 'tree,form',
        #     'res_model': 'purchase.agreement',
        #     'domain' : [('id', 'in', purchase_tender.ids)],
        #     'target': 'current'
        # }  
        

    
    @api.model
    def create_blanket_order(self):
        data = []
        purchase_request_line_ids = self.browse(self._context.get('active_ids'))
        is_goods_orders = False
        if all(line.is_goods_orders for line in purchase_request_line_ids):
            is_goods_orders = True
        requested_by = purchase_request_line_ids.mapped('requested_by')
        if len(requested_by) > 1:   
            raise ValidationError("Requested By should be same for all record!")
        origin = ",".join(purchase_request_line_ids.mapped('request_id.name'))
        company_id = purchase_request_line_ids.mapped('company_id').id
        for purchase_req_line in purchase_request_line_ids:
            if purchase_req_line.request_id.state not in 'approved' and purchase_req_line.request_id.purchase_req_state not in ('pending','in_progress'):
                raise UserError(_("Purchase Request %s Is Not Approved") % (purchase_req_line.request_id.name))
            else:
                data.append((0, 0, {'product_id' : purchase_req_line.product_id.id,
                                    'product_qty' : purchase_req_line.product_qty,
                                    'price_unit' : purchase_req_line.estimated_cost,
                }))
        blanket_order = self.env['purchase.requisition'].create({
				'user_id' : requested_by.id,
                'origin' : origin,
                'is_goods_orders': is_goods_orders,
                'company_id' : company_id,
                'line_ids' : data
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Blanket Order',
            'view_mode': 'tree,form',
            'res_model': 'purchase.requisition',
            'domain' : [('id', 'in', blanket_order.ids)],
            'target': 'current'
        }

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    not_editable = fields.Boolean('Not Editable')
    is_editable = fields.Boolean('Is Editable')
    tender_order_line = fields.One2many('purchase.order.line', 'purchase_order_id', string='Tender Order Lines')
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Purchase Order Lines', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True) #rename to purchase order line
    from_bo = fields.Boolean("RFQ/PO from BO", default=False)
    is_btn_approval_matrix = fields.Boolean('Button Approval Matrix', compute="_compute_btn_approval_matrix")
    state = fields.Selection(selection_add=[
        ('request_for_amendment', 'Request for Amendment'),
        ('draft',),
        ('rfq_approved',),
        ('blanket_ordered', 'Blanket Ordered'),
    ])
    is_blanket_cancel = fields.Boolean('Blanket Order Cancel', compute="_compute_blanket_cancel")
    open_tender = fields.Boolean("Open Tender")

    @api.onchange('product_template_id')
    def product_template_id_change(self):
        if self.product_template_id:
            data = [(5, 0, 0)]
            for record in self.product_template_id.purchase_product_template_ids:
                vals = {}
                vals.update({
                    'price_unit': record.unit_price,
                    'name': record.description,
                    'product_qty': record.ordered_qty,
                    'product_uom': record.product_uom.id,
                    'date_planned': datetime.now(),
                    'analytic_tag_ids': [(6, 0, self.analytic_account_group_ids.ids)]
                })
                if record.name:
                    vals.update({'product_id': record.name.id})
                data.append((0, 0, vals))
            self.update({
                'order_line': data,
            })

    def _compute_blanket_cancel(self):
        for search in self:
            blanket_obj = self.env['purchase.requisition'].search([('purchase_id', '=', search.id)])
            count_blanket = len(blanket_obj)
            count_cancel = 0
            for blanket in blanket_obj:
                if blanket.state_blanket_order == 'cancel':
                    count_cancel += 1
            if count_blanket == count_cancel:
                search.is_blanket_cancel = True
            else:
                search.is_blanket_cancel = False
    
    @api.model
    def action_approval_matrix_menu(self):
        # IrConfigParam = self.env['ir.config_parameter'].sudo()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_blanket_order_approval_matrix = IrConfigParam.get_param('is_blanket_order_approval_matrix', False)
        is_purchase_request_approval_matrix = IrConfigParam.get_param('is_purchase_request_approval_matrix', False)
        is_purchase_order_approval_matrix = IrConfigParam.get_param('is_purchase_order_approval_matrix', False)
        is_purchase_tender_approval_matrix=IrConfigParam.get_param('is_purchase_tender_approval_matrix', False)
        # is_blanket_order_approval_matrix = self.env.company.is_blanket_order_approval_matrix
        # is_purchase_request_approval_matrix = self.env.company.is_purchase_request_approval_matrix
        # is_purchase_order_approval_matrix = self.env.company.is_purchase_order_approval_matrix
        # is_purchase_tender_approval_matrix = self.env.company.is_purchase_tender_approval_matrix
        if is_blanket_order_approval_matrix:
            self.env.ref('equip3_purchase_other_operation.approval_matrix_blanket_order_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_other_operation.approval_matrix_blanket_order_configuration_menu').active = False
        if is_purchase_tender_approval_matrix:
            self.env.ref('equip3_purchase_other_operation.approval_matrix_purchase_agreement_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_other_operation.approval_matrix_purchase_agreement_configuration_menu').active = False

        if is_purchase_order_approval_matrix:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_order_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_order_configuration_menu').active = False

        if is_purchase_request_approval_matrix:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_request_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_request_configuration_menu').active = False

    def _compute_approval_matrix(self):
        res = super(PurchaseOrder, self)._compute_approval_matrix()
        for record in self:
            if record.from_bo:
                record.is_approval_matrix = False
        return res


    def set_not_editable(self):
        for res in self:
            res.write({'state': 'request_for_amendment', 'is_editable': False})
            for line in res.order_line:
                line.purchase_order_id = line.order_id.id

    def action_button_confirm(self):
        for record in self:
            record.write({'state': 'draft', 'is_editable': True})

    @api.model
    def create(self, vals):
        if 'agreement_id' in vals:
            agreement_id = self.env['purchase.agreement'].browse(vals['agreement_id'])
            if agreement_id.tender_scope == 'open_tender':
                vals['open_tender'] = True
        res = super(PurchaseOrder, self).create(vals)
        if res.agreement_id:
            if res.agreement_id.state == 'bid_selection':
                res.not_editable = True
        return res

    @api.depends('order_line', 'partner_id', 'state', 'is_approval_matrix', 'approval_matrix_id')
    def _compute_btn_approval_matrix(self):
        for record in self:
            record.is_btn_approval_matrix = False
            if not record.is_approval_matrix and record.state in ('draft','sent'):
                record.is_btn_approval_matrix = True
            elif record.is_approval_matrix and record.state in ('draft','sent') and not record.approval_matrix_id:
                record.is_btn_approval_matrix = True
            elif record.is_approval_matrix and record.state == 'rfq_approved' and record.approval_matrix_id:
                record.is_btn_approval_matrix = True

    def create_blanket_order(self):
        data = []
        branch_id = False
        for record in self:
            if record.branch_id:
                branch_id = record.branch_id.id
            for line_id in record.order_line:
                data.append((0, 0, {
                    'product_id' : line_id.product_id.id,
                    'product_qty' : line_id.product_qty,
                    'price_unit' : line_id.price_unit,
                    'company_id' : line_id.company_id.id,
                    'destination_warehouse': line_id.destination_warehouse_id.id,
                    'product_uom_id': line_id.product_uom.id,
                    'account_tag_ids': [(6, 0, line_id.analytic_tag_ids.ids)],
                }))
            blanket_order_id = self.env['purchase.requisition'].create({
                    'purchase_id': record.id,
                    'user_id' : record.create_uid.id,
                    'vendor_id': record.partner_id.id,
                    'account_tag_ids': [(6, 0, record.analytic_account_group_ids.ids)],
                    'origin' : record.name,
                    'currency_id': record.currency_id.id,
                    'company_id' : record.company_id.id,
                    'branch_id': branch_id,
                    'destination_warehouse': record.destination_warehouse_id.id,
                    'line_ids' : data
            })
            record.write({'state':'blanket_ordered'})
            return {
                'type': 'ir.actions.act_window',
                'name': 'Blanket Order',
                'domain': [('purchase_id','=',record.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'purchase.requisition',
                # 'res_id' : blanket_order_id.id,
                'target': 'current'
            }

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        domain = [('company_id','=',self.env.company.id),('purchase_ok','=',True)]
        if context.get('goods_order'):
            return domain+[('type', 'in', ('consu','product'))]
        elif context.get('services_good'):
            return domain+[('type', '=', 'service')]
        return domain

    product_template_id = fields.Many2one(domain=_default_domain, required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    is_goods_orders = fields.Boolean(string="Goods Orders", default=False)
    is_services_orders = fields.Boolean(string="Services Orders", default=False)  
    requisition_line_id = fields.Many2one('purchase.requisition.line')
    agreement_line_id = fields.Many2one('purchase.agreement.line', string='Agreement Line')
    sh_product_description = fields.Text(string="Product Description")
    not_editable = fields.Boolean('Not Editable', related='order_id.not_editable', store=True)

    @api.depends('company_id', 'destination_warehouse_id', 'product_id', 'requisition_line_id')
    def compute_destination(self):
        res = super(PurchaseOrderLine, self).compute_destination()
        if not self[0].order_id.is_single_delivery_destination:
            for record in self:
                if record.requisition_line_id:
                    record.destination_warehouse_id = record.requisition_line_id.destination_warehouse
        return res

    def action_confirm(self):
        res = super(PurchaseOrderLine, self).action_confirm()
        for line in self:
            line.status = 'confirm'
        return res

    @api.onchange('price_unit')
    def onchange_price_unit(self):
        self.order_id._amount_all()
        self.order_id._compute_approval_matrix_id()

class PurchaseAgreementLine(models.Model):
    _inherit ='purchase.agreement.line'

    schedule_date = fields.Date(string='Scheduled Date', default= datetime.now().date() + timedelta(days=14))

    # Jalan
    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        domain = [('company_id','=',self.env.company.id),('purchase_ok','=',True)]
        if context.get('goods_order'):
            return domain+[('type', 'in', ('consu','product'))]
        elif context.get('services_good'):
            return domain+[('type', '=', 'service')]
        return domain

    sh_product_id = fields.Many2one(domain=_default_domain)

class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    # Jalan
    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        domain = [('company_id','=',self.env.company.id),('purchase_ok','=',True)]
        if context.get('goods_order'):
            return domain+[('type', 'in', ('consu','product'))]
        elif context.get('services_good'):
            return domain+[('type', '=', 'service')]
        return domain

    product_id = fields.Many2one(domain=_default_domain)
    branch_id = fields.Many2one(
        'res.branch',
        related='requisition_id.branch_id', store=True,
        default=lambda self: self.env.user.branch_id)

class PurchaseAgreement(models.Model):
    _inherit ='purchase.agreement'

    is_goods_orders = fields.Boolean(string="Goods Orders", default=False)
    is_services_orders = fields.Boolean(string="Services Orders", default=False)  

class PurchaseRequisition(models.Model):
    _inherit ='purchase.requisition'

    is_goods_orders = fields.Boolean(string="Goods Orders", default=False)
    is_services_orders = fields.Boolean(string="Services Orders", default=False)  
