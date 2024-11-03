odoo.define('equip3_pos_general.CashierSelectionPopup', function (require) {
    'use strict';

    const { useState, useExternalListener } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
 
    class CashierSelectionPopup extends AbstractAwaitablePopup {
        /**
         * Value of the `item` key of the selected element in the Selection
         * Array is the payload of this popup.
         *
         * @param {Object} props
         * @param {String} [props.confirmText='Confirm']
         * @param {String} [props.cancelText='Cancel']
         * @param {String} [props.title='Select']
         * @param {String} [props.body='']
         * @param {Array<Selection>} [props.list=[]]
         *      Selection {
         *          id: integer,
         *          label: string,
         *          isSelected: boolean,
         *          item: any,
         *      }
         */
        constructor() {
            super(...arguments);
            this.state = useState({ selectedId: this.props.list.find((item) => item.isSelected) });

            useExternalListener(window, 'keyup', this._keyUp);
        }

        async _keyUp(event) {
            console.log('[CashierSelectionPopup_keyboardHandler]: ', event.key)
            //TODO: Select cashier when press numeric keys
            const key = parseInt(event.key);
            if ([0, 1, 2, 3, 4, 5, 6, 7, 8, 9].includes(key)) {
                let $target = $('.cashier-modal-dialog .selection-item')[event.key];
                if($target){
                    $target.click();
                }
            }
        }

        selectItem(itemId) {
            this.state.selectedId = itemId;
            this.confirm();
        }
        /**
         * We send as payload of the response the selected item.
         *
         * @override
         */
        getPayload() {
            const selected = this.props.list.find((item) => this.state.selectedId === item.id);
            return selected && selected.item;
        }
    }
    CashierSelectionPopup.template = 'CashierSelectionPopup';
    CashierSelectionPopup.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Select',
        body: '',
        list: [],
    };

    Registries.Component.add(CashierSelectionPopup);

    return CashierSelectionPopup;
});
