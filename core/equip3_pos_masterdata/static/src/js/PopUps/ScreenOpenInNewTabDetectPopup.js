odoo.define('equip3_pos_masterdata.ScreenOpenInNewTabDetectPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl

    class ScreenOpenInNewTabDetectPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }

        async close_pos(){
            await this.env.pos.chrome._closePosScreen();
        }
    }
    
    ScreenOpenInNewTabDetectPopup.template = 'ScreenOpenInNewTabDetectPopup';
    ScreenOpenInNewTabDetectPopup.defaultProps = {
		title: 'Warning, We will close POS now',
		body: 'POS Screen already open in another tab, please close it before open it in new tab',
    };
    Registries.Component.add(ScreenOpenInNewTabDetectPopup);
    return ScreenOpenInNewTabDetectPopup;
});