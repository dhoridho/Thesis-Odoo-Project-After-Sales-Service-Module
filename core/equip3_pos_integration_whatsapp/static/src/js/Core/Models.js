odoo.define('equip3_pos_integration_whatsapp.model', function (require) {
    const models = require('point_of_sale.models');
    
    models.load_fields('res.company', ['pos_whatsapp_notification_for_receipt', 'pos_whatsapp_auto_sent_receipt_to_member']);
});