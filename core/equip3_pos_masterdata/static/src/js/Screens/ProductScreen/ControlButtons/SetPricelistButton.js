odoo.define('equip3_pos_masterdata.SetPricelistButton', function (require) {
    'use strict';

    const SetPricelistButton = require('point_of_sale.SetPricelistButton');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils')

    const RetailSetPricelistButton = (SetPricelistButton) =>
        class extends SetPricelistButton {
            async onClick() {

                // Create the list to be passed to the SelectionPopup.
                // Pricelist object is passed as item in the list because it
                // is the object that will be returned when the popup is confirmed.
                const selectionList = this.env.pos.pricelists.map(pricelist => ({
                    id: pricelist.id,
                    label: pricelist.name,
                    isSelected: pricelist.id === this.currentOrder.pricelist.id,
                    item: pricelist,
                }));

                const { confirmed, payload: selectedPricelist } = await this.showPopup(
                    'SelectionPopup',
                    {
                        title: this.env._t('Select the pricelist'),
                        list: selectionList,
                    }
                );

                if (confirmed) {
                    this.currentOrder.set_pricelist(selectedPricelist);
                    this.env.pos.currency = this.env.pos.currencies.filter(c => c.id == selectedPricelist.currency_id[0])[0]
                }
            }
        }
    Registries.Component.extend(SetPricelistButton, RetailSetPricelistButton);

    return RetailSetPricelistButton;
});
