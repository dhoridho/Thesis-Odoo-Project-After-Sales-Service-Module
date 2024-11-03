odoo.define('aspl_feedback_system.feedback_system', function (require) {
    "use strict";
    var ajax = require('web.ajax');

    $(document).ready(function (){
        $('.rating1').on('click', function(){
            $(event.currentTarget).html('').html('😠')
            $('.rating2').html('').html('😶')
            $('.rating3').html('').html('😶')
            $('.rating4').html('').html('😶')
            $('.rating5').html('').html('😶')
        })
        $('.rating2').on('click', function(){
            $(event.currentTarget).html('').html('😦')
            $('.rating1').html('').html('😶')
            $('.rating3').html('').html('😶')
            $('.rating4').html('').html('😶')
            $('.rating5').html('').html('😶')
        })
        $('.rating3').on('click', function(){
            $(event.currentTarget).html('').html('😐')
            $('.rating2').html('').html('😶')
            $('.rating1').html('').html('😶')
            $('.rating4').html('').html('😶')
            $('.rating5').html('').html('😶')
        })
        $('.rating4').on('click', function(){
            $(event.currentTarget).html('').html('😀')
            $('.rating2').html('').html('😶')
            $('.rating1').html('').html('😶')
            $('.rating3').html('').html('😶')
            $('.rating5').html('').html('😶')
        })
        $('.rating5').on('click', function(){
            $(event.currentTarget).html('').html('😍')
            $('.rating1').html('').html('😶')
            $('.rating2').html('').html('😶')
            $('.rating3').html('').html('😶')
            $('.rating4').html('').html('😶')
        })
        $('.page-link').on('click', function(){
            $('input[name=cur_page]').attr('value', $(this).text())
        })


    })
})
