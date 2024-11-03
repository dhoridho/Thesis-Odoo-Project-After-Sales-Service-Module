odoo.define('website_axis_helpdesk.portal_post', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var composer = require('portal.composer')

    composer.PortalComposer.include({
        _onSubmitButtonClick: function () {
            var id = document.getElementsByName("res_id")[0].value;
            ajax.jsonRpc('/portal/get_id', 'call', {
                'id' : id,
              }).then(function (data) {
            });
        },
    });
     $(document).ready(function() {
        $(".customer_rating").click(function(){
            var id = $(this).attr('data-value');
            document.getElementById('ticket_id').value = id;
        });
       });
});
