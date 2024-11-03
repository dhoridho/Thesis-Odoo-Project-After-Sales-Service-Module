odoo.define('equip3_pos_general.ReserveTablePopupButton', function (require) {
    'use strict';

    const {useState} = owl;
    const core = require('web.core');
    const _t = core._t;
    const models = require('point_of_sale.models');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');
    const TableWidget = require('pos_restaurant.TableWidget');
    const {posbus} = require('point_of_sale.utils');
    const {Gui} = require('point_of_sale.Gui');
	let checkReserveTableInterval = false;

    class ReserveTablePopupButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.opening = false
            var self = this;

            rpc.query({
				model: 'pos.order',
				method: 'get_table_reservation_popup_data', 
				args: [[]],
			}).then(function(res) {
				if(res){
					self.customer_ids = res.customer;
					self.floor_ids = res.floors;
					self.table_ids = res.tables;
				}
			})
        }


        async onClick() {
            const self = this

			let {confirmed, payload: popup_data} = await this.showPopup('ReserveTablePopup', {
				'customer_ids': self.customer_ids,
				'floor_ids': self.floor_ids,
				'table_ids': self.table_ids,
				'visible_table_ids': [],
			})
			if (confirmed) {
				let $popup = $('.popup.reserve-table-popup');
				let r_date = $popup.find('[name="rsv_date"]').val();
				let r_time = $popup.find('[name="rsv_time"]').val();
				let r_customer = $popup.find('[name="rsv_customer"]').select2('data')['text'];
				let r_phone = $popup.find('[name="rsv_customer_phone"]').val();
				let r_email = $popup.find('[name="rsv_customer_email"]').val();
				let r_floor = $popup.find('[name="rsv_floor"]').val();
				let r_table = $popup.find('[name="rsv_table"]').val();
				let r_note = $popup.find('[name="rsv_note"]').val();
				let r_guest = $popup.find('[name="rsv_guest"]').val();

				let tbl_locked = false;
				let manager_user = self.env.pos.user;
				if (manager_user.role == "manager"){
					let {confirmed:c, payload: p} = await Gui.showPopup('NumberPopup', {
						isPassword: true,
						title: this.env._t('Manager pin')
					});
					if (c) {
						var manager_security_pin = manager_user.pos_security_pin
						var entered_security_pin = p
						if (manager_security_pin.toString() !== entered_security_pin.toString()){
							return self.env.pos.alert_message({
								title: _t('Warning'),
								body: _t('Pos Security Pin of ') + manager_user.name + _t(' Incorrect.')
							})
						}else {
							if (r_date && r_time && r_customer) {
								await rpc.query({
									model: 'reserve.order',
									method: 'create',
									args: [{
										customer_name: r_customer,
										cust_phone_no: r_phone,
										reservation_from: moment(r_date+' '+r_time).utc().format('YYYY-MM-DD HH:mm:ss'),
										reservation_to: moment(r_date+' '+r_time).add(1, 'hours').utc().format('YYYY-MM-DD HH:mm:ss'),
										table_no: r_table,
										table_floor: r_floor,
										guest:r_guest,
										// reservation_seat: selectedOrder.get_customer_count() ? selectedOrder.get_customer_count() : 0,
									}]
								}).then(function(res){
									self.rpc({
										model: 'restaurant.table',
										method: 'write',
										args: [r_table, 
											{
												date_reserve: moment(r_date+' '+r_time).utc().format('YYYY-MM-DD HH:mm:ss'),
												guest:r_guest,
											}
										],
									});
								});
								await self.env.pos.getReserveOrders();
								await self.env.pos.db.get_reserve_order();
								if($('.reservation-list-tmp .button_back').length > 0){
									$('.reservation-list-tmp .button_back').click()
									$('.reservation-list-header-button').click()
								}

							}
						}
					}
				}

			}
        }
    }

    ReserveTablePopupButton.template = 'ReserveTablePopupButton';
    Registries.Component.add(ReserveTablePopupButton);
	
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

    return ReserveTablePopupButton;

});
