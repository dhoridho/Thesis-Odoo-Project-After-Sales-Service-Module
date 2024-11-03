odoo.define('mx_elearning_plus.extended', function (require) {
    'use strict';
    var Fullscreen = require('website_slides.fullscreen');
    var findSlide = function (slideList, matcher) {
        var slideMatch = _.matcher(matcher);
        return _.find(slideList, slideMatch);
    };

    Fullscreen.include({

        _onChangeSlideRequest: function (ev){
            this._super.apply(this, arguments);
            var slideData = ev.data;
            var $data = this.$el.prevObject.find('.js_publish_btn:visible').parents(".js_publish_management:first");
            this._rpc({
                route: '/website/publish/slide',
                params: {
                    id: slideData.id,
                },
            })
            .then(function (result) {
                if (result){
                    $data.removeClass("css_unpublished");
                    $data.addClass("css_published");
                    $data.find('input').prop("checked", result);
                    $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
                }else{
                    $data.removeClass("css_published");
                    $data.addClass("css_unpublished");
                    $data.find('input').prop("checked", result);
                    $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
                }
            })
        }
    });
});
