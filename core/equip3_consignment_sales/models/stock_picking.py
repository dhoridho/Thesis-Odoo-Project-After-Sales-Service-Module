from odoo import _, api, fields, models
from lxml import etree
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_consignment_id = fields.Many2one(
        comodel_name='sale.consignment.agreement', string='Sale Consignment')

    def _action_done(self):
        result = super(StockPicking, self)._action_done()

        # ITR
        transfer_id = self.transfer_id
        if transfer_id and transfer_id.sale_consignment_id:
            sale_consignment_id = transfer_id.sale_consignment_id

            consignment_lines_dict = {
                line.product_id.id: line for line in sale_consignment_id.consignment_line_ids
            }

            for move_line in self.move_line_ids_without_package:
                product_tmpl_id = move_line.product_id.product_tmpl_id
                consignment_line = consignment_lines_dict.get(product_tmpl_id.id)

                if consignment_line:
                    # Update consignment quantities based on transfer type
                    if transfer_id.is_transfer_back_consignment:
                        consignment_line.current_qty -= move_line.qty_done
                    else:
                        if self.is_transfer_in or not self.is_transfer_out and not self.is_transfer_in:
                            consignment_line.product_transferred_qty += move_line.qty_done
                            consignment_line.current_qty += move_line.qty_done

        # Consignment Orders
        if self.picking_type_id.code == 'outgoing':
            if self.sale_id:
                self.sale_consignment_id = self.sale_id.sale_consignment_id
                consignment_lines_dict = {
                    line.product_id.id: line for line in self.sale_consignment_id.consignment_line_ids
                }

                for move_line in self.move_line_ids_without_package:
                    product_tmpl_id = move_line.product_id.product_tmpl_id
                    consignment_line = consignment_lines_dict.get(product_tmpl_id.id)

                    if consignment_line:
                        consignment_line.current_qty -= move_line.qty_done

        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        result = super(StockPicking, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        try:
            context = self.env.context
            active_model = context.get('active_model')
            active_id = context.get('active_id')
            is_visible = False

            if active_model == 'internal.transfer':
                internal_transfer = self.env['internal.transfer'].browse(active_id)
                if internal_transfer and internal_transfer.sale_consignment_id:
                    is_visible = True
            
            elif active_model == 'sale.order':
                sale_order = self.env['sale.order'].browse(active_id)
                if sale_order and sale_order.sale_consignment_id:
                    is_visible = True
               
            _logger.info(f"========= IS VISIBLE: {is_visible} ==========")     
            if is_visible and view_type == 'form':
                move_ids_view = result['fields']['move_ids_without_package']['views']['tree']['arch']
                doc = etree.XML(move_ids_view)
                tree_element = doc.xpath("//tree")[0]
                tree_element.set('create', '0')
                updated_arch = etree.tostring(doc, pretty_print=True, encoding='unicode')
                result['fields']['move_ids_without_package']['views']['tree']['arch'] = updated_arch

        except Exception as e:
            _logger.error(f"An error occurred: {str(e)}")

        return result