odoo.define('equip3_pos_membership.ClientLine', function (require) {
    'use strict';

    const ClientLine = require('point_of_sale.ClientLine');
    const Registries = require('point_of_sale.Registries');

    const PosMemClientLine = (ClientLine) =>
        class extends ClientLine {
            constructor() {
                super(...arguments);
            } 

            async reChargePoints() {
                let {confirmed, payload: newPoints} = await this.showPopup('ReChargePointPopup', {
                    title: this.props.partner['name'] + this.env._t(' have total points: ') + this.env.pos.format_currency_no_symbol(this.props.partner['pos_loyalty_point']) + this.env._t(' How many points need ReCharge ?'),
                    startingValue: 0,
                    id:'member_popup_point',
                })
                if (confirmed) {
                    this.props.partner['pos_loyalty_point']
                    let partner = await this.rpc({
                        model: 'res.partner',
                        method: 'recharge_point',
                        args: [[this.props.partner.id], {
                            'pos_loyalty_point_import': newPoints
                        }],
                    });
                    if(partner){
                        this.props.partner['pos_loyalty_point'] = partner.pos_loyalty_point;
                    }
                    await this._autoSyncBackend();
                    this.render();
                }
            }
 
            // async sendMessage(selectedClient) {
            //     if (!selectedClient['mobile'] && !selectedClient['phone']) {
            //         return this.env.pos.alert_message({
            //             title: this.env._t('Warning'),
            //             body: this.env._t('Customer missed Mobile and Phone, it not possible send message via WhatsApp')
            //         })
            //     } else {
            //         let startingValue = this.env._t('Dear ') + selectedClient.name + '\n';
            //         startingValue += this.env._t('---- *** This is your account information *** ------ \n');
            //         if(selectedClient.pos_loyalty_point){
            //             startingValue += this.env._t('You have Total Loyalty Points: ') + this.env.pos.format_currency_no_symbol(selectedClient.pos_loyalty_point) + '\n';
            //         }
            //         startingValue += this.env._t('With Credit Points: ') + this.env.pos.format_currency_no_symbol(selectedClient.balance) + '\n';
            //         startingValue += this.env._t('With Wallet Points: ') + this.env.pos.format_currency_no_symbol(selectedClient.wallet) + '\n';
            //         startingValue += this.env._t('-------- \n');
            //         startingValue += this.env._t('Thanks you for choice our services.');
            //         let {confirmed, payload: messageNeedSend} = await this.showPopup('TextAreaPopup', {
            //             title: this.env._t('What message need to send Client ?'),
            //             startingValue: startingValue
            //         })
            //         if (confirmed) {
            //             let mobile_no = selectedClient['phone'] || selectedClient['mobile']
            //             let message = messageNeedSend
            //             let responseOfWhatsApp = await this.rpc({
            //                 model: 'pos.config',
            //                 method: 'send_message_via_whatsapp',
            //                 args: [[], this.env.pos.config.id, mobile_no, message],
            //             });
            //             if (responseOfWhatsApp && responseOfWhatsApp['id']) {
            //                 return this.showPopup('ConfirmPopup', {
            //                     title: this.env._t('Successfully'),
            //                     body: this.env._t("Send successfully message to your Client's Phone WhatsApp: ") + mobile_no,
            //                     disableCancelButton: true,
            //                 })
            //             } else {
            //                 return this.env.pos.alert_message({
            //                     title: this.env._t('Error'),
            //                     body: this.env._t("Send Message is fail, please check WhatsApp API and Token of your pos config or Your Server turn off Internet"),
            //                     disableCancelButton: true,
            //                 })
            //             }
            //         }
            //     }
            // }

        }

        
    Registries.Component.extend(ClientLine, PosMemClientLine);
    return PosMemClientLine;
});
