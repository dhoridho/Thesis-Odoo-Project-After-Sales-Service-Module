$('#owl-c').owlCarousel({
  loop: true,
  margin: 10,
  autoplay: true,
  autoplaySpeed: 600,
  nav: true,
  dots: false,
  navText: [
    '<i class="fa fa-chevron-left"></i>',
    '<i class="fa fa-chevron-right"></i>'
  ],
  navContainer: '.owl-nav',
  responsive: {
    0: {
      items: 1
    },
    500: {
      items: 2
    },
    700: {
      items: 3
    },
    880: {
      items: 4
    },
    1200: {
      items: 5
    },
    1320: {
      items: 6
    }
  }
});


$(document).ready(function() {
  $('#arrow-top').click(function() {
    $('body,html').animate({
      scrollTop: 0
    }, 400);
    return false;
  });

});
