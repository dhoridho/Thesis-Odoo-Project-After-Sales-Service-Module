odoo.define('equip3_pos_masterdata_fnb.Models', function (require) {
    'use strict';
    const models = require('point_of_sale.models');
    const rpc = require('pos.rpc');
    
    models.load_fields('restaurant.table', ['customer_name', 'date_reserve']);
    models.load_fields("pos.order.line", ['is_complementary']);


    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        export_for_printing: function(){
            var receipt = _super_order.export_for_printing.apply(this, arguments);
            if(this.backendOrder){
                var qrcodelink = window.origin + "/pos/fnb/scanQrCode?order_id=" + this.backendOrder.id
            }
            else{
                var qrcodelink = false
            }
            receipt['qrcodelink'] = qrcodelink
            return receipt;
        }
    });

    let _super_pos_model = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function(attributes) {
            _super_pos_model.initialize.apply(this,arguments);
            this.r_customer_name = '';
            this.table_reserve_date = '';
            this.clear_interval = '';
            this.apply_promotion_succeed = false;
        },
        checkIsLocked: function(table){
            var result = false
            if(table.locked){
                result = true 
            }
            if(table.date_reserve && !table.locked){
                let reserve_dt = table.date_reserve
                let lock_dt = new Date(moment(reserve_dt).format('YYYY-MM-DD HH:mm:ss'))
                let dt_now = new Date(moment().utc().format('YYYY-MM-DD HH:mm:ss'))
                let diff = dt_now - lock_dt
                if(diff > 0){
                    result = true 
                }

            }
            return result 
        },
        async unlock_table() {
            var self = this;
            let resultUnLock = await rpc.query({
                model: 'restaurant.table',
                method: 'lock_table',
                args: [[this.table_click.id], {
                    'locked': false,
                    'customer_name': '',
                    'date_reserve': false,
                }],
            }, {
                timeout: 30000,
                shadow: true,
            })
            if (resultUnLock) {
                this.table_click['locked'] = false;
                const table = this.tables.find(t => t.id == this.table_click.id)
                table.locked = false;
                table.date_reserve = false
                this.set_table(this.table_click);
                var orders = this.get('orders').models;
                const order_of_table = orders.find(o => o.table && o.table.id == table.id)
                if (self.pos_bus && order_of_table) {
                    self.pos_bus.send_notification({
                        data: {
                            order: order_of_table.export_as_JSON(),
                            table_id: order_of_table.table.id,
                            order_uid: order_of_table.uid,
                            lock: false,
                            customer_name: '',
                            date_reserve: false
                        },
                        action: 'lock_table',
                        order_uid: order_of_table.uid,
                    })
                }
            }
        },
    });

});