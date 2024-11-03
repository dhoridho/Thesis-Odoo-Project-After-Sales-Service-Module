odoo.define('equip3_pos_general_contd.MyCustomMessagePopup', function (require) {
    'use strict';

    const {useState, useRef, useContext} = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');
    const {useExternalListener} = owl.hooks;
    
	// MyCustomMessagePopup Popup
    class MyCustomMessagePopup extends AbstractAwaitablePopup {}
    MyCustomMessagePopup.template = 'MyCustomMessagePopup';
    MyCustomMessagePopup.defaultProps = { title: 'Message', value:'' };
    Registries.Component.add(MyCustomMessagePopup);

    return MyCustomMessagePopup;

});