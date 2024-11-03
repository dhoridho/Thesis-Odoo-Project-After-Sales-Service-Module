// odoo.define('equip3_pos_masterdata.BackToFloorButton', function (require) {
//     'use strict';
//
//     const BackToFloorButton = require('pos_restaurant.BackToFloorButton');
//     const Registries = require('point_of_sale.Registries');
//
//     const RetailBackToFloorButton = (BackToFloorButton) =>
//         class extends BackToFloorButton {
//             async backToFloorScreen() {
//                 if (this.env.pos.config.auto_order) {
//                     let selectedOrder = this.env.pos.get_order();
//                     if (selectedOrder.hasChangesToPrint()) {
//                         const isPrintSuccessful = await selectedOrder.printChanges();
//                         if (isPrintSuccessful) {
//                             selectedOrder.saveChanges();
//                         }
//                     }
//                 }
//                 super.backToFloorScreen()
//             }
//         }
//     Registries.Component.extend(BackToFloorButton, RetailBackToFloorButton);
//
//     return RetailBackToFloorButton;
// });

odoo.define('equip3_pos_masterdata.BackToFloorButton', function (require) {
    'use strict';

    const BackToFloorButton = require('pos_restaurant.BackToFloorButton');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    const RetailBackToFloorButton = (BackToFloorButton) =>
        class extends BackToFloorButton {
            get hasTable() {
                let hasTable = super.hasTable;
                let selectedOrderMethod = jQuery('.pos > .pos-content').attr('data-selected-order-method');
                if(['takeaway','employee-meal','online-order'].includes(selectedOrderMethod)){
                    hasTable = false; //Hide Button when choose Take Away or Employee Meal
                }
                return hasTable;
            }
            backToFloorScreen() {
                this.showScreen('FloorScreen', { floor: this.floor, selected_order_method: 'dine-in' }); 
            }
        }
    Registries.Component.extend(BackToFloorButton, RetailBackToFloorButton);

    return RetailBackToFloorButton;
});

