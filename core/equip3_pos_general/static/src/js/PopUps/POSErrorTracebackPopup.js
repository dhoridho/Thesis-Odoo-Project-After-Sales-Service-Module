odoo.define('equip3_pos_general.ErrorTr1acebackPopup', function(require) {
    'use strict';

    const ErrorPopup = require('point_of_sale.ErrorPopup');
    const Registries = require('point_of_sale.Registries');
    var session = require('web.session');


    // formerly ErrorTracebackPopupWidget
    class ErrorTracebackPopup extends ErrorPopup {

        // buttonClose(){
        //     $('#POSErrorTracebackPopup').modal('toggle');
        //     $('#POSErrorTracebackPopup').modal('toggle');
        //     $('#POSErrorTracebackPopup').remove()

        // }
        buttonViewDetail(){
            var download = 1
            if(odoo.debug){
                if($('.button_view_error_detail_error').text()=='View Detail'){
                    $('.button_view_error_detail_error').text('Hide Detail')
                    $('.main_error_desc_new_pos').show()
                }
                else{
                    $('.button_view_error_detail_error').text('View Detail')
                    $('.main_error_desc_new_pos').hide()
                    download = 0
                }

            }
            if(download==1) {
                $('#blob_error_download').click()
            }
            
                
        }

        get tracebackUrl() {
            const blob = new Blob([this.props.body]);
            const URL = window.URL || window.webkitURL;
            return URL.createObjectURL(blob);
        }
        get tracebackFilename() {
            return `${this.env._t('error')} ${moment().format('YYYY-MM-DD-HH-mm-ss')}.txt`;
        }
        emailTraceback() {
            const address = this.env.pos.company.email;
            const subject = this.env._t('IMPORTANT: Bug Report From Point Of Sale');
            window.open(
                'mailto:' +
                    address +
                    '?subject=' +
                    (subject ? window.encodeURIComponent(subject) : '') +
                    '&body=' +
                    (this.props.body ? window.encodeURIComponent(this.props.body) : '')
            );
        }
    }
    ErrorTracebackPopup.template = 'POSErrorTracebackPopup';
    ErrorTracebackPopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Error with Traceback',
        body: '',
        exitButtonIsShown: false,
        exitButtonText: 'Exit Pos',
        exitButtonTrigger: 'close-pos'
    };

    Registries.Component.add(ErrorTracebackPopup);

    return ErrorTracebackPopup;
});