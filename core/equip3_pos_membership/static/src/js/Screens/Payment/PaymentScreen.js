odoo.define('equip3_pos_membership.PaymentScreen', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    

    const MembershipPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen { 
            selectPaymentLine(event) {
	            super.selectPaymentLine(event); 
	            let selectedOrder = this.env.pos.get_order();
                if(selectedOrder){
                    selectedOrder.orderlines.models.forEach(l => {
                        if(l.redeem_point && l.redeem_point > 0) {
                            l.selected_redeem_payment = false
                        }
                    });
                }
                this.render();
	        }
            deletePaymentLine(event) {
                const {cid} = event.detail;
                const line = this.paymentLines.find((line) => line.cid === cid);
                if(line && line.customer_deposit_id){
                    this.currentOrder.customer_deposit_id = false;
                }
                super.deletePaymentLine(event);
            }
        }

    Registries.Component.extend(PaymentScreen, MembershipPaymentScreen);
  
    return MembershipPaymentScreen;
});
