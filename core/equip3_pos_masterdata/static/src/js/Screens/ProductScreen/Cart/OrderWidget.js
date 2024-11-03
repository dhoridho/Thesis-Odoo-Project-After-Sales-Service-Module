odoo.define('equip3_pos_masterdata.OrderWidget', function (require) {
        'use strict';

        const OrderWidget = require('point_of_sale.OrderWidget');
        const Registries = require('point_of_sale.Registries');
        const {useState, useRef, onPatched} = owl.hooks;

        let updateSummaryTimeout = null;

        const RetailOrderWidget = (OrderWidget) =>
            class extends OrderWidget {
                constructor() {
                    super(...arguments);
                    this.state = useState({
                        total: 0,
                        tax: 0,
                        discount: 0,
                        totalWithOutTaxes: 0,
                        margin: 0,
                        totalItems: 0,
                        totalQuantities: 0,
                    });
                }

                getSequenceNumber(){
                    const selectedOrder = this.env.pos.get_order();
                    return selectedOrder.sync_sequence_number;
                }

                // Overide
                async _onNewOrder(order) {
                    let self = this;
                    if (order) {
                        order.orderlines.on(
                            'new-orderline-selected',
                            () => this.trigger('new-orderline-selected'),
                            this
                        );
                        order.orderlines.on(
                            'change', 
                            () => {
                                clearTimeout(updateSummaryTimeout);
                                updateSummaryTimeout = setTimeout(function() {
                                    self._updateSummary();
                                }, 300);
                            }, 
                            this
                        );    
                        order.orderlines.on(
                            'add remove',
                            () => {
                                this.scrollToBottom = true;
                                this._updateSummary();
                            },
                            this
                        );

                        if(!order.sync_sequence_number){
                            let sync_sequence_number = await this.env.pos.get_sync_sequence_number();
                            order.sync_sequence_number = sync_sequence_number;
                        }
                        console.log('[_onNewOrder] sync_sequence_number:', order.sync_sequence_number) 

                        order.on('change', this.render, this);
                    }
                    this._updateSummary();
                    this.trigger('new-orderline-selected');
                }


                _updateCurrentOrder(pos, newSelectedOrder) {
                    this._currentOrder.orderlines.off('change', null, this);
                    if (newSelectedOrder) {
                        this._currentOrder = newSelectedOrder;
                        this._currentOrder.orderlines.on('change', this._updateSummary, this);
                    }
                }

                _selectLine(event) {
                    super._selectLine(event)
                }

                async _editPackLotLines(event) {
                    let self = this;
                    const orderline = event.detail.orderline;
                    const isAllowOnlyOneLot = orderline.product.isAllowOnlyOneLot();
                    const packLotLinesToEdit = orderline.getPackLotLinesToEdit(isAllowOnlyOneLot);
                    if (packLotLinesToEdit.length == 1 && packLotLinesToEdit[0].text == "" && this.env.pos.config.fullfill_lots && ['serial', 'lot'].includes(orderline.product.tracking)) {
                        let packLotLinesToEdit = await this.rpc({
                            model: 'stock.production.lot',
                            method: 'search_read',
                            domain: [['product_id', '=', orderline.product.id]],
                            fields: ['name', 'id']
                        }).then(function (value) {
                            return value
                        }, function (error) {
                            self.env.pos.query_backend_fail(error)
                            return false
                        })
                        if (!packLotLinesToEdit) {
                            packLotLinesToEdit = this.env.pos.lots.filter(l => l.product_id && l.product_id[0] == product['id'])
                        }
                        let newPackLotLinesToEdit = packLotLinesToEdit.map((lot) => ({text: lot.name}));
                        const {confirmed, payload} = await this.showPopup('EditListPopup', {
                            title: this.env._t('Selection only 1 Lot/Serial Number(s). It a required'),
                            isSingleItem: isAllowOnlyOneLot,
                            array: newPackLotLinesToEdit,
                        });
                        if (confirmed) {
                            const modifiedPackLotLines = Object.fromEntries(
                                payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                            );
                            const newPackLotLines = payload.newArray
                                .filter(item => !item.id)
                                .map(item => ({lot_name: item.text}));
                            if (newPackLotLines.length == 1) {
                                orderline.setPackLotLines({modifiedPackLotLines, newPackLotLines});
                            } else {
                                return this.env.pos.alert_message({
                                    title: this.env._t('Warning'),
                                    body: this.env._t('Please select only one Lot/Serial')
                                })
                            }
                        }
                        this.order.select_orderline(event.detail.orderline);
                    } else {
                        await super._editPackLotLines(event)
                    }
                }

            }

        Registries.Component.extend(OrderWidget, RetailOrderWidget);

        return RetailOrderWidget;
    }
);
