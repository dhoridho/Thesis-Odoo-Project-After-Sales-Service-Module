odoo.define('equip3_pos_masterdata.CardGroupImg', function(require) {
    'use strict';
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CardGroupImg extends PosComponent {
        get imageUrl() {
            const card_group = this.props.card_group;
            return `/web/image?model=group.card&field=card_group_img&id=${card_group.id}&write_date=${card_group.write_date}&unique=1`;
        }
    };
    CardGroupImg.template = 'CardGroupImg';

    Registries.Component.add(CardGroupImg);

    return CardGroupImg;
});