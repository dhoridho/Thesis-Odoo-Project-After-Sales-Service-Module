odoo.define('equip3_pos_user.SaleOrderDetail', function (require) {
    'use strict';

    const SaleOrderDetail = require('equip3_pos_masterdata.SaleOrderDetail');
    const Registries = require('point_of_sale.Registries');
    const framework = require('web.framework');

    const UserSaleOrderDetail = (SaleOrderDetail) =>
        class extends SaleOrderDetail {
            async covertToPosOrder() {
                var self = this;
                let {confirmed, payload: result} = await this.showPopup('ConfirmPopupPickupSO', {
                        title: this.env._t('Are you this order has been picked up ?'),
                        number_so: this.props.order.name,
                        name_member:this.props.order.partner_id[1],
                    })
                    if (confirmed) {
                        framework.blockUI();
                        if (this.props.order.pos_order_id) {
                            this.env.pos.alert_message({
                                title: this.env._t('Alert'),
                                body: this.env._t('SO: ' + this.props.order['name'] + ' is already converted to POS Order!')
                            })
                            framework.unblockUI();
                            return
                        }
                        await this.rpc({
                            model: 'pos.order',
                            method: 'create_pos_order_from_so',
                            args: [[], this.props.order.id],
                            context: {
                                pos: true,
                                config_id: this.env.session.config.id,
                                session_id: this.env.session.config.pos_session_id,
                                delivered:true
                            }
                        }).then(async function (response) {
                            framework.unblockUI();
                            self.env.pos.alert_message({
                                title: self.env._t('Alert'),
                                body: self.env._t('SO: ' + self.props.order['name'] + ' is converted into pos order!')
                            })
                            self.env.pos.booking_in_state_sale_ids = self.env.pos.booking_in_state_sale_ids.filter(function(id) { return id !==  self.props.order.id});
                            await self.env.pos.getSaleOrders();
                            self.trigger('close-temp-screen');
                            self.render();
                            if($('.reservation-list-header-button').length==1){
                                $('.reservation-list-header-button').click()
                            }
                            return response
                        }, function (err) {
                            framework.unblockUI();
                            console.log(err)
                            return self.env.pos.query_backend_fail(err);
                        })
                        
                    }
            }
        };

    Registries.Component.extend(SaleOrderDetail, UserSaleOrderDetail);

    return UserSaleOrderDetail;
});


