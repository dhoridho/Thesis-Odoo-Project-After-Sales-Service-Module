odoo.define('equip3_pos_general.BigData', function (require) {

    const models = require('point_of_sale.models');
  
    const core = require('web.core');
    const _t = core._t;
    const db = require('point_of_sale.DB');
    const big_data = require('equip3_pos_masterdata.big_data');
    const field_utils = require('web.field_utils');
    const time = require('web.time');
    const retail_db = require('equip3_pos_masterdata.database');
    const bus = require('equip3_pos_masterdata.core_bus');
    const rpc = require('web.rpc');
    const exports = {};
    const {posbus} = require('point_of_sale.utils');
    const { Gui } = require('point_of_sale.Gui');
    const Session = require('web.Session')
    var SuperOrder = models.Order.prototype;
    var SuperOrderline = models.Orderline.prototype;
    var SuperPosModel = models.PosModel.prototype;


    models.load_fields('pos.order', [
        'create_date', 'name', 'date_order', 'user_id', 'amount_tax', 'amount_total', 'amount_paid', 
        'amount_return', 'pricelist_id', 'partner_id', 'sequence_number', 'session_id', 'state', 'account_move', 
        'picking_ids', 'picking_type_id', 'location_id', 'note', 'nb_print', 'pos_reference', 'payment_journal_id', 
        'fiscal_position_id', 'ean13', 'expire_date', 'is_return', 'is_returned', 'voucher_id', 'email', 'write_date', 
        'config_id','is_paid_full', 'session_id', 'shipping_id','return_order_id', 'payment_ids', 'is_return_order', 
        'return_status', 'amount_total','void_order_id','void_state','is_past_date','cashier_id','estimated_order_pre_order','is_pre_order',
        'id', 'lines','so_pickup_id'
    ]);
    models.load_fields('pos.order.line', ['line_qty_returned', 'not_returnable','original_line_id','returnable_by_categories']);
    models.load_fields('res.users', ['name','image_1920','allow_discount','allow_qty','allow_price','allow_remove_line','allow_minus','allow_payment','allow_customer','allow_add_order','allow_remove_order','allow_add_product','allow_payment_zero','cashier_code']);

    
    models.Orderline = models.Orderline.extend({
        initialize: function (attributes, options) {
            let res = SuperOrderline.initialize.apply(this, arguments);
            if (!options.json) {
                this.is_from_cross_sale = '';
            }

            this.picking_type_id = false;
            this.picking_type = false;
            this.picking_warehouse_id = false;
            this.select_stock_quant_id = false;

            return res;
        }, 

        init_from_JSON: function (json) {
            let res = SuperOrderline.init_from_JSON.apply(this, arguments);
            if (json.is_from_cross_sale) {
                this.is_from_cross_sale = json.is_from_cross_sale;
            }
            if (json.picking_type_id){
                this.picking_type_id = json.picking_type_id;
            }
            if (json.picking_type){
                this.picking_type = json.picking_type;
            }
            if (json.picking_warehouse_id){
                this.picking_warehouse_id = json.picking_warehouse_id;
            }
            if (json.select_stock_quant_id){
                this.select_stock_quant_id = json.select_stock_quant_id;
            }
            return res;
        },

        export_as_JSON: function () {
            let json = SuperOrderline.export_as_JSON.apply(this, arguments);
            if (this.is_from_cross_sale) {
                json.is_from_cross_sale = this.is_from_cross_sale;
            }

            if (this.picking_type_id){
                json.picking_type_id = this.picking_type_id;
            }
            if (this.picking_type){
                json.picking_type = this.picking_type;
            }
            if (this.picking_warehouse_id){
                json.picking_warehouse_id = this.picking_warehouse_id;
            }
            if (this.select_stock_quant_id){
                json.select_stock_quant_id = this.select_stock_quant_id;
            }
            return json;
        },
        export_for_printing: function(){
            var res = SuperOrderline.export_for_printing.apply(this, arguments);
            if (!this.picking_type_id || !this.picking_type || !this.picking_warehouse_id || !this.select_stock_quant_id) {
                var stock_quant = false
                if (this.pos.stock_quant_by_product_id) {
                    const product = this.get_product();
                    const stock_quant_product_id = this.pos.stock_quant_by_product_id[product.id]
                    if (stock_quant_product_id) {
                        stock_quant = stock_quant_product_id.find(item => item.quantity >= 1);
                    }
                    if (this.pos.get_order().is_multiple_warehouse === true && stock_quant !== false){
                        if (this.picking_type === undefined || this.picking_type_id === undefined){
                            if (this.pos.stock_quant_by_product_id[product.id]) {
                                const picking_type = this.pos.stock_picking_types.find(item => item.default_location_src_id[0] === stock_quant.location_id[0]);
                                if (picking_type !== undefined){
                                    this.picking_type = picking_type;
                                    this.picking_type_id = picking_type.id;
                                    this.picking_warehouse_id = stock_quant.warehouse_id;
                                }
                            }
                        }
                    }
                }
                this.select_stock_quant_id = stock_quant;
                res['picking_type_id'] = this.picking_type_id;
                res['picking_type'] = this.picking_type;
                res['picking_warehouse_id'] = this.picking_warehouse_id;
                res['select_stock_quant_id'] = this.select_stock_quant_id;
            } else {
                res['picking_type_id'] = this.picking_type_id;
                res['picking_type'] = this.picking_type;
                res['picking_warehouse_id'] = this.picking_warehouse_id;
                res['select_stock_quant_id'] = this.select_stock_quant_id;
            }
            return res;
        },
        _auto_select_stock_quant(){
            var stock_quant = false
            if (this.pos.stock_quant_by_product_id){
                const product = this.get_product();
                const stock_quant_product_id = this.pos.stock_quant_by_product_id[product.id]
                if (stock_quant_product_id) {
                    stock_quant = stock_quant_product_id.find(item => item.quantity >= 1);
                }
            }
            let order = this.pos.get_order();
            if(order && order.is_multiple_warehouse && stock_quant){
                if (!this.picking_type || !this.picking_type_id){
                    const picking_type = this.pos.stock_picking_types.find(item => item.default_location_src_id[0] === stock_quant.location_id[0]);
                    if(picking_type === undefined){
                        Gui.showPopup('ErrorPopup', {
                            title: this.pos.env._t('Warning'),
                            body: this.pos.env._t('Warehouse "' + stock_quant.location_id + '" is not found. Please configure in Stock Operation Types > Operation Types'),
                            confirmText: 'OK',
                            cancelText: ''
                        });
                        return false;
                    }
                    if (picking_type){
                        this.picking_type = picking_type;
                        this.picking_type_id = picking_type.id;
                        this.picking_warehouse_id = stock_quant.warehouse_id;
                    }
                }
            }
            this.select_stock_quant_id = stock_quant;
        },
        set_quantity: function(quantity, keep_price){
            SuperOrderline.set_quantity.apply(this, arguments);
            this._auto_select_stock_quant();
        }
    });
    

    models.Order = models.Order.extend({
        initialize: function (attributes, options){
            SuperOrder.initialize.apply(this, arguments);
            this.is_multiple_warehouse = this.check_order_multiple_warehouse();
        },
        init_from_JSON: function (json) {
            let res = SuperOrder.init_from_JSON.apply(this, arguments);
            if (json.is_multiple_warehouse){
                this.is_multiple_warehouse = json.is_multiple_warehouse;
            }
            return res;
        },
        export_as_JSON: function () {
            const json = SuperOrder.export_as_JSON.apply(this, arguments);
            if (this.is_multiple_warehouse){
                json.is_multiple_warehouse = this.is_multiple_warehouse;
            }
            return json;
        },
        check_order_multiple_warehouse: function () {
            if (this.pos.config.multi_stock_operation_type){
                return true;
            } else {
                return false;
            }
        },
    })


    models.PosModel = models.PosModel.extend({
        _save_to_server: function (orders, options) {
            var self = this;
            return SuperPosModel._save_to_server.call(this,orders,options).then(function(return_dict){
                if (return_dict && return_dict.length >= 1){
                    _.each(orders, function(order){
                        if(order.data && order.data.lines){
                            _.each(order.data.lines, function(line_data){
                                let orderline = line_data[2];
                                let select_stock_quant_id = false;
                                if (orderline.select_stock_quant_id){
                                    select_stock_quant_id = orderline.select_stock_quant_id.id
                                }
                                if (orderline && select_stock_quant_id) {
                                    let stock_quant = self.stock_quant.find(o => o.id === select_stock_quant_id)
                                    if (stock_quant){
                                        stock_quant.quantity -= orderline.qty;
                                    }
                                }
                            });
                        }
                    });
                }
                return return_dict;
            })
        },
    })


});
