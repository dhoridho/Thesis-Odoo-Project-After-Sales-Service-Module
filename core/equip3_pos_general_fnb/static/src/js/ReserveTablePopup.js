odoo.define('equip3_pos_general.ReserveTablePopup', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');
    const core = require('web.core');
    const _t = core._t;
    const {Gui} = require('point_of_sale.Gui');
    const {useState} = owl;

// models.load_models({
//     model: 'restaurant.table',
//     fields: ['guest'],
// });


    class ReserveTablePopup extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
            	reserve_dt: this.props.reserve_dt,
            	reserve_time: this.props.reserve_time,
            	reserve_customer: this.props.reserve_customer,
            	reserve_phone: this.props.reserve_phone,
            	reserve_email: this.props.reserve_email,
                reserve_floor: this.props.reserve_floor,
            	reserve_table: this.props.reserve_table,
            	reserve_note: this.props.reserve_note,
                reserve_guest: this.props.reserve_guest,
            });
        }
        mounted() {
            super.mounted();
            let self = this;
            let customers = this.props.customer_ids;
            if($("input[name='rsv_customer']").length > 0){
                $("input[name='rsv_customer']").select2({
                    minimumInputLength: 3,
                    query: function(query) {
                        let key = query.term.toLowerCase();
                        let results = customers
                                .filter((m)=>m.name.toLowerCase().startsWith(key))
                                .map((m)=>({ id: m.id, text: m.name }));
                        query.callback({results: results});
                        return;
                    },
                }).select2('val', []);
            }
        }

		getPayload() {
            return {
            	r_dt: this.state.reserve_dt,
            	r_time: this.state.reserve_time,
            	r_customer: this.state.reserve_customer,
            	r_phone: this.state.reserve_phone,
            	r_email: this.state.reserve_email,
                r_floor: this.state.reserve_floor,
            	r_table: this.state.reserve_table,
            	r_note: this.state.reserve_note,
                r_guest: this.state.reserve_guest,
            };
        }
        async onChangeFloor() {
            let $popup = $('.popup.reserve-table-popup');
            let selected_value = parseInt($popup.find('[name="rsv_floor"]').val());
            let html_select_table = '';
            let visible_table_ids = []
            for(let table of this.props.table_ids){
                if(table.floor_id[0] == selected_value){
                    visible_table_ids.push(table);
                    html_select_table += `<option  value="${table.id}">${table.name}</option>`
                }
            }
            this.props.visible_table_ids = visible_table_ids;
            $popup.find('[name="rsv_table"]').html(html_select_table);
        }
        get dateToday(){
            return moment().format('YYYY-MM-DD');
        }
        cancel() {
            this.trigger('close-popup');
        }
        async confirm() {
            let self = this;
            let has_error = [];
            let $popup = $('.popup.reserve-table-popup');

            $popup.find('input[required="1"], select[required="1"]').each(function(){
                let $i = $(this);
                $i.removeClass('has_error');
                $($i.parent().find('a')).removeClass('has_error');
                if($i.val() == '' || $i.val() == null){
                    $i.addClass('has_error');
                    has_error.push($i.attr('name'));
                    $($i.parent().find('a')).addClass('has_error');
                }
            });
            if(has_error.length){
                return;
            }

            let r_date = $popup.find('[name="rsv_date"]').val();
            let r_time = $popup.find('[name="rsv_time"]').val();
            let r_floor = parseInt($popup.find('[name="rsv_floor"]').val());
            let r_table = parseInt($popup.find('[name="rsv_table"]').val());
            let r_guest = $popup.find('[name="rsv_guest"]').val();

            let reservation_from = moment(r_date+' '+r_time).utc().format('YYYY-MM-DD HH:mm:ss');
            let reservation_to = moment(r_date+' '+r_time).add(1, 'hours').utc().format('YYYY-MM-DD HH:mm:ss');
            let reserve_order = await self.rpc({
                model: 'restaurant.table',
                method: 'get_reserve_order',
                args: [[r_table], {
                    table_no: r_table,
                    table_floor: r_floor,
                    reservation_from: reservation_from,
                    reservation_to: reservation_to,
                    guest: r_guest,
                }],
            });

            if (Object.keys(reserve_order).length){
                let order = reserve_order;
                let msg = `${order.name} Table/Floor: ${order.table_no[1]}/${order.table_floor[1]}`;
                return Gui.showPopup('ConfirmPopup', {
                    title: _t('Warning'),
                    body: 'Table already reserved\n' + msg,
                });
                return;
            }
			this.props.resolve({ confirmed: true, payload: true });
            this.trigger('close-popup');
		}
    }

    ReserveTablePopup.template = 'ReserveTablePopup';
    ReserveTablePopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Add New Reservation',
        // table_ids: this.state.table_ids,
    };

    Registries.Component.add(ReserveTablePopup);

    return ReserveTablePopup;
});
