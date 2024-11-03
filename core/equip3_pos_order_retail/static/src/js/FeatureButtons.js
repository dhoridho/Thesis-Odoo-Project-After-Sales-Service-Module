odoo.define('equip3_pos_order_retail.FeatureButtons', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const FeatureButtons = require('pos_retail.FeatureButtons');
    const TransferOrderButton = require('pos_restaurant.TransferOrderButton');
    var models = require('point_of_sale.models');
    const {posbus} = require('point_of_sale.utils');
    const TableWidget = require('pos_restaurant.TableWidget');
    models.load_fields('restaurant.table', ['tbl_moved_from','date_reserve','clear_interval']);

    // const core = require('web.core');
    // const qweb = core.qweb;
    // const {Printer} = require('point_of_sale.Printer');
    // const OrderReceipt = require('point_of_sale.OrderReceipt');
    // const field_utils = require('web.field_utils');
    // const {useListener} = require('web.custom_hooks');
    // const {useState} = owl.hooks;
    // const Session = require('web.Session')
    // const framework = require('web.framework');

    const POSTableWidgetExt = (TableWidget) =>
        class extends TableWidget {
            mounted() {
                super.mounted(...arguments);
                var self = this;
                let table = this.props.table;
                let curr_tbl_interval = false
                let curr_locked_tbl_id = false
                let tbl_locked = false
                const selectedOrder = this.env.pos.get_order()
                const orders = this.env.pos.get('orders').models;
                // setTimeout(function () {
                curr_tbl_interval = setInterval(function () {
                    self.rpc({
                        model: 'restaurant.table',
                        method: 'search_read',
                        args: [[['id','=',table.id]], ['id','name','date_reserve','clear_interval']],
                    }).then(function(tbl){
                        if(tbl.length && tbl[0].date_reserve){
                            let reserve_dt = tbl[0].date_reserve
                            let lock_dt = new Date(moment(reserve_dt).format('YYYY-MM-DD HH:mm:ss'))
                            let dt_now = new Date(moment().utc().format('YYYY-MM-DD HH:mm:ss'))
                            let diff = dt_now - lock_dt
                            let days = diff / (24*60*60*1000);
                            let hours = (days % 1) * 24;
                            let minutes = (hours % 1) * 60;
                            let secs = (minutes % 1) * 60;
                            [days, hours, minutes, secs] = [Math.floor(days), Math.floor(hours), Math.floor(minutes), Math.floor(secs)]
                            // var duration = moment.duration(moment(max).diff(moment(min)));
                            if(diff > 0 && !tbl_locked){
                                // selectedOrder.lock_order()
                                self.rpc({
                                    model: 'restaurant.table',
                                    method: 'lock_table',
                                    args: [[table.id], {
                                        'locked': true,
                                        'customer_name': self.env.pos.r_customer_name || '',
                                        'date_reserve': self.env.pos.table_reserve_date || false,
                                        'clear_interval': self.env.pos.clear_interval || false
                                    }],
                                })
                                table.locked = true
                                tbl_locked = true
                                curr_locked_tbl_id = tbl.id
                                self.env.pos.set_table(null)
                                posbus.trigger('refresh:FloorScreen')
                            }
                        }
                    })
                },4000)
                if(table.id){
                    this.rpc({
                        model: 'restaurant.table',
                        method: 'write',
                        args: [table.id, {clear_interval: curr_tbl_interval}],
                    })
                }
            }
        }
    Registries.Component.extend(TableWidget, POSTableWidgetExt);

    const TableLockFeatureButtons = (FeatureButtons) =>
        class extends FeatureButtons {
            constructor() {
                super(...arguments);
            }
            async lockTable() {
                var self = this
                const selectedOrder = this.env.pos.get_order()
                const orders = this.env.pos.get('orders').models;
                let {confirmed, payload: reserved} = await this.showPopup('TableReservationPopup', {
                    title: this.env._t('Table Reservation'),
                    r_date: moment().format('YYYY-MM-DD HH:mm:ss')
                    });
                    
                if (confirmed) {
                    if (reserved) {
                        this.env.pos.r_customer_name = reserved.name;
                        if($('input[name="set_lock_tbl"]').length > 0){
                            this.env.pos.popup_date_reserve = moment($('input[type="datetime-local"]')[0].value).utc().format('YYYY-MM-DD HH:mm:ss');
                            this.env.pos.table_reserve_date = moment($('input[name="set_lock_tbl"]')[0].value).utc().format('YYYY-MM-DD HH:mm:ss');
                            this.env.pos.cust_phone_no = $('input[name="popup-phone-no"]')[0].value
                            let table = this.env.pos.table;
                            let tbl_locked = false

                            const selectedOrder = this.env.pos.get_order()
                            // selectedOrder.lock_order()
                            self.rpc({
                                model: 'restaurant.table',
                                method: 'write',
                                args: [table.id, {date_reserve: self.env.pos.table_reserve_date}],
                            })

                            self.rpc({
                                model: 'reserve.order',
                                method: 'create',
                                args: [
                                    {
                                        customer_name: reserved.name,
                                        cust_phone_no: this.env.pos.cust_phone_no,
                                        reservation_from: moment().utc().format('YYYY-MM-DD HH:mm:ss'),
                                        reservation_to: this.env.pos.popup_date_reserve,
                                        table_no: table.id,
                                        table_floor: table.floor_id[0],
                                        reservation_seat: selectedOrder.get_customer_count() ? selectedOrder.get_customer_count() : 0,
                                    }
                                ]
                            })
                            this.env.pos.set_table(null)
                            
                        }
                        return
                    } else {
                        // for (let i = 0; i < orders.length; i++) {
                        //     orders[i].lock_order()
                        // }
                    }
                }
            }
        };
    Registries.Component.extend(FeatureButtons, TableLockFeatureButtons);

    var _super_posmodel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        transfer_order_to_table: function(table) {
            let table_moved_from = this.order_to_transfer_to_different_table.table.id
            _super_posmodel.transfer_order_to_table.apply(this, arguments);
            this.rpc({
                model: 'restaurant.table',
                method: 'write',
                args: [table.id, {tbl_moved_from: table_moved_from}],
            }).then(function(d){
                console.log('2222222222222222222222222222:', d);
            })
        },

    });

    return TableLockFeatureButtons;
});