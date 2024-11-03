odoo.define('equip3_pos_order_retail.Chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    const QWeb = core.qweb;
    const _t = core._t;
    const Session = require('web.Session');

    const CloseRetailChrome = (Chrome) =>
        class extends Chrome {
            async _closePos() {
                let ordersUnpaid = this.env.pos.db.get_unpaid_orders()
                const iot_url = this.env.pos.session.origin;
                const connection = new Session(void 0, iot_url, {
                    use_cors: true
                });
                const pingServer = await connection.rpc('/pos/passing/login', {}).then(function (result) {
                    return result
                }, function (error) {
                    return false;
                })
                if (!pingServer) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Your Internet or Odoo Server Offline. If you close a POS, could not open back'),
                    });
                    return true;
                }
                const self = this;
                let lists = [
                    {
                        name: this.env._t('Close POS Screen'),
                        item: 0,
                        id: 0,
                    },
                    {
                        name: this.env._t('Logout POS'),
                        item: 1,
                        id: 1,
                    },
                ]
                if (this.env.pos.user && this.env.pos.config.allow_closing_session) {
                    lists.push({
                        name: this.env._t('Close POS Screen and auto Closing Posting Entries Current Session'),
                        item: 2,
                        id: 2,
                    })
                    lists.push({
                        name: this.env._t('Close POS Screen, Closing Posting Entries and Logout POS'),
                        item: 3,
                        id: 3,
                    })
                    lists.push({
                        name: this.env._t('Posting Entries of POS Session and Print Z-Report'),
                        item: 4,
                        id: 4,
                    })
                }
                if (this.env.pos.config.cash_control && this.env.pos.config.management_session) {
                    lists.push({
                        name: this.env._t('Set Closing Cash'),
                        item: 5,
                        id: 5,
                    })
                }
                let title = this.env._t('Select 1 Close Type. ')
                if (ordersUnpaid.length > 0) {
                    title = title + ordersUnpaid.length + this.env._t(' unpaid Orders, have some draft unpaid orders. You can exit temporarily the Point of Sale, but you will loose that orders if you close the session')
                }
                let {confirmed, payload: selectedCloseTypes} = await this.showPopup(
                    'PopUpSelectionBox',
                    {
                        title: title,
                        items: lists,
                        onlySelectOne: true,
                    }
                );
                
                if (confirmed && selectedCloseTypes['items'] && selectedCloseTypes['items'].length == 1) {
                    let close_confirm = await this.env.pos._validate_action(_t(selectedCloseTypes['items'][0].name));
                    if(close_confirm || !this.env.pos.config.validate_by_manager){
                        const typeId = selectedCloseTypes['items'][0]['id']
                        if (typeId == 0) {
                            return this._closePosScreen()
                        }
                        if (typeId == 1) {
                            return window.location = '/web/session/logout';
                        }
                        if (typeId == 2) {
                            await this.closingSession()
                            return this._closePosScreen()
                        }
                        if (typeId == 3) {
                            await this.closingSession()
                            return window.location = '/web/session/logout';
                        }
                        if (typeId == 4) {
                            await this.closingSession()
                            let params = {
                                model: 'pos.session',
                                method: 'build_sessions_report',
                                args: [[this.env.pos.pos_session.id]],
                            };
                            let values = await this.rpc(params, {shadow: true}).then(function (values) {
                                return values
                            }, function (err) {
                                return self.env.pos.query_backend_fail(err);
                            })
                            let reportData = values[this.env.pos.pos_session.id];
                            let start_at = field_utils.parse.datetime(reportData.session.start_at);
                            start_at = field_utils.format.datetime(start_at);
                            reportData['start_at'] = start_at;
                            if (reportData['stop_at']) {
                                var stop_at = field_utils.parse.datetime(reportData.session.stop_at);
                                stop_at = field_utils.format.datetime(stop_at);
                                reportData['stop_at'] = stop_at;
                            }
                            let reportHtml = QWeb.render('ReportSalesSummarySession', {
                                pos: this.env.pos,
                                report: reportData,
                            })
                            this.showScreen('ReportScreen', {
                                report_html: reportHtml,
                                closeScreen: true
                            })
                        }
                        if (typeId == 5) {
                            await this._setClosingCash()
                        }
                    }
                }
            }
        }
    Registries.Component.extend(Chrome, CloseRetailChrome);

    return CloseRetailChrome;
});