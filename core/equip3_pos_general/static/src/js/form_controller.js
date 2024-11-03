odoo.define('equip3_pos_general.PosGeneralFormController', function(require) {
    "use strict";

    var FormController = require('web.FormController');
    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var _t = core._t;

    let PosGeneralFormController = FormController.include({

        _actionPosConfirmClosing: function(ev) {
            let self = this; 
            let record = self.model.get(ev.data.record.id).data;
            let message = _('This Session still opened on several tab/device, Are you sure want to close this session?');
            let $content = $(`
                <div class="d-flex align-items-center justify-content-center">
                    <div class="message w-100">${message}</div>
                </div>
            `);

            let dialog = new Dialog(self, {
                title: _t('Confirmation'),
                $content: $content,
                buttons: [
                    {
                        text: _t('Ok'), 
                        classes: 'btn-primary', 
                        close: true, 
                        click: function () {
                            ev.data.attrs.is_confirmed = true;
                            self._onButtonClicked(ev);
                        }
                    }, 
                    {   
                        text: _t('No'), 
                        close: true
                    },
                ],
                size: false,
            });

            dialog.opened().then(function () {   });
            dialog.open();
        },

        _actionPosDownloadData: function (filename, text) {
            const blob = new Blob([text]);
            const URL = window.URL || window.webkitURL;
            const url =  URL.createObjectURL(blob);
            const element = document.createElement('a');
            element.setAttribute('href', url);
            element.setAttribute('download', filename);
            element.style.display = 'none';
            document.body.appendChild(element);
            element.click();
            document.body.removeChild(element);
        },

        // TODO: Download paid pos session order (complete order) when left unsynced
        _actionPosDownloadPaidOrders: function (session) {
            console.warn('[_actionPosDownloadPaidOrders] backup data pos session order.');
            let storage_name = 'openerp_pos_db_' + session.pos_config_uuid + '_orders';
            let paid_orders_json_data = localStorage.getItem(storage_name);
            if(paid_orders_json_data === null){
                paid_orders_json_data = '[]';
            }
            let filename = `backup_paid_orders_${moment().format('YYYY-MM-DD-HH-mm-ss')}.json`;
            this.do_notify(false, _t('Preparing download backup paid orders, please wait for moment.'));
            this._actionPosDownloadData(filename, paid_orders_json_data);
        },

        _onButtonClicked: function (ev) {
            let action = ev.data.attrs.name;
            let _action_confirm_closing = [
                'action_end_session_opened_open_cash_control', // End of Session (IF Has Cash Control is True)
                'action_pos_session_closing_control', // Close Session & Post Entries
            ]
            
            if (_action_confirm_closing.includes(action) == true) {
                let is_cashier_not_logout = false;
                let record = this.model.get(ev.data.record.id).data;
                
                if(record.is_multi_session && record.log_cashier_ids){
                    is_cashier_not_logout = record.log_cashier_ids.data.some(data=>(data.data.logout_date==false));
                }
                if (!is_cashier_not_logout) {
                    if (!ev.data.attrs.is_confirmed){
                        this._actionPosDownloadPaidOrders(record);
                    }
                }
                if (is_cashier_not_logout) {
                    if (!ev.data.attrs.is_confirmed){
                        this._actionPosDownloadPaidOrders(record);

                        return this._actionPosConfirmClosing(ev);
                    }
                    ev.data.attrs.is_confirmed = false;
                }

                return  this._super.apply(this, arguments);
            }

            return this._super.apply(this, arguments);
        }
    });

    return PosGeneralFormController;

});