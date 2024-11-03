// odoo.define('equip3_pos_membership.PaymentScreenStatus', function (require) {
//     'use strict';

//     const PaymentScreenStatus = require('point_of_sale.PaymentScreenStatus');
//     const models = require('point_of_sale.models');
//     const Registries = require('point_of_sale.Registries');

//     const RetailPaymentScreenStatus = (PaymentScreenStatus) =>
//         class extends PaymentScreenStatus {
//             constructor() {
//                 super(...arguments);
//             }

//             get Client() {
//                 if (this.env.pos.get_order() && this.env.pos.get_order().get_client()) {
//                     return this.env.pos.get_order().get_client();
//                 } else {
//                     return { 
//                         pos_loyalty_point: 0,
//                         balance: 0,
//                         wallet: 0,
//                     }
//                 }
//             }

//         }
//     Registries.Component.extend(PaymentScreenStatus, RetailPaymentScreenStatus);
//     return RetailPaymentScreenStatus;
// });
//  