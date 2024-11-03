odoo.define('equip3_pos_masterdata_fnb.TableReservationPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class TableReservationPopup extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string} props.startingValue
         */
        constructor() {
            super(...arguments);
            this.state = useState({ r_customer: this.props.r_customer, r_date: this.props.r_date });
            this.inputReserveCustomerRef = useRef('input-reservation-customer');
        }
        mounted() {
            this.inputReserveCustomerRef.el.focus();
        }
        getPayload() {
            return {name: this.state.r_customer, date: this.state.r_date};
        }
        confirm(){
            if(!this.state.r_customer || !$('input[name="set_lock_tbl"]')[0].value){
                return false;
            }
            super.confirm();
        }
    }
    
    TableReservationPopup.template = 'TableReservationPopup';
    TableReservationPopup.defaultProps = {
        confirmText: 'Reserve',
        cancelText: 'Cancel',
        title: 'Table Reservation',
        body: '',
    };
    Registries.Component.add(TableReservationPopup);
    return TableReservationPopup;
});
