odoo.define('equip3_pos_masterdata_fnb.CustomFeatureButtons', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const FeatureButtons = require('equip3_pos_masterdata.FeatureButtons');
    const TransferOrderButton = require('pos_restaurant.TransferOrderButton');
    var models = require('point_of_sale.models');
    const {posbus} = require('point_of_sale.utils');
    const TableWidget = require('pos_restaurant.TableWidget');

    let checkReserveTableInterval = false;

    const POSTableWidgetExt = (TableWidget) =>
        class extends TableWidget {
            mounted() {
                super.mounted(...arguments);
                var self = this;
                let table = this.props.table;
                let curr_locked_tbl_id = false
                let tbl_locked = false
                const selectedOrder = this.env.pos.get_order()
                const orders = this.env.pos.get('orders').models;
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
                            table.locked = true
                            table.date_reserve = this.env.pos.table_reserve_date
                            let tbl_locked = false

                            const selectedOrder = this.env.pos.get_order()
                            // selectedOrder.lock_order()
                            self.rpc({
                                model: 'restaurant.table',
                                method: 'write',
                                args: [table.id, {date_reserve: self.env.pos.table_reserve_date,locked:true}],
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