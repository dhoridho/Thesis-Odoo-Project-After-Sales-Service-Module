odoo.define('mx_elearning_plus.course_extended', function (require) {
    'use strict';
    var publicWidget = require('web.public.widget');
    publicWidget.registry.websiteCourseExtended = publicWidget.Widget.extend({
        selector: '.o_course_extended',

        /**
         * @override
         */
        start: function () {
            $('.o_course_extended').on('click','#collapse_div',function() {
                var id = this.dataset.target.split('-')[1]
                if($('#slide-'+id).hasClass('show')) {
                    $(this).children().first().children().removeClass('fa-minus');
                    $(this).children().first().children().addClass('fa-plus');
                }else {
                    $(this).children().first().children().removeClass('fa-plus');
                    $(this).children().first().children().addClass('fa-minus');
                }
            });
        }
    })
});
