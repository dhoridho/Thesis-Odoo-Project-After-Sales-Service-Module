odoo.define('equip3_pos_membership_l10n_id.models', function (require) {
    "use strict";

    const models = require('point_of_sale.models');
    const equip3_pos_general_models = require('equip3_pos_general.models');
    const equip3_pos_membership_models = require('equip3_pos_membership.model');
    
    const PosOrderGeneral = require('equip3_pos_general.pos_order');
    const PosOrderMasterdata = require('equip3_pos_masterdata.order');

    models.load_fields('res.partner', ['l10n_id_pkp']);

});
