odoo.define('equip3_pos_masterdata.CardPaymentImg', function(require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CardPaymentImg extends PosComponent {
        get imageUrl() {
            const card_payment = this.props.card_payment;
            return `/web/image?model=card.payment&field=card_img&id=${card_payment.id}&write_date=${card_payment.write_date}&unique=1`;
        }
    };
    CardPaymentImg.template = 'CardPaymentImg';

    Registries.Component.add(CardPaymentImg);

    return CardPaymentImg;
});